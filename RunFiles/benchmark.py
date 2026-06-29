import sys
import os
import time
import subprocess
import random
import psutil
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt, QTimer

MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "main.py")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


class DummyWindow(QWidget):

    def __init__(self, idx, speed_x, speed_y):
        super().__init__()
        self.setWindowTitle(f"StressTest Dummy Window {idx}")
        self.resize(300, 200)
        self.speed_x = speed_x
        self.speed_y = speed_y

        if speed_x != 0 or speed_y != 0:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.move_step)
            self.timer.start(16)  # 約60FPS

    def move_step(self):
        pos = self.pos()
        new_x = pos.x() + self.speed_x
        new_y = pos.y() + self.speed_y

        screen = QApplication.primaryScreen().geometry()
        if new_x < 0 or new_x > screen.width() - 300:
            self.speed_x = -self.speed_x
        if new_y < 0 or new_y > screen.height() - 200:
            self.speed_y = -self.speed_y

        self.move(new_x, new_y)


class BenchmarkWindow(QWidget):

    def __init__(self, main_process, py_proc, dummy_windows):
        super().__init__()
        self.main_process = main_process
        self.py_proc = py_proc
        self.dummy_windows = dummy_windows
        
        self.cpu_usages = []
        self.mem_usages = []
        self.elapsed_seconds = 0
        self.test_duration = 10  # テスト時間 (秒)

        self.setWindowTitle("動作ベンチマークテスト")
        self.resize(550, 900)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 最前面表示で埋もれないようにする

        # クールなダークテーマUI
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                font-size: 15px;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #2b2b2b;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #00bcd4;
            }
            QPushButton {
                background-color: #00bcd4;
                color: #1a1a1a;
                border: none;
                padding: 10px 24px;
                font-size: 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #26c6da;
            }
        """)

        self.setup_measuring_ui()

        # 1秒ごとの測定タイマー
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_measure_tick)
        self.timer.start(1000)

    def setup_measuring_ui(self):
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(30, 40, 30, 40)
        self.layout.setSpacing(20)

        # タイトル
        title_label = QLabel("WindowBorderTool - 動作ベンチマーク\nWindowBorderTool - Performance Benchmark")
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title_label.setStyleSheet("color: #00bcd4;")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setWordWrap(True)
        self.layout.addWidget(title_label)

        # 進捗状況説明
        self.status_label = QLabel("PCの性能測定と描画負荷の耐久テストを実行中...\nRunning hardware performance measurement and draw load stress test...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.layout.addWidget(self.status_label)

        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.test_duration)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        # リアルタイム統計
        self.info_layout = QVBoxLayout()
        self.cpu_label = QLabel("現在のCPU負荷 (Current CPU Load): 測定中 (Measuring)...")
        self.mem_label = QLabel("現在のメモリ使用量 (Current Memory Usage): 測定中 (Measuring)...")
        self.cpu_label.setWordWrap(True)
        self.mem_label.setWordWrap(True)
        self.info_layout.addWidget(self.cpu_label)
        self.info_layout.addWidget(self.mem_label)
        self.layout.addLayout(self.info_layout)

        self.setLayout(self.layout)

    def on_measure_tick(self):
        self.elapsed_seconds += 1
        self.progress_bar.setValue(self.elapsed_seconds)

        try:
            # ターゲットプロセスの負荷を取得
            cpu = self.py_proc.cpu_percent(interval=None)
            mem = self.py_proc.memory_info().rss / (1024 * 1024)
            self.cpu_usages.append(cpu)
            self.mem_usages.append(mem)

            # 表示更新
            self.cpu_label.setText(f"現在のCPU負荷: {cpu:.1f} %\n(Current CPU Load: {cpu:.1f} %)")
            self.mem_label.setText(f"現在のメモリ使用量: {mem:.1f} MB\n(Current Memory Usage: {mem:.1f} MB)")
        except Exception:
            pass

        if self.elapsed_seconds >= self.test_duration:
            self.timer.stop()
            self.show_results()

    def show_results(self):
        # 1. バックグラウンドのダミーウィンドウをすべて破棄
        for win in self.dummy_windows:
            win.close()
        self.dummy_windows.clear()

        # 2. ターゲットプロセス (main.py) を終了
        try:
            self.py_proc.kill()
        except Exception:
            pass
        self.main_process.kill()

        # 3. 統計計算
        if self.cpu_usages:
            valid_cpu = self.cpu_usages[1:] if len(self.cpu_usages) > 1 else self.cpu_usages
            avg_cpu = sum(valid_cpu) / len(valid_cpu)
            avg_mem = sum(self.mem_usages) / len(self.mem_usages)
        else:
            avg_cpu, avg_mem = 0, 0

        # スコアの算出 (100点満点からの減点方式)
        score = max(50, 100 - int(avg_cpu * 1.0))
        
        # 判定とアドバイスの決定
        if score >= 90:
            rank = "S ランク [極めて快適]\nS Rank [Extremely Comfortable]"
            rank_color = "#4caf50"  # 緑
            advice = "このPCなら、他の重い作業を同時に行っても、枠線は完全に滑らかに動作します。実用上全く問題ありません。\n(On this PC, the borders will run completely smoothly even if other heavy tasks are performed simultaneously. There are no practical issues.)"
        elif score >= 80:
            rank = "A ランク [快適]\nA Rank [Comfortable]"
            rank_color = "#00bcd4"  # 水色
            advice = "通常業務において、十分な応答性と滑らかな描画を維持できます。安心してご利用ください。\n(It can maintain sufficient responsiveness and smooth rendering in normal business operations. Please use it with confidence.)"
        elif score >= 70:
            rank = "B ランク [普通]\nB Rank [Normal]"
            rank_color = "#ffeb3b"  # 黄色
            advice = "実用可能です。もし動作にやや引っかかりを感じる場合は、設定画面から「線の太さ」を少し細くすると改善します。\n(It is practical for use. If you feel any slight stuttering, it can be improved by slightly reducing the 'Border Width' in the settings dialog.)"
        else:
            rank = "C ランク [要調整]\nC Rank [Adjustment Needed]"
            rank_color = "#f44336"  # 赤
            advice = "PCの描画処理にやや負荷がかかっています。設定画面で「線の太さ」を細くするか、「不透明度」を下げてご使用ください。\n(There is a slight load on the PC's drawing process. Please use it by narrowing the 'Border Width' or lowering the 'Opacity' in the settings dialog.)"

        # レイアウトをクリアして結果画面を再構築
        # 古いウィジェットの削除
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 結果UIの組み立て
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(10)

        # タイトル
        res_title = QLabel("ベンチマークテスト結果\nBenchmark Test Results")
        res_title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        res_title.setStyleSheet("color: #00bcd4;")
        res_title.setAlignment(Qt.AlignCenter)
        res_title.setWordWrap(True)
        self.layout.addWidget(res_title)

        # スコアとランク
        score_layout = QHBoxLayout()
        score_layout.setAlignment(Qt.AlignCenter)
        
        score_label = QLabel(f"スコア: {score}点 (Score: {score})")
        score_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        score_layout.addWidget(score_label)
        self.layout.addLayout(score_layout)

        rank_label = QLabel(rank)
        rank_label.setFont(QFont("Segoe UI", 15, QFont.Bold))
        rank_label.setStyleSheet(f"color: {rank_color};")
        rank_label.setAlignment(Qt.AlignCenter)
        rank_label.setWordWrap(True)
        self.layout.addWidget(rank_label)

        # 境界線
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #444;")
        self.layout.addWidget(line)

        # 統計詳細
        stats_layout = QVBoxLayout()
        stats_layout.addWidget(QLabel(f"・ 平均CPU負荷 (Average CPU Load): {avg_cpu:.1f} %"))
        stats_layout.addWidget(QLabel(f"・ 平均メモリ使用量 (Average Memory Usage): {avg_mem:.1f} MB"))
        
        load_lbl = QLabel(
            "・ テスト負荷: ウィンドウ50個の重ね合わせと高速描画\n"
            "  (Test Load: 50 overlapping windows moving at high speed)"
        )
        load_lbl.setWordWrap(True)
        stats_layout.addWidget(load_lbl)
        self.layout.addLayout(stats_layout)

        # アドバイス
        adv_title = QLabel("■ 動作アドバイス (Operation Advice):")
        adv_title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.layout.addWidget(adv_title)
        
        adv_text = QLabel(advice)
        adv_text.setWordWrap(True)
        adv_text.setStyleSheet("color: #b0b0b0; font-size: 13px;")
        self.layout.addWidget(adv_text)

        # 技術的注意書きの追加
        note_title = QLabel("※ ベンチマークに関する注意点 (Notes on Benchmark):")
        note_title.setFont(QFont("Segoe UI", 10, QFont.Bold))
        note_title.setStyleSheet("color: #888; margin-top: 5px;")
        self.layout.addWidget(note_title)
        
        note_text = QLabel(
            "・主にCPUの2D描画処理能力で測定しています（GPUの3D性能は測定対象外です）\n"
            "  (Mainly measures the CPU's 2D rendering capability; GPU 3D performance is not measured)\n"
            "・表示画面解像度の影響を大きく受けます（4Kなどの高解像度表示では得点が下がります）\n"
            "  (Highly affected by display resolution; scores will decrease in high resolutions like 4K)"
        )
        note_text.setWordWrap(True)
        note_text.setStyleSheet("color: #777; font-size: 11px;")
        self.layout.addWidget(note_text)

        # 閉じるボタン
        close_btn = QPushButton("ベンチマークを閉じる (Close Benchmark)")
        close_btn.clicked.connect(self.close)
        self.layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        # UI要素を完全に表示するためにウィンドウサイズを更新
        self.resize(550, 900)


def main():
    # 1. ターゲットプログラム (main.py) をバックグラウンドで起動
    process = subprocess.Popen([sys.executable, MAIN_SCRIPT])
    time.sleep(2)  # 起動待機

    # プロセスのスキャン
    py_proc = None
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if p.info['name'].lower().startswith('python') and any(
                "main.py" in arg for arg in p.info['cmdline'] or []
            ):
                py_proc = psutil.Process(p.info['pid'])
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not py_proc:
        print("[Error] main.py のプロセスを検出できませんでした。")
        process.kill()
        return

    # 2. ダミーウィンドウの大量生成
    # ベンチマーク画面を描画するために QApplication を作成
    app = QApplication(sys.argv)

    # 起動確認ダイアログの表示 (QMessageBox)
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Question)
    msg_box.setWindowTitle("Confirmation")
    msg_box.setText("「WindowBorderTool」を終了していますか？\nHas \"WindowBorderTool\" been closed?")
    msg_box.setStandardButtons(QMessageBox.Ok)
    msg_box.setDefaultButton(QMessageBox.Ok)
    msg_box.exec()

    dummy_windows = []
    # 50個のウィンドウを生成してばら撒く
    for i in range(50):
        # 最初の5個だけを60FPSで高速移動させて描画負荷をかける
        speed_x = 0
        speed_y = 0
        if i < 5:
            speed_x = random.choice([-8, -5, 5, 8])
            speed_y = random.choice([-8, -5, 5, 8])

        win = DummyWindow(i, speed_x, speed_y)
        screen = app.primaryScreen().geometry()
        rx = random.randint(50, screen.width() - 350)
        ry = random.randint(50, screen.height() - 250)
        win.move(rx, ry)
        win.show()
        dummy_windows.append(win)

    # 3. ベンチマークウィンドウの表示
    bench_win = BenchmarkWindow(process, py_proc, dummy_windows)
    bench_win.show()

    # Qtのイベントループ開始
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

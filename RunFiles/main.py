import sys
import os
import json
import win32gui
import win32con
import ctypes
from PySide6.QtWidgets import (
    QApplication, QWidget, QSystemTrayIcon, QMenu,
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QColorDialog
)
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QPixmap, QRegion
from PySide6.QtCore import Qt, QTimer, QRect

# DWM APIのロード (Windows固有の不可視ウィンドウを除外するため)
dwmapi = ctypes.windll.dwmapi
DWMWA_CLOAKED = 14

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")


def enum_windows(exclude_hwnd=None):
    windows = []

    def callback(hwnd, extra):
        # 自身（オーバーレイ）のウィンドウは除外
        if exclude_hwnd and hwnd == exclude_hwnd:
            return

        # 非表示のウィンドウは除外
        if not win32gui.IsWindowVisible(hwnd):
            return

        # 最小化されているウィンドウは除外
        if win32gui.IsIconic(hwnd):
            return

        # ウィンドウタイトルが空のものは除外
        title = win32gui.GetWindowText(hwnd)
        if title == "":
            return

        # デスクトップの背景やタスクバーなどのシステムウィンドウ、および透明なオーバーレイを除外
        class_name = win32gui.GetClassName(hwnd)
        if class_name in [
            "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
            "MousePointerCrosshairs", "CEF-OSC-WIDGET"
        ]:
            return

        # DWMによってクローク（非表示・別デスクトップ・UWPの非活性状態）されている窓を除外
        cloaked = ctypes.c_int(0)
        hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        if hr == 0 and cloaked.value != 0:
            return

        # ウィンドウの位置とサイズを取得
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        # 極端に小さいウィンドウを除外
        if right - left < 50 or bottom - top < 50:
            return

        windows.append((left, top, right, bottom))

    win32gui.EnumWindows(callback, None)
    return windows


class SettingsDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.overlay = parent
        self.setWindowTitle("設定")
        # 設定画面も常に最前面にして埋もれないようにする
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)

        # キャンセル時の復元用に現在の値を保持
        self.orig_color = QColor(self.overlay.line_color)
        self.orig_width = self.overlay.line_width
        self.orig_alpha_pct = self.overlay.line_alpha_pct

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # --- 色の選択 ---
        color_layout = QHBoxLayout()
        color_label = QLabel("枠線の色:")
        self.color_btn = QPushButton("色を選択...")
        self.update_color_button_preview(self.overlay.line_color)
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_btn)
        layout.addLayout(color_layout)

        # --- 太さ調整 (1 - 40 px) ---
        width_layout = QHBoxLayout()
        width_label = QLabel("線の太さ (1-40 px):")
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setRange(1, 40)
        self.width_slider.setValue(self.overlay.line_width)
        self.width_val_label = QLabel(f"{self.overlay.line_width} px")
        self.width_slider.valueChanged.connect(self.on_width_changed)
        width_layout.addWidget(width_label)
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_val_label)
        layout.addLayout(width_layout)

        # --- 透明度調整 (0 - 100 %) ---
        alpha_layout = QHBoxLayout()
        alpha_label = QLabel("不透明度 (0-100 %):")
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(self.overlay.line_alpha_pct)
        self.alpha_val_label = QLabel(f"{self.overlay.line_alpha_pct} %")
        self.alpha_slider.valueChanged.connect(self.on_alpha_changed)
        alpha_layout.addWidget(alpha_label)
        alpha_layout.addWidget(self.alpha_slider)
        alpha_layout.addWidget(self.alpha_val_label)
        layout.addLayout(alpha_layout)

        # --- 保存・キャンセルボタン ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.cancel_settings)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def update_color_button_preview(self, color):
        # ボタンの背景色を選択された色でプレビュー表示する
        self.color_btn.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"color: {'black' if color.lightness() > 128 else 'white'}; "
            f"font-weight: bold; border: 1px solid gray; padding: 5px;"
        )

    def choose_color(self):
        # カラーピッカーを開く
        color = QColorDialog.getColor(self.overlay.line_color, self, "枠線の色を選択")
        if color.isValid():
            self.overlay.line_color = color
            self.update_color_button_preview(color)
            self.overlay.update()  # リアルタイム反映

    def on_width_changed(self, value):
        self.width_val_label.setText(f"{value} px")
        self.overlay.line_width = value
        self.overlay.update()  # リアルタイム反映

    def on_alpha_changed(self, value):
        self.alpha_val_label.setText(f"{value} %")
        self.overlay.line_alpha_pct = value
        self.overlay.line_alpha = int(value * 2.55)  # 0-100% から 0-255 へ変換
        self.overlay.update()  # リアルタイム反映

    def save_settings(self):
        # 設定をJSONに保存
        settings = {
            "line_color": [self.overlay.line_color.red(), self.overlay.line_color.green(), self.overlay.line_color.blue()],
            "line_width": self.overlay.line_width,
            "line_alpha_pct": self.overlay.line_alpha_pct
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
        self.accept()

    def cancel_settings(self):
        # 設定を元の状態にロールバック
        self.overlay.line_color = self.orig_color
        self.overlay.line_width = self.orig_width
        self.overlay.line_alpha_pct = self.orig_alpha_pct
        self.overlay.line_alpha = int(self.orig_alpha_pct * 2.55)
        self.overlay.update()
        self.reject()


class Overlay(QWidget):

    def __init__(self):
        super().__init__()

        # デフォルト設定値
        self.line_color = QColor(255, 255, 0)  # 黄色
        self.line_width = 10
        self.line_alpha_pct = 80
        self.line_alpha = int(self.line_alpha_pct * 2.55)
        self.update_interval_ms = 33

        # 設定ファイルのロード
        self.load_settings()

        # 最前面表示、枠なし、ツールウィンドウ属性を設定
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
        )

        # 背景を透明化し、マウスイベントを透過させる
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 画面全体のサイズを取得して設定
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.windows = []

        # 自身のウィンドウハンドル (HWND) を取得し、除外用に保持
        self.my_hwnd = int(self.winId())

        # システムトレイアイコンのセットアップ
        self.setup_tray_icon()

        # 定期更新タイマーの開始
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_windows)
        self.timer.start(self.update_interval_ms)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    c = settings.get("line_color", [255, 255, 0])
                    self.line_color = QColor(c[0], c[1], c[2])
                    self.line_width = max(1, min(40, settings.get("line_width", 10)))
                    self.line_alpha_pct = max(0, min(100, settings.get("line_alpha_pct", 80)))
                    self.line_alpha = int(self.line_alpha_pct * 2.55)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # 枠線色と同じ色の16x16ピクセルの正方形アイコンを動的生成
        pixmap = QPixmap(16, 16)
        pixmap.fill(self.line_color)
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Window枠強調ツール")

        # 右クリックメニューの作成
        tray_menu = QMenu()
        
        # 設定アクションの追加
        settings_action = tray_menu.addAction("設定...")
        settings_action.triggered.connect(self.show_settings)
        
        tray_menu.addSeparator()
        
        # 終了アクション
        exit_action = tray_menu.addAction("終了")
        exit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_settings(self):
        # 設定ダイアログを表示
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # 保存されて設定が変わった場合、トレイアイコンの色も同期更新する
            pixmap = QPixmap(16, 16)
            pixmap.fill(self.line_color)
            self.tray_icon.setIcon(QIcon(pixmap))

    def keyPressEvent(self, event):
        # 念のためEscキーが押された際も終了するように設定
        if event.key() == Qt.Key_Escape:
            QApplication.quit()

    def update_windows(self):
        self.windows = enum_windows(exclude_hwnd=self.my_hwnd)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 読み込まれている設定に基づいてペンを作成
        pen = QPen(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), self.line_alpha))
        pen.setWidth(self.line_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        covered_region = QRegion()

        overlay_rect = self.geometry()
        ox, oy = overlay_rect.x(), overlay_rect.y()

        for l, t, r, b in self.windows:
            local_l = l - ox
            local_t = t - oy
            local_w = r - l
            local_h = b - t
            local_rect = QRect(local_l, local_t, local_w, local_h)

            expanded_rect = local_rect.adjusted(-self.line_width, -self.line_width, self.line_width, self.line_width)
            window_region = QRegion(expanded_rect)

            visible_region = window_region.subtracted(covered_region)

            painter.save()
            painter.setClipRegion(visible_region)
            painter.drawRect(local_rect)
            painter.restore()

            covered_region = covered_region.united(QRegion(local_rect))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = Overlay()
    overlay.showFullScreen()
    sys.exit(app.exec())

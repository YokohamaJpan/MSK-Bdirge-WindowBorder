import sys
import os
import time
import win32gui
import win32con
import ctypes
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QRegion
from PySide6.QtCore import QTimer, QRect, Qt

# DWM API
dwmapi = ctypes.windll.dwmapi
DWMWA_CLOAKED = 14


class SingleOverlay(QWidget):

    def __init__(self, target_hwnd):
        super().__init__()
        self.target_hwnd = target_hwnd
        self.line_width = 10
        self.line_color = QColor(0, 255, 0)  # 緑色で描画 (プロトタイプ識別用)
        self.line_alpha = 200

        # 個別窓用のウィンドウフラグ (Toolかつフォーカス拒否、入力透過)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.my_hwnd = int(self.winId())

        # 100ms周期の同期タイマー (秒間10回)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_position)
        self.timer.start(100)

        self.sync_position()

    def sync_position(self):
        # ターゲットウィンドウが消失したかチェック
        if not win32gui.IsWindow(self.target_hwnd) or not win32gui.IsWindowVisible(self.target_hwnd):
            print("Target window closed or minimized. Exiting prototype.")
            QApplication.quit()
            return

        try:
            # ターゲットの位置とサイズを取得
            l, t, r, b = win32gui.GetWindowRect(self.target_hwnd)
            w = r - l
            h = b - t

            # 枠線の太さ分のマージンを考慮して配置座標を計算
            offset = self.line_width // 2 + 1
            ox = l - offset
            oy = t - offset
            ow = w + offset * 2
            oh = h + offset * 2

            # 位置とサイズを同期
            self.setGeometry(ox, oy, ow, oh)

            # マスク処理：中央部分（対象ウィンドウの本体領域）を透過除外する
            outer = QRegion(0, 0, ow, oh)
            inner = QRegion(offset, offset, w, h)
            mask = outer.subtracted(inner)
            self.setMask(mask)

            # Zオーダー of 物理同期（対象ウィンドウの「直上」に差し込む）
            win32gui.SetWindowPos(
                self.my_hwnd,
                self.target_hwnd,
                ox, oy, ow, oh,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )

        except Exception as e:
            print(f"Sync error: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 枠線のみを描画
        pen = QPen(QColor(self.line_color.red(), self.line_color.green(), self.line_color.blue(), self.line_alpha))
        pen.setWidth(self.line_width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        offset = self.line_width // 2 + 1
        painter.drawRect(offset, offset, self.width() - offset * 2, self.height() - offset * 2)


def find_initial_target():
    # ユーザーがターゲット窓（例: メモ帳）を前面にするための猶予時間
    time.sleep(2)
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    class_name = win32gui.GetClassName(hwnd)

    if class_name in ["Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"]:
        return None, "Invalid target"
    return hwnd, title


if __name__ == "__main__":
    print("==================================================")
    print("  個別オーバーレイ方式 技術検証プロトタイプ")
    print(" 2秒後、アクティブなウィンドウに枠線(緑)を同期します...")
    print("==================================================")

    app = QApplication(sys.argv)

    hwnd, title = find_initial_target()
    if not hwnd:
        print("[Error] 通常アプリケーションウィンドウをアクティブにした状態で実行してください。")
        sys.exit(1)

    print(f"-> ターゲット検知: '{title}' (HWND: {hwnd})")

    overlay = SingleOverlay(hwnd)
    overlay.show()

    sys.exit(app.exec())

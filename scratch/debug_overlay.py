import sys
import os
import time
import win32gui
import win32con
import ctypes
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import QTimer, Qt

# DWM API
dwmapi = ctypes.windll.dwmapi
DWMWA_CLOAKED = 14


class TestOverlay(QWidget):

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

        # 初期フラグ設定
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.my_hwnd = int(self.winId())

        # 1秒ごとにステータスを監視するタイマー
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.monitor_status)
        self.monitor_timer.start(1000)
        self.elapsed = 0

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_native_style()

    def apply_native_style(self):
        try:
            style = win32gui.GetWindowLong(self.my_hwnd, win32con.GWL_EXSTYLE)
            target_style = style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_NOACTIVATE | win32con.WS_EX_LAYERED
            win32gui.SetWindowLong(self.my_hwnd, win32con.GWL_EXSTYLE, target_style)
            
            # SWP_FRAMECHANGED を呼んでスタイル適用をシステムに強制通知
            win32gui.SetWindowPos(
                self.my_hwnd, win32con.HWND_TOPMOST, 
                0, 0, 0, 0, 
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_FRAMECHANGED
            )
        except Exception as e:
            print(f"Error setting style: {e}")

    def monitor_status(self):
        self.elapsed += 1
        try:
            # 1. 現在のウィンドウ拡張スタイルを取得して検証
            style = win32gui.GetWindowLong(self.my_hwnd, win32con.GWL_EXSTYLE)
            has_transparent = bool(style & win32con.WS_EX_TRANSPARENT)
            has_noactivate = bool(style & win32con.WS_EX_NOACTIVATE)
            has_layered = bool(style & win32con.WS_EX_LAYERED)

            # 2. 現在最前面でアクティブになっているウィンドウの情報を取得
            fg_hwnd = win32gui.GetForegroundWindow()
            fg_title = win32gui.GetWindowText(fg_hwnd)
            fg_class = win32gui.GetClassName(fg_hwnd)
            is_me_active = (fg_hwnd == self.my_hwnd)

            print(f"[{self.elapsed}s] Style: TRANSPARENT={has_transparent}, NOACTIVATE={has_noactivate}, LAYERED={has_layered} | Active Window: '{fg_title}' ({fg_class}) {'[ME]' if is_me_active else ''}")
        except Exception as e:
            print(f"Monitor error: {e}")

        if self.elapsed >= 10:
            print("Monitoring finished.")
            QApplication.quit()

    def paintEvent(self, event):
        if self.mode == "nopaint":
            return  # 描画処理をスキップ

        # ダミー枠線の描画
        painter = QPainter(self)
        pen = QPen(QColor(255, 0, 0, 200))
        pen.setWidth(10)
        painter.setPen(pen)
        painter.drawRect(100, 100, 400, 300)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"Starting test overlay in mode: '{mode}'")
    app = QApplication(sys.argv)
    overlay = TestOverlay(mode)
    overlay.show()
    sys.exit(app.exec())

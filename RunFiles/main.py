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

        # ウィンドウスタイルの取得
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # 子ウィンドウは除外
        if style & win32con.WS_CHILD:
            return

        # ツールウィンドウは除外
        if exstyle & win32con.WS_EX_TOOLWINDOW:
            return

        # デスクトップの背景やタスクバーなどのシステムウィンドウ、および透明なオーバーレイを除外
        class_name = win32gui.GetClassName(hwnd)
        if class_name in [
            "Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
            "MousePointerCrosshairs", "CEF-OSC-WIDGET",
            "SHELLDLL_DefView", "SysListView32",
            "DesktopWindowXamlSource", "Windows.UI.Core.CoreWindow"
        ]:
            return

        # DWMによってクロークされている窓を除外
        cloaked = ctypes.c_int(0)
        hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
        if hr == 0 and cloaked.value != 0:
            return

        # ウィンドウの位置とサイズを取得
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)

        # 極端に小さいウィンドウを除外
        if right - left < 50 or bottom - top < 50:
            return

        # HWNDも格納して返す
        windows.append((hwnd, left, top, right, bottom))

    win32gui.EnumWindows(callback, None)
    return windows


class SettingsDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.overlay = parent  # 管理クラス (Overlay)
        self.setWindowTitle("設定")
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
        self.color_btn.setStyleSheet(
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"color: {'black' if color.lightness() > 128 else 'white'}; "
            f"font-weight: bold; border: 1px solid gray; padding: 5px;"
        )

    def choose_color(self):
        color = QColorDialog.getColor(self.overlay.line_color, self, "枠線の色を選択")
        if color.isValid():
            self.overlay.line_color = color
            self.update_color_button_preview(color)
            self.overlay.update_all_overlays_style()

    def on_width_changed(self, value):
        self.width_val_label.setText(f"{value} px")
        self.overlay.line_width = value
        self.overlay.update_all_overlays_style()

    def on_alpha_changed(self, value):
        self.alpha_val_label.setText(f"{value} %")
        self.overlay.line_alpha_pct = value
        self.overlay.update_all_overlays_style()

    def save_settings(self):
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
        self.overlay.line_color = self.orig_color
        self.overlay.line_width = self.orig_width
        self.overlay.line_alpha_pct = self.orig_alpha_pct
        self.overlay.update_all_overlays_style()
        self.reject()


class WindowOverlay(QWidget):
    """個々の通常ウィンドウに追従する枠線のみのオーバーレイ"""

    def __init__(self, target_hwnd, manager):
        super().__init__()
        self.target_hwnd = target_hwnd
        self.manager = manager

        # 枠なし、ツールウィンドウ、入力透過、フォーカス拒否を設定
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
        self.sync_position()

    def sync_position(self):
        try:
            # ターゲット位置とサイズを取得
            l, t, r, b = win32gui.GetWindowRect(self.target_hwnd)
            w = r - l
            h = b - t

            # 枠線幅をそのまま余白にする
            offset = self.manager.line_width
            ox = l - offset
            oy = t - offset
            ow = w + offset * 2
            oh = h + offset * 2

            self.setGeometry(ox, oy, ow, oh)

            # マスク処理：アプリ領域（offset以降）を透過
            outer = QRegion(0, 0, ow, oh)
            inner = QRegion(offset, offset, w, h)
            mask = outer.subtracted(inner)
            self.setMask(mask)

            # Zオーダーの物理同期 (対象ウィンドウの直上、アクティブ化しない)
            win32gui.SetWindowPos(
                self.my_hwnd,
                self.target_hwnd,
                ox, oy, ow, oh,
                win32con.SWP_NOACTIVATE | win32con.SWP_SHOWWINDOW
            )
        except Exception:
            pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = self.manager.line_color
        alpha = self.manager.line_alpha
        width = self.manager.line_width

        pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha))
        pen.setWidth(width)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        half_w = width / 2.0
        painter.drawRect(half_w, half_w, self.width() - width, self.height() - width)


class Overlay(QWidget):
    """トレイメニューと全オーバーレイを管理する隠し管理者クラス"""

    def __init__(self):
        super().__init__()

        # デフォルト設定
        self.line_color = QColor(255, 255, 0)
        self.line_width = 10
        self.line_alpha_pct = 80
        self.line_alpha = int(self.line_alpha_pct * 2.55)
        self.update_interval_ms = 100  # 100ms周期

        self.load_settings()

        # 管理クラス自身は非表示のQObjectのように振る舞わせるため、画面外の最小サイズにする
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, 1, 1)

        self.my_hwnd = int(self.winId())
        self.overlays = {}  # target_hwnd -> WindowOverlay オブジェクト

        # システムトレイのセットアップ
        self.setup_tray_icon()

        # 100msごとに同期を行う一括タイマー
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

        pixmap = QPixmap(16, 16)
        pixmap.fill(self.line_color)
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Window枠拡張ツール")

        tray_menu = QMenu()
        settings_action = tray_menu.addAction("設定...")
        settings_action.triggered.connect(self.show_settings)

        tray_menu.addSeparator()

        exit_action = tray_menu.addAction("終了")
        exit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            pixmap = QPixmap(16, 16)
            pixmap.fill(self.line_color)
            self.tray_icon.setIcon(QIcon(pixmap))

    def update_all_overlays_style(self):
        self.line_alpha = int(self.line_alpha_pct * 2.55)
        # 全個別オーバーレイの描画スタイルを同期更新
        for w_overlay in self.overlays.values():
            w_overlay.update()

    def update_windows(self):
        # 現在のアクティブな通常ウィンドウをスキャン
        current_windows = enum_windows(exclude_hwnd=self.my_hwnd)
        current_hwnds = {w[0] for w in current_windows}

        # 1. 消失したウィンドウのオーバーレイを破棄
        for hwnd in list(self.overlays.keys()):
            if hwnd not in current_hwnds:
                self.overlays[hwnd].close()
                self.overlays[hwnd].deleteLater()
                del self.overlays[hwnd]

        # 2. 新規ウィンドウの生成 ＆ 既存の追従同期
        for hwnd, l, t, r, b in current_windows:
            # 最小化中の場合は非表示にする
            if win32gui.IsIconic(hwnd):
                if hwnd in self.overlays:
                    self.overlays[hwnd].hide()
                continue

            if hwnd not in self.overlays:
                self.overlays[hwnd] = WindowOverlay(hwnd, self)

            self.overlays[hwnd].sync_position()
            self.overlays[hwnd].show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = Overlay()
    overlay.show()
    sys.exit(app.exec())

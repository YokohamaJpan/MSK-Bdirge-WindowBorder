# Window Border Tool (WindowBorderTool) - v1.0

[日本語版説明書 (Japanese)](README_JA.md)

An accessibility support tool that draws a thick border around all window boundaries to make them visually distinct on your desktop. Designed for low-vision individuals, seniors, or anyone who finds modern flat designs hard to distinguish.

---

## 🌱 Purpose & Philosophy

> **"Solve information-related disabilities systematically, not through the struggles of individuals."**

We aim to remove barriers for people with visual, auditory, or cognitive information-based disabilities by utilizing technology systematically, rather than relying on individual effort and patience ("trying harder to see/hear").

This project is the very first step toward this grand goal under the name of **"MSK-Bdirge"**.

The developer himself has long struggled with the difficulty of distinguishing window boundaries in Windows. This tool was created to solve such daily barriers with technology, realizing a world where everyone can operate a PC stress-free and intuitively.

---

## 🚀 Features
- **Security-Friendly & Corporate Ready**: It runs as open-source Python scripts (.py) rather than binary executables (.exe). It is less likely to be blocked by corporate security policies and easily passes IT safety audits (Requires no admin rights if Python is installed).
- **Intuitive Settings Dialog**: Easily open the configuration window from the system tray icon to change line thickness (1-40px), color, and opacity (0-100%) in real-time.

---

## 📂 How to Run

### ① First Time (Initial Setup)
1. Double-click **`Setup_and_Run.bat`** in the folder.
2. A console window will open, automatically install the required libraries (PySide6, pywin32), and then start the application.
   - *Note: Requires an internet connection.*
   - *Note: It may take 30 to 60 seconds to complete the library installation on the first run.*

### ② Subsequent Runs
1. Double-click **`WindowBorderTool.bat`** in the folder.
2. The borders will be drawn around all windows immediately.

---

## ⚙️ How to Change Settings
1. Right-click the **square icon (WindowBorderTool)** in the system tray (taskbar bottom-right).
2. Select **"設定..." (Settings)** from the menu.
3. The settings dialog will open. Adjust thickness, opacity, and color, then click "保存" (Save) to apply changes.
   - *Note: Changes will be previewed on the screen in real-time.*
   - *Note: Clicking "キャンセル" (Cancel) will roll back any unsaved changes.*

---

## ❌ How to Exit
- Right-click the square icon in the system tray and select **"終了" (Exit)**.
- Alternatively, close the black console window (command prompt) by clicking the **"X" close button** at the top-right of that window.

---

## 🛠️ Debug Mode
If you experience any issues or wish to view detailed exception logs for troubleshooting:
1. Open **`WindowBorderTool.bat`** with a text editor.
2. Change `set DEBUG_MODE=0` to `set DEBUG_MODE=1` and save the file.
3. Upon running the tool, the console window will display detailed log messages (such as exception errors).
   - *Note: You can also temporarily launch in debug mode by passing a command-line argument (e.g., run `WindowBorderTool.bat debug` in cmd/PowerShell).*

---

## ⚠️ Notes and Specifications
- **Directory Structure**:
  - You can rename the folder (e.g., to `WindowBorderTool`) or move it anywhere you like.
  - However, **do not change the files inside the folder** (`main.py`, `settings.json`, `WindowBorderTool.bat`), as the relative paths between them must remain intact for the application to start.
- **Multi-Monitor Environments**:
  - Under the current specifications, borders are only displayed on the primary monitor. They will not appear on secondary displays.

# 文件: main.py (已修改为自适应窗口)

import sys
from PyQt5.QtWidgets import QApplication

from ui_mainwindow import MainWindow
from ui_styles import MODERN_STYLE

def main():
    """程序主入口"""
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLE)
    
    # --- 窗口尺寸自适应 ---
    # 获取主屏幕的分辨率
    screen_geometry = app.primaryScreen().geometry()
    # 计算一个合适的初始尺寸，例如屏幕的70%
    initial_width = int(screen_geometry.width() * 0.7)
    initial_height = int(screen_geometry.height() * 0.7)
    
    main_window = MainWindow()
    main_window.resize(initial_width, initial_height) # 使用resize而不是setGeometry
    
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
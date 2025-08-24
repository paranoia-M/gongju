# 文件: main.py

import sys
from PyQt5.QtWidgets import QApplication

# 从同级目录导入主窗口类和样式
from ui_mainwindow import MainWindow
from ui_styles import MODERN_STYLE

def main():
    """程序主入口"""
    app = QApplication(sys.argv)
    
    # 应用统一样式表
    app.setStyleSheet(MODERN_STYLE)
    
    # 创建并显示主窗口
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
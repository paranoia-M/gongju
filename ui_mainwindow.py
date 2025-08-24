# 文件: ui_mainwindow.py (已修正)

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QListWidget, QStackedWidget
)

# 导入功能模块和工具
from modules.pdf_merger import PdfMergerWidget
from utils import Stream

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF 工具箱 v1.0')
        self.setGeometry(100, 100, 850, 600)

        # 【修正】调整了调用顺序
        self.setup_logging()  # 1. 先设置日志流，创建 self.stream
        self.initUI()         # 2. 再初始化UI，此时可以安全地触发 change_page

    def initUI(self):
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 左侧菜单栏
        self.menu_widget = QListWidget()
        main_layout.addWidget(self.menu_widget, 1)

        # 2. 右侧内容区
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 4)

        # 3. 添加功能模块
        self.add_module("PDF 合并", PdfMergerWidget())
        self.add_module("PDF 拆分 (开发中)", self.create_placeholder_widget("PDF 拆分"))
        self.add_module("PDF 加水印 (开发中)", self.create_placeholder_widget("PDF 加水印"))
        
        # 4. 连接菜单切换事件
        self.menu_widget.currentRowChanged.connect(self.change_page)
        
        # 5. 设置默认选中的页面 (这会第一次触发 change_page)
        self.menu_widget.setCurrentRow(0)

    def add_module(self, name, widget):
        """向主窗口添加一个功能模块"""
        self.menu_widget.addItem(name)
        self.stacked_widget.addWidget(widget)

    def create_placeholder_widget(self, feature_name):
        """创建一个占位符页面"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        label = QLabel(f"{feature_name}功能正在紧张开发中，敬请期待！")
        label.setStyleSheet("font-size: 16px; color: #888; text-align: center;")
        layout.addWidget(label)
        return widget

    def change_page(self, index):
        """切换右侧显示的功能页面"""
        self.stacked_widget.setCurrentIndex(index)
        current_widget = self.stacked_widget.widget(index)

        # 动态地将日志流连接到当前活动模块的on_update_text方法
        try: 
            # 在操作前先断开所有可能的旧连接，防止重复连接
            self.stream.newText.disconnect()
        except TypeError: 
            # 如果之前没有连接，会抛出TypeError，这是正常的，直接忽略
            pass
        
        if hasattr(current_widget, 'on_update_text'):
            # 如果新页面有日志接收方法，则连接它
            self.stream.newText.connect(current_widget.on_update_text)

    def setup_logging(self):
        """设置日志重定向"""
        self.stream = Stream()
        sys.stdout = self.stream
        sys.stderr = self.stream
        # 【修正】移除这里的 change_page(0) 调用，因为它在 initUI 中处理更合适

    def closeEvent(self, event):
        """关闭窗口时恢复标准输出"""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)
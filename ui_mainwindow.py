# 文件: ui_mainwindow.py (最终整合版)

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QLabel, QListWidget, QStackedWidget
)

# 导入所有功能模块和通用工具
from modules.pdf_merger import PdfMergerWidget
from modules.patent_splitter import PatentSplitterWidget # 导入新功能模块
from utils import Stream

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF 工具箱 v1.0')
        self.setGeometry(100, 100, 850, 600)

        # 先设置日志流，再初始化UI，防止启动时出错
        self.setup_logging()
        self.initUI()

    def initUI(self):
        """初始化主窗口的UI布局和控件"""
        # 创建中央容器和主水平布局
        container = QWidget()
        self.setCentralWidget(container)
        main_layout = QHBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. 左侧菜单栏 (QListWidget)
        self.menu_widget = QListWidget()
        main_layout.addWidget(self.menu_widget, 1) # 设置伸缩比例为1

        # 2. 右侧内容区 (QStackedWidget)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 4) # 设置伸缩比例为4

        # 3. 添加所有功能模块到窗口中
        self.add_module("PDF 合并", PdfMergerWidget())
        self.add_module("专利五书分割", PatentSplitterWidget()) # 加载新功能
        self.add_module("其他功能 (开发中)", self.create_placeholder_widget("PDF 其他功能"))
        
        # 4. 连接菜单点击事件，并设置默认显示第一个功能
        self.menu_widget.currentRowChanged.connect(self.change_page)
        self.menu_widget.setCurrentRow(0)

    def add_module(self, name, widget):
        """一个辅助函数，用于向菜单和内容区添加一个新模块"""
        self.menu_widget.addItem(name)
        self.stacked_widget.addWidget(widget)

    def create_placeholder_widget(self, feature_name):
        """创建一个占位符页面，用于未开发的功能"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        label = QLabel(f"{feature_name}功能正在紧张开发中，敬请期待！")
        label.setStyleSheet("font-size: 16px; color: #888;")
        layout.addWidget(label)
        return widget

    def change_page(self, index):
        """
        当用户点击左侧菜单时，切换右侧显示的功能页面。
        同时，动态地将日志流重新连接到当前活动模块的日志接收方法。
        """
        self.stacked_widget.setCurrentIndex(index)
        current_widget = self.stacked_widget.widget(index)

        # 断开之前可能存在的连接，防止日志重复输出
        try: 
            self.stream.newText.disconnect()
        except TypeError: 
            # 如果之前没有连接，会抛出TypeError，这是正常的，直接忽略
            pass
        
        # 检查新页面是否有 on_update_text 方法，如果有，则连接日志流
        if hasattr(current_widget, 'on_update_text'):
            self.stream.newText.connect(current_widget.on_update_text)

    def setup_logging(self):
        """
        设置日志重定向。
        将Python的 print() 输出（标准输出和标准错误）重定向到一个自定义的信号流。
        """
        self.stream = Stream()
        sys.stdout = self.stream
        sys.stderr = self.stream

    def closeEvent(self, event):
        """在关闭应用程序窗口时，恢复标准的输出流，避免影响其他程序"""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)
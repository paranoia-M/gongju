# 文件: modules/pdf_splitter.py

import os
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit, QMessageBox, QFrame, QCheckBox
)
from PyQt5.QtCore import QThread

from utils import Worker

# ==============================================================================
# ==                       后端核心逻辑 (适配GUI版)                           ==
# ==============================================================================

def split_pdf_task(input_path, page_range_str, output_path=None):
    """
    根据指定的物理页码范围拆分一个PDF文件 (GUI适配版)。
    """
    if not os.path.isfile(input_path):
        print(f"错误: 输入文件不存在 -> '{input_path}'")
        return

    try:
        input_doc = fitz.open(input_path)
    except Exception as e:
        print(f"错误: 无法打开或解析PDF文件 '{input_path}'. 文件可能已损坏或受密码保护。\n详细信息: {e}")
        return

    total_pages = len(input_doc)
    print(f"源文件 '{os.path.basename(input_path)}' 共 {total_pages} 页 (物理页数)。")

    try:
        if not page_range_str.strip():
            raise ValueError("页码范围不能为空。")
        
        if '-' in page_range_str:
            start_str, end_str = page_range_str.split('-', 1)
            start = int(start_str) if start_str else 1
            end = int(end_str) if end_str else total_pages
        else:
            start = int(page_range_str)
            end = start

        if start > end:
            print(f"错误: 起始页码 ({start}) 不能大于结束页码 ({end})。")
            input_doc.close()
            return

        if start < 1 or end > total_pages:
            print(f"错误: 页码范围 '{page_range_str}' 无效。有效的物理页码范围是 1 到 {total_pages}。")
            input_doc.close()
            return
            
    except ValueError:
        print(f"错误: 无效的页码格式 '{page_range_str}'。请使用 '5-10', '7', '12-' 或 '-5' 这样的格式。")
        input_doc.close()
        return

    from_page, to_page = start - 1, end - 1
    print(f"\n准备提取物理页码从 {start} 到 {end} 的页面...")
    output_doc = fitz.open()
    output_doc.insert_pdf(input_doc, from_page=from_page, to_page=to_page)

    if not output_path:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_dir = os.path.dirname(os.path.abspath(input_path))
        output_filename = f"{base_name}_pages_{start}-{end}.pdf"
        output_path = os.path.join(output_dir, output_filename)
    elif not output_path.lower().endswith('.pdf'):
        output_path += '.pdf'

    try:
        output_doc.save(output_path, garbage=4, deflate=True, clean=True)
        print("\n[成功] PDF拆分完成！")
        print(f"已提取 {len(output_doc)} 个页面。")
        print(f"新文件已保存至: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"\n[错误] 保存文件时出错: {e}")
    finally:
        input_doc.close()
        output_doc.close()

# ==============================================================================
# ==                      PDF拆分功能的UI面板 (QWidget)                       ==
# ==============================================================================
class PdfSplitterWidget(QWidget):
    def __init__(self):
        super().__init__()
        class SplitterWorker(Worker):
            def __init__(self, **kwargs): super().__init__(task_function=split_pdf_task, **kwargs)
        self.worker_class = SplitterWorker
        self.initUI()
        self.toggle_output_mode(self.auto_output_check.isChecked())

    def on_update_text(self, text):
        self.log_console.moveCursor(self.log_console.textCursor().End)
        self.log_console.insertPlainText(text)

    def initUI(self):
        # --- UI控件 ---
        self.input_path_edit = QLineEdit()
        self.input_browse_btn = QPushButton('选择文件...')
        self.page_range_edit = QLineEdit(); self.page_range_edit.setPlaceholderText("例如: 5-10, 7, 12-")
        self.output_path_edit = QLineEdit()
        self.output_browse_btn = QPushButton('另存为...')
        self.auto_output_check = QCheckBox('自动命名并保存在源文件目录')
        self.auto_output_check.setChecked(True)
        self.split_btn = QPushButton('开始拆分'); self.split_btn.setObjectName("MergeButton")
        self.log_console = QTextEdit(); self.log_console.setReadOnly(True)
        self.info_panel = QTextEdit(); self.info_panel.setReadOnly(True)
        self.info_panel.setHtml("""
            <h2 style='color: #409EFF;'>功能说明</h2>
            <p>本功能可以从一个PDF文件中，根据您指定的<b>物理页码</b>范围，提取并生成一个新的PDF文件。</p>
            <h3 style='color: #E6A23C;'>页码范围格式 (从1开始计数):</h3>
            <ul>
                <li><b><code>5-10</code></b> : 提取第 5 页到第 10 页。</li>
                <li><b><code>7</code></b> : 只提取第 7 页。</li>
                <li><b><code>12-</code></b> : 从第 12 页提取到文件末尾。</li>
                <li><b><code>-5</code></b> : 从第 1 页提取到第 5 页。</li>
            </ul>
            <h3 style='color: #E6A23C;'>输出模式:</h3>
            <ul>
                <li><b>自动命名(默认):</b> 在源文件同目录下，生成如“原文件名_pages_5-10.pdf”的文件。</li>
                <li><b>手动指定:</b> 取消勾选后，可自定义输出文件的位置和名称。</li>
            </ul>
        """)
        
        # --- 布局 ---
        main_layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        input_group = QHBoxLayout()
        input_group.addWidget(QLabel('输入PDF:')); input_group.addWidget(self.input_path_edit); input_group.addWidget(self.input_browse_btn)
        range_group = QHBoxLayout()
        range_group.addWidget(QLabel('页面范围:')); range_group.addWidget(self.page_range_edit)
        output_group = QHBoxLayout()
        output_group.addWidget(QLabel('输出文件:')); output_group.addWidget(self.output_path_edit); output_group.addWidget(self.output_browse_btn)
        left_layout.addLayout(input_group); left_layout.addLayout(range_group); left_layout.addLayout(output_group)
        left_layout.addWidget(self.auto_output_check)
        
        top_layout.addLayout(left_layout)
        top_layout.addWidget(self.split_btn)
        main_layout.addLayout(top_layout)
        
        separator = QFrame(); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)
        
        bottom_layout = QHBoxLayout()
        log_area_widget = QWidget(); log_layout = QVBoxLayout(log_area_widget); log_layout.setContentsMargins(0,0,0,0)
        log_layout.addWidget(QLabel('日志输出:')); log_layout.addWidget(self.log_console)
        info_area_widget = QWidget(); info_layout = QVBoxLayout(info_area_widget); info_layout.setContentsMargins(0,0,0,0)
        info_layout.addWidget(QLabel('使用说明:')); info_layout.addWidget(self.info_panel)
        bottom_layout.addWidget(log_area_widget, 3); bottom_layout.addWidget(info_area_widget, 2)
        main_layout.addLayout(bottom_layout)

        # --- 连接信号 ---
        self.input_browse_btn.clicked.connect(self.select_input_file)
        self.output_browse_btn.clicked.connect(self.select_output_file)
        self.auto_output_check.toggled.connect(self.toggle_output_mode)
        self.split_btn.clicked.connect(self.start_split_process)

    def toggle_output_mode(self, checked):
        self.output_path_edit.setReadOnly(checked)
        self.output_browse_btn.setEnabled(not checked)
        if checked: self.output_path_edit.setText("将自动生成...")
        else: self.output_path_edit.clear()

    def select_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择PDF文件", "", "PDF Files (*.pdf)")
        if path: self.input_path_edit.setText(path)
            
    def select_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存拆分后的PDF", "", "PDF Files (*.pdf)")
        if path: self.output_path_edit.setText(path)

    def start_split_process(self):
        input_path = self.input_path_edit.text().strip()
        page_range = self.page_range_edit.text().strip()
        if not input_path or not os.path.isfile(input_path):
            QMessageBox.warning(self, "路径错误", "输入文件不存在！"); return
        if not page_range:
            QMessageBox.warning(self, "输入错误", "请输入页面范围！"); return
        
        output_path = None
        if not self.auto_output_check.isChecked():
            output_path = self.output_path_edit.text().strip()
            if not output_path:
                QMessageBox.warning(self, "路径错误", "请指定输出文件路径！"); return

        self.log_console.clear()
        self.set_controls_enabled(False)
        self.thread = QThread()
        self.worker = self.worker_class(input_path=input_path, page_range_str=page_range, output_path=output_path)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.on_split_error)
        self.thread.finished.connect(self.on_split_finished)
        self.thread.start()

    def set_controls_enabled(self, enabled):
        for w in [self.input_path_edit, self.input_browse_btn, self.page_range_edit,
                  self.output_path_edit, self.output_browse_btn, self.auto_output_check,
                  self.split_btn]:
            w.setEnabled(enabled)
        # 确保手动输出模式的控件状态正确
        if enabled: self.toggle_output_mode(self.auto_output_check.isChecked())
        self.split_btn.setText("开始拆分" if enabled else "正在拆分...")

    def on_split_finished(self):
        print("\nGUI: 任务已完成。")
        self.set_controls_enabled(True)
        QMessageBox.information(self, "完成", "PDF文件拆分已成功完成！")

    def on_split_error(self, error_message):
        print(f"\nGUI: 任务发生错误。")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "错误", error_message)
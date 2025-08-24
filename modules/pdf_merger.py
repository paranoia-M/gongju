# 文件: modules/pdf_merger.py

import os
import re
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QCheckBox, QTextEdit, QMessageBox
)
from PyQt5.QtCore import QThread

# 从项目根目录的utils.py导入工具类
from utils import Worker

# ==============================================================================
# ==                       后端核心逻辑 (这部分完全不变)                        ==
# ==============================================================================
SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff']
A4_PAPER_SIZE = fitz.paper_size("a4")

# ... (此处省略了你的4个后端函数: natural_sort_key, create_resized_image_pdf, 
#      process_directory_recursively, merge_files。请将你原来的这4个函数
#      完整地复制粘贴到这里。)
def natural_sort_key(s):
    """提供自然排序的键，用于像文件管理器一样排序"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def create_resized_image_pdf(image_path):
    """【可靠的图片处理函数】创建一个包含单张、居中、A4尺寸图片的内存PDF文档。"""
    doc = fitz.open()
    page = doc.new_page(width=A4_PAPER_SIZE[0], height=A4_PAPER_SIZE[1])
    try:
        with fitz.open(image_path) as img:
            img_rect = img[0].rect
            margin = 36
            drawable_area = page.rect + (margin, margin, -margin, -margin)
            target_rect = img_rect.fit(drawable_area)
            page.insert_image(target_rect, filename=image_path)
    except Exception as e:
        print(f"    - 警告: 无法处理图片 '{os.path.basename(image_path)}' : {e}")
        doc.close()
        return None
    return doc

def process_directory_recursively(current_dir, final_doc, toc, level, config):
    """
    【核心递归函数 - 已修正】采用“先添加，后验证移除”策略。
    """
    try:
        items = os.listdir(current_dir)
        items.sort(key=natural_sort_key)
    except OSError as e:
        print(f"  - 警告: 无法读取目录 '{current_dir}': {e}")
        return

    for item_name in items:
        full_path = os.path.join(current_dir, item_name)

        if os.path.abspath(full_path) == os.path.abspath(config['output_filepath']):
            continue

        if os.path.isdir(full_path):
            pages_before_entering = len(final_doc)
            print(f"\n进入子文件夹: {os.path.relpath(full_path, config['root_folder'])}")
            bookmark_to_add = [level, item_name, pages_before_entering + 1]
            toc.append(bookmark_to_add)
            process_directory_recursively(full_path, final_doc, toc, level + 1, config)
            if len(final_doc) == pages_before_entering:
                print(f"  - (空文件夹 '{item_name}'，已移除书签)")
                toc.pop()
        else:
            ext = os.path.splitext(item_name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                print(f"  - 处理中: {item_name}")
                source_doc = None
                try:
                    start_page_count = len(final_doc)
                    if config['resize_images'] and ext != '.pdf':
                        source_doc = create_resized_image_pdf(full_path)
                    else:
                        source_doc = fitz.open(full_path)
                    if source_doc:
                        final_doc.insert_pdf(source_doc)
                        print(f"    - 已合并 ({len(source_doc)} 页)")
                        file_bookmark_title = os.path.splitext(item_name)[0]
                        toc.append([level, file_bookmark_title, start_page_count + 1])
                except Exception as e:
                    print(f"    - 严重错误: 处理 '{item_name}' 失败: {e}")
                finally:
                    if source_doc:
                        source_doc.close()


def merge_files(root_folder, output_filepath, resize_images=False):
    """主函数，负责初始化和调用递归处理"""
    if not os.path.isdir(root_folder):
        print(f"[错误] 输入路径 '{root_folder}' 不是一个有效的文件夹。")
        return

    output_dir = os.path.dirname(output_filepath)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    final_doc = fitz.open()
    toc = []

    print(f"开始处理文件夹: {os.path.abspath(root_folder)}")
    if resize_images:
        print("模式: 图片将统一为A4页面尺寸。")
    print("-" * 40)

    config = {
        'root_folder': root_folder,
        'output_filepath': output_filepath,
        'resize_images': resize_images
    }

    try:
        process_directory_recursively(root_folder, final_doc, toc, 1, config)

        if len(final_doc) == 0:
            print("\n[错误] 未能合并任何文件。")
            return

        print("\n正在生成最终PDF...")
        if toc:
            final_doc.set_toc(toc)

        final_doc.save(output_filepath, garbage=4, deflate=True, clean=True)

        print("\n" + "=" * 40)
        print("[成功] 所有文件已合并完成！")
        print(f"文件已保存至: {os.path.abspath(output_filepath)}")
        print(f"总页数: {len(final_doc)}")
        print("=" * 40)

    finally:
        if final_doc:
            final_doc.close()

# ==============================================================================
# ==                  PDF合并功能的UI面板 (QWidget)                           ==
# ==============================================================================

class PdfMergerWidget(QWidget):
    """PDF合并功能的独立UI面板"""
    def __init__(self):
        super().__init__()
        # 为这个特定的模块定义一个Worker，它知道要调用哪个后端函数
        class MergerWorker(Worker):
            def __init__(self, **kwargs):
                super().__init__(task_function=merge_files, **kwargs)
        self.worker_class = MergerWorker
        self.initUI()

    def on_update_text(self, text):
        """接收日志信号并更新文本框"""
        self.log_console.moveCursor(self.log_console.textCursor().End)
        self.log_console.insertPlainText(text)

    def initUI(self):
        # 创建所有UI控件
        self.input_label = QLabel('输入文件夹:')
        self.input_path_edit = QLineEdit()
        self.input_browse_btn = QPushButton('浏览...')
        self.output_label = QLabel('输出文件:')
        self.output_path_edit = QLineEdit()
        self.output_browse_btn = QPushButton('另存为...')
        self.resize_checkbox = QCheckBox('将所有图片统一调整为A4页面尺寸')
        self.merge_btn = QPushButton('开始合并')
        self.merge_btn.setObjectName("MergeButton")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)

        # 设置布局
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_btn)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(input_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(self.resize_checkbox)
        main_layout.addWidget(self.merge_btn)
        main_layout.addWidget(QLabel('日志输出:'))
        main_layout.addWidget(self.log_console)

        # 连接信号与槽
        self.input_browse_btn.clicked.connect(self.select_input_folder)
        self.output_browse_btn.clicked.connect(self.select_output_file)
        self.merge_btn.clicked.connect(self.start_merge_process)

    def start_merge_process(self):
        input_folder = self.input_path_edit.text().strip()
        output_file = self.output_path_edit.text().strip()

        if not input_folder or not output_file:
            QMessageBox.warning(self, "输入错误", "请输入有效的输入文件夹和输出文件路径。")
            return
        if not os.path.isdir(input_folder):
            QMessageBox.warning(self, "路径错误", f"输入文件夹不存在:\n{input_folder}")
            return

        self.log_console.clear()
        self.set_controls_enabled(False)

        self.thread = QThread()
        self.worker = self.worker_class(
            root_folder=input_folder,
            output_filepath=output_file,
            resize_images=self.resize_checkbox.isChecked()
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.on_merge_error)
        self.thread.finished.connect(self.on_merge_finished)
        self.thread.start()

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含PDF和图片的文件夹")
        if folder:
            self.input_path_edit.setText(folder)
            folder_name = os.path.basename(folder)
            suggested_output = os.path.join(folder, f"{folder_name}_merged.pdf")
            self.output_path_edit.setText(suggested_output)

    def select_output_file(self):
        default_path = self.output_path_edit.text() or os.path.expanduser("~")
        file_path, _ = QFileDialog.getSaveFileName(self, "保存合并后的PDF", default_path, "PDF Files (*.pdf)")
        if file_path:
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            self.output_path_edit.setText(file_path)

    def set_controls_enabled(self, enabled):
        self.input_path_edit.setEnabled(enabled)
        self.output_path_edit.setEnabled(enabled)
        self.input_browse_btn.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.resize_checkbox.setEnabled(enabled)
        self.merge_btn.setEnabled(enabled)
        self.merge_btn.setText("开始合并" if enabled else "正在合并...")

    def on_merge_finished(self):
        print("\nGUI: 任务已完成。")
        self.set_controls_enabled(True)
        QMessageBox.information(self, "完成", "PDF合并已成功完成！")

    def on_merge_error(self, error_message):
        print(f"\nGUI: 任务发生错误。")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "错误", error_message)
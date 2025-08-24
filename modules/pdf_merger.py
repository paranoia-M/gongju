# 文件: modules/pdf_merger.py (最终整合版)

import os
import re
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QCheckBox, QTextEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import QThread

# 从项目根目录的utils.py导入工具类
from utils import Worker

# ==============================================================================
# ==                       后端核心逻辑 (已修正图片处理)                        ==
# ==============================================================================
SUPPORTED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.bmp', '.tiff']
A4_PAPER_SIZE = fitz.paper_size("a4")

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
    【核心递归函数 - 已修正V2】统一处理PDF和图片，确保都能合并。
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
                    
                    if ext == '.pdf':
                        # 如果是PDF，直接打开并插入
                        source_doc = fitz.open(full_path)
                        if source_doc and len(source_doc) > 0:
                            final_doc.insert_pdf(source_doc)
                            print(f"    - 已合并 ({len(source_doc)} 页PDF)")
                    # 如果是图片 (且不是PDF)
                    elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
                        if config['resize_images']:
                            # 使用我们现有的函数将图片转为带边距的单页PDF
                            source_doc = create_resized_image_pdf(full_path)
                            if source_doc:
                                final_doc.insert_pdf(source_doc)
                                print(f"    - 已合并 (1 页图片，已缩放至A4)")
                        else:
                            # 不缩放图片，将其尽可能大地插入新页面
                            page = final_doc.new_page()
                            with fitz.open(full_path) as img_doc:
                                img_rect = img_doc[0].rect
                                page.insert_image(page.rect, stream=img_doc[0].get_pixmap().tobytes())
                            print(f"    - 已合并 (1 页图片，原始比例)")
                    
                    # 如果有页面被成功添加，则创建书签
                    if len(final_doc) > start_page_count:
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
            final_doc.close()
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
# ==                  PDF合并功能的UI面板 (QWidget) - 布局已修改              ==
# ==============================================================================

class PdfMergerWidget(QWidget):
    """PDF合并功能的独立UI面板"""
    def __init__(self):
        super().__init__()
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
        # 1. --- 创建所有UI控件 ---
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

        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        self.info_panel.setHtml("""
            <h2 style='color: #88C0D0;'>功能说明</h2>
            <p>
                本功能可以递归遍历您选择的输入文件夹，将其中所有的PDF和图片文件
                （.jpg, .png等）按照文件名自然排序，合并成一个单一的PDF文件。
            </p>
            
            <h3 style='color: #EBCB8B;'>操作步骤：</h3>
            <ol>
                <li>点击“浏览...”选择一个包含源文件的文件夹。</li>
                <li>程序会自动生成一个输出文件名，您也可以点击“另存为...”自定义。</li>
                <li>如果文件夹中包含图片，建议勾选“将所有图片统一调整为A4页面尺寸”。</li>
                <li>点击“开始合并”，并在日志输出区查看处理过程。</li>
            </ol>
            
            <h3 style='color: #EBCB8B;'>注意事项：</h3>
            <ul>
                <li>文件的合并顺序遵循自然的数字和字母排序（例如："第1章", "第2章", "第10章"）。</li>
                <li>程序会自动创建层级书签，文件夹名为一级书签，文件名（不含后缀）为二级书签。</li>
                <li>空的子文件夹将被自动忽略。</li>
                <li>默认合并的顺序是文件存在的顺序，如果有特定要求可以给源文件使用数字排序，排序后即按照所需的顺序合并</li>
                <li>只能处理pdf和图片，如果遇到docx和xlsx需要提前手动转换，不然会忽略</li>
            </ul>
        """)

        # 2. --- 设置布局 ---
        main_layout = QVBoxLayout(self)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_btn)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)
        
        main_layout.addLayout(input_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(self.resize_checkbox)
        main_layout.addWidget(self.merge_btn)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #4C566A;")
        main_layout.addWidget(separator)

        bottom_area_layout = QHBoxLayout()

        log_area_widget = QWidget()
        log_area_layout = QVBoxLayout(log_area_widget)
        log_area_layout.setContentsMargins(0, 0, 0, 0)
        log_area_layout.addWidget(QLabel('日志输出:'))
        log_area_layout.addWidget(self.log_console)

        info_area_widget = QWidget()
        info_area_layout = QVBoxLayout(info_area_widget)
        info_area_layout.setContentsMargins(0, 0, 0, 0)
        info_area_layout.addWidget(QLabel('使用说明:'))
        info_area_layout.addWidget(self.info_panel)

        bottom_area_layout.addWidget(log_area_widget, 3)
        bottom_area_layout.addWidget(info_area_widget, 2)
        
        main_layout.addLayout(bottom_area_layout)

        # 3. --- 连接信号与槽 ---
        self.input_browse_btn.clicked.connect(self.select_input_folder)
        self.output_browse_btn.clicked.connect(self.select_output_file)
        self.merge_btn.clicked.connect(self.start_merge_process)

    # 4. --- 逻辑处理函数 ---
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
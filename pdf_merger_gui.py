# 文件名: pdf_merger_gui.py
# 版本: 11.0 (GUI集成版)
# 描述: 为V10.0的层级修正版PDF合并工具添加了PyQt5图形用户界面，
#       通过多线程处理避免UI卡顿，并实时显示处理日志。
# 作者: [Your Name]
# 日期: [Date]

import os
import re
import sys
import argparse
import fitz  # PyMuPDF
import traceback

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QCheckBox,
    QTextEdit, QMessageBox
)
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# ==============================================================================
# ==                                                                          ==
# ==                       后端核心逻辑 (来自 pdf_merger.py)                      ==
# ==                                                                          ==
# ==============================================================================

# --- 全局配置 ---
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
# ==                                                                          ==
# ==                            GUI 前端界面                                    ==
# ==                                                                          ==
# ==============================================================================

# 用于将 print 输出重定向到GUI的文本框
class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))

    def flush(self):
        pass  # 在这个场景下不需要做什么


# Worker 线程，用于在后台执行耗时的合并任务，防止UI冻结
class Worker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, input_folder, output_file, resize_images):
        super().__init__()
        self.input_folder = input_folder
        self.output_file = output_file
        self.resize_images = resize_images

    def run(self):
        try:
            merge_files(self.input_folder, self.output_file, self.resize_images)
        except Exception as e:
            # 捕获任何未预见的错误，并发送到主线程
            error_info = traceback.format_exc()
            self.error.emit(f"发生了一个意外错误:\n{error_info}")
        finally:
            self.finished.emit()


# 主窗口类
class PdfMergerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF Merger Pro v10.0 (GUI)')
        self.setGeometry(100, 100, 700, 500)
        self.initUI()

        # 将 print 输出重定向到日志窗口
        sys.stdout = Stream(newText=self.on_update_text)
        sys.stderr = Stream(newText=self.on_update_text)

    def on_update_text(self, text):
        """将文本追加到日志窗口，并滚动到底部"""
        self.log_console.moveCursor(self.log_console.textCursor().End)
        self.log_console.insertPlainText(text)

    def closeEvent(self, event):
        """关闭窗口时恢复标准输出"""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        super().closeEvent(event)

    def initUI(self):
        # --- 创建控件 ---
        # 输入文件夹
        self.input_label = QLabel('输入文件夹:')
        self.input_path_edit = QLineEdit()
        self.input_browse_btn = QPushButton('浏览...')

        # 输出文件
        self.output_label = QLabel('输出文件:')
        self.output_path_edit = QLineEdit()
        self.output_browse_btn = QPushButton('另存为...')

        # 选项
        self.resize_checkbox = QCheckBox('将所有图片统一调整为A4页面尺寸')

        # 操作按钮
        self.merge_btn = QPushButton('开始合并')

        # 日志控制台
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)

        # --- 布局 ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 输入布局
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_btn)

        # 输出布局
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.output_browse_btn)

        # 将所有控件添加到主布局
        main_layout.addLayout(input_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(self.resize_checkbox)
        main_layout.addWidget(self.merge_btn)
        main_layout.addWidget(QLabel('日志输出:'))
        main_layout.addWidget(self.log_console)

        # --- 连接信号和槽 ---
        self.input_browse_btn.clicked.connect(self.select_input_folder)
        self.output_browse_btn.clicked.connect(self.select_output_file)
        self.merge_btn.clicked.connect(self.start_merge_process)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择包含PDF和图片的文件夹")
        if folder:
            self.input_path_edit.setText(folder)
            # 自动建议一个输出文件名
            folder_name = os.path.basename(folder)
            suggested_output = os.path.join(folder, f"{folder_name}_merged.pdf")
            self.output_path_edit.setText(suggested_output)

    def select_output_file(self):
        # 默认路径可以从输入框获取
        default_path = self.output_path_edit.text() or os.path.expanduser("~")
        file_path, _ = QFileDialog.getSaveFileName(self, "保存合并后的PDF", default_path, "PDF Files (*.pdf)")
        if file_path:
            # 确保文件名以.pdf结尾
            if not file_path.lower().endswith('.pdf'):
                file_path += '.pdf'
            self.output_path_edit.setText(file_path)

    def start_merge_process(self):
        input_folder = self.input_path_edit.text().strip()
        output_file = self.output_path_edit.text().strip()

        # --- 输入验证 ---
        if not input_folder or not output_file:
            QMessageBox.warning(self, "输入错误", "请输入有效的输入文件夹和输出文件路径。")
            return
        if not os.path.isdir(input_folder):
            QMessageBox.warning(self, "路径错误", f"输入文件夹不存在:\n{input_folder}")
            return

        self.log_console.clear()  # 清空上次的日志
        self.set_controls_enabled(False)

        # --- 使用QThread执行任务 ---
        self.thread = QThread()
        self.worker = Worker(
            input_folder=input_folder,
            output_file=output_file,
            resize_images=self.resize_checkbox.isChecked()
        )
        self.worker.moveToThread(self.thread)

        # 连接信号
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.on_merge_error)
        self.thread.finished.connect(self.on_merge_finished)

        # 启动线程
        self.thread.start()

    def set_controls_enabled(self, enabled):
        """启用或禁用界面控件"""
        self.input_path_edit.setEnabled(enabled)
        self.output_path_edit.setEnabled(enabled)
        self.input_browse_btn.setEnabled(enabled)
        self.output_browse_btn.setEnabled(enabled)
        self.resize_checkbox.setEnabled(enabled)
        self.merge_btn.setEnabled(enabled)
        self.merge_btn.setText("开始合并" if enabled else "正在合并...")

    def on_merge_finished(self):
        """任务完成后的收尾工作"""
        print("\nGUI: 任务已完成。")
        self.set_controls_enabled(True)
        # 可以在这里弹出成功对话框
        QMessageBox.information(self, "完成", "PDF合并已成功完成！")

    def on_merge_error(self, error_message):
        """处理任务中的错误"""
        print(f"\nGUI: 任务发生错误。")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "错误", error_message)


# ==============================================================================
# ==                                                                          ==
# ==                            程序入口点                                      ==
# ==                                                                          ==
# ==============================================================================

def main_cli():
    """原始的命令行接口，保留作为备用"""
    parser = argparse.ArgumentParser(
        prog="pdf_merger.py",
        description="【层级修正终极版】100%遍历并保持正确排序，修复所有已知错误。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_folder", type=str, help="包含要合并的文件的根文件夹路径。")
    parser.add_argument("-o", "--output", type=str, default="merged_output.pdf", help="输出的合并后PDF文件名。")
    parser.add_argument("--resize-images", action="store_true", help="将所有图片统一调整为A4页面尺寸。")

    args = parser.parse_args()

    if not args.output.lower().endswith('.pdf'):
        args.output += '.pdf'

    merge_files(args.input_folder, args.output, args.resize_images)


if __name__ == "__main__":
    # 如果从命令行提供了参数，则使用命令行模式
    # 否则，启动GUI模式
    if len(sys.argv) > 1:
        main_cli()
    else:
        app = QApplication(sys.argv)
        main_window = PdfMergerApp()
        main_window.show()
        sys.exit(app.exec_())
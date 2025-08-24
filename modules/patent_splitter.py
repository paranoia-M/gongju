# 文件: modules/patent_splitter.py (最终整合版，包含说明面板)

import os
import re
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit, QMessageBox, QFrame
)
from PyQt5.QtCore import QThread

from utils import Worker

# ==============================================================================
# ==                       后端核心逻辑 (来自你的脚本)                        ==
# ==============================================================================

# 页面分类关键词
header_keywords = ["说明书摘要", "摘要附图", "权利要求书", "说明书附图", "说明书"]
merge_groups = {
    "说明书摘要": ["说明书摘要", "摘要附图"]
}

def extract_header_pages(pdf_path, header_y_threshold=100):
    """识别每页页眉文本，判断所属类型页面"""
    keyword_pages = {key: [] for key in header_keywords}
    claims_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            header_texts = [char["text"] for char in page.chars if char["top"] < header_y_threshold]
            header_str = ''.join(header_texts).replace(" ", "").replace("\n", "")
            if header_str.startswith("权利要求书"):
                claims_pages.append(i)
            else:
                matched = False
                for key in header_keywords:
                    if key == "权利要求书": continue
                    if header_str.startswith(key):
                        keyword_pages[key].append(i)
                        matched = True
                        break
                if not matched:
                    keyword_pages["说明书"].append(i)
    return keyword_pages, claims_pages

def extract_max_claim_number(pdf_path, claims_pages):
    """从权利要求书页中提取最大段落编号"""
    max_num = 0
    pattern = re.compile(r"\b(\d+)[.\uFF0E](?:[\s\u3000]?)")
    merged_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for p in claims_pages:
            page = pdf.pages[p]
            text = page.extract_text() or ""
            lines = text.splitlines()
            filtered_lines = [line.strip() for line in lines if not re.fullmatch(r"\d+", line.strip())]
            merged_text += ' '.join(filtered_lines) + " "
    nums = [int(n) for n in pattern.findall(merged_text)]
    if nums:
        max_num = max(nums)
        print(f"匹配到的所有段落序号: {nums}")
    else:
        print("⚠️ 未匹配到任何段落序号")
    return max_num

def merge_pages(pdf_path, keyword_pages_map, claims_pages, max_claim_num, output_dir):
    """根据页面映射关系，将页面写入不同的PDF文件"""
    reader = PdfReader(pdf_path)
    os.makedirs(output_dir, exist_ok=True)
    # 合并说明书摘要类
    for group_name, keys in merge_groups.items():
        pages_to_merge = sorted(set(p for key in keys for p in keyword_pages_map.get(key, [])))
        if pages_to_merge:
            writer = PdfWriter()
            for p in pages_to_merge: writer.add_page(reader.pages[p])
            out_path = os.path.join(output_dir, f"{group_name}.pdf")
            with open(out_path, "wb") as f: writer.write(f)
            print(f"✅ 已输出合并PDF: {out_path}（共 {len(pages_to_merge)} 页）")
    # 合并其余类型
    keys_in_groups = set(k for keys in merge_groups.values() for k in keys)
    for key, pages in keyword_pages_map.items():
        if key in keys_in_groups or key == "权利要求书" or not pages: continue
        writer = PdfWriter()
        for p in pages: writer.add_page(reader.pages[p])
        out_path = os.path.join(output_dir, f"{key}.pdf")
        with open(out_path, "wb") as f: writer.write(f)
        print(f"✅ 已输出合并PDF: {out_path}（共 {len(pages)} 页）")
    # 合并权利要求书
    if claims_pages:
        writer = PdfWriter()
        for p in sorted(claims_pages): writer.add_page(reader.pages[p])
        out_path = os.path.join(output_dir, f"权利要求书{max_claim_num}.pdf")
        with open(out_path, "wb") as f: writer.write(f)
        print(f"✅ 已输出权利要求书PDF: {out_path}（最大序号 {max_claim_num}）")

def split_patent_pdf(input_pdf_path, output_dir):
    """主调用函数，整合所有步骤"""
    print(f"\n🔍 正在处理: {os.path.basename(input_pdf_path)}")
    keyword_pages_map, claims_pages = extract_header_pages(input_pdf_path)
    max_claim_num = extract_max_claim_number(input_pdf_path, claims_pages)
    merge_pages(input_pdf_path, keyword_pages_map, claims_pages, max_claim_num, output_dir)
    print("\n🎉 PDF 分组完成！")


# ==============================================================================
# ==                  专利五书分割功能的UI面板 (QWidget)                      ==
# ==============================================================================

class PatentSplitterWidget(QWidget):
    def __init__(self):
        super().__init__()
        class SplitterWorker(Worker):
            def __init__(self, **kwargs):
                super().__init__(task_function=split_patent_pdf, **kwargs)
        self.worker_class = SplitterWorker
        self.initUI()

    def on_update_text(self, text):
        self.log_console.moveCursor(self.log_console.textCursor().End)
        self.log_console.insertPlainText(text)

    def initUI(self):
        # --- 1. 创建UI控件 ---
        self.input_label = QLabel('选择专利PDF文件:')
        self.input_path_edit = QLineEdit()
        self.input_browse_btn = QPushButton('浏览...')
        self.output_label = QLabel('输出文件夹:')
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        self.split_btn = QPushButton('开始分割')
        self.split_btn.setObjectName("MergeButton")
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)

        self.info_panel = QTextEdit()
        self.info_panel.setReadOnly(True)
        self.info_panel.setHtml("""
            <h2 style='color: #409EFF;'>功能说明</h2>
            <p>
                本功能用于将单个包含完整专利信息的PDF文件，根据标准的页眉
                （如“权利要求书”、“说明书”等），自动分割成多个独立的PDF文件。
            </p>
            
            <h3 style='color: #E6A23C;'>操作步骤：</h3>
            <ol>
                <li>点击“浏览...”选择一个需要分割的专利PDF文件。</li>
                <li>程序会自动在源文件同目录下创建一个与源文件同名的文件夹作为输出位置。</li>
                <li>点击“开始分割”，处理结果将保存在上述输出文件夹中。</li>
            </ol>
            
            <h3 style='color: #E6A23C;'>注意事项：</h3>
            <ul>
                <li>本工具强依赖于对PDF页眉文本的识别，请确保PDF是文本可选的，而非扫描图片。</li>
                <li>非标准的页眉格式可能会导致分割失败或不准确。</li>
                <li>分割后的“权利要求书.pdf”会自动附上识别到的最大权利要求项编号。</li>
                <li>只能上传pdf文件，并且上传之前将附图的位置调整成在两页以内，因为超过2页在专利系统可能通过不了</li>
            </ul>
        """)

        # --- 2. 设置布局 ---
        main_layout = QVBoxLayout(self)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(self.input_browse_btn)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path_edit)
        
        main_layout.addLayout(input_layout)
        main_layout.addLayout(output_layout)
        main_layout.addWidget(self.split_btn)

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

        # --- 3. 连接信号 ---
        self.input_browse_btn.clicked.connect(self.select_input_file)
        self.split_btn.clicked.connect(self.start_split_process)

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择一个专利PDF文件", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_path_edit.setText(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.join(os.path.dirname(file_path), base_name)
            self.output_path_edit.setText(output_dir)

    def start_split_process(self):
        input_file = self.input_path_edit.text().strip()
        output_dir = self.output_path_edit.text().strip()
        if not input_file or not os.path.isfile(input_file):
            QMessageBox.warning(self, "路径错误", f"输入文件不存在:\n{input_file}")
            return
        
        self.log_console.clear()
        self.set_controls_enabled(False)

        self.thread = QThread()
        self.worker = self.worker_class(input_pdf_path=input_file, output_dir=output_dir)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.on_split_error)
        self.thread.finished.connect(self.on_split_finished)
        self.thread.start()

    def set_controls_enabled(self, enabled):
        self.input_path_edit.setEnabled(enabled)
        self.input_browse_btn.setEnabled(enabled)
        self.split_btn.setEnabled(enabled)
        self.split_btn.setText("开始分割" if enabled else "正在分割...")

    def on_split_finished(self):
        print("\nGUI: 任务已完成。")
        self.set_controls_enabled(True)
        QMessageBox.information(self, "完成", "专利PDF分割已成功完成！")

    def on_split_error(self, error_message):
        print(f"\nGUI: 任务发生错误。")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "错误", error_message)
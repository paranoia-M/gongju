# 文件: modules/pdf_compressor.py (最终整合版 - 已优化输出逻辑)

import os
import fitz  # PyMuPDF
from PIL import Image
import io
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QFileDialog, QTextEdit, QMessageBox, QFrame, QSpinBox, QComboBox, QCheckBox,
    QGridLayout
)
from PyQt5.QtCore import QThread

from utils import Worker

# ==============================================================================
# ==                       后端核心逻辑 (来自你的脚本)                        ==
# ==============================================================================

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']

def get_output_path(input_path, source_base, output_base, new_ext=None):
    """计算输出文件的完整路径，并确保目录存在。"""
    relative_path = os.path.relpath(input_path, start=source_base)
    output_path = os.path.join(output_base, relative_path)
    if new_ext:
        base, _ = os.path.splitext(output_path)
        output_path = base + new_ext
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return output_path

def get_file_size(filepath, unit='mb'):
    """获取文件大小"""
    try:
        size_bytes = os.path.getsize(filepath)
        if unit.lower() == 'mb': return size_bytes / (1024 * 1024)
        return size_bytes
    except FileNotFoundError: return 0

def compress_pdf_by_rendering(filepath, output_path, dpi, quality, to_grayscale):
    """通过将PDF每一页渲染成图片，然后重新组合的方式进行极限压缩。"""
    try:
        original_size_mb = get_file_size(filepath, 'mb')
        print(f"-> 开始极限压缩PDF: {os.path.basename(filepath)} | 原始大小: {original_size_mb:.2f} MB")
        print(f"   (模式: 渲染-重组, DPI: {dpi}, 质量: {quality})")
        output_doc, input_doc = fitz.open(), fitz.open(filepath)
        for i, page in enumerate(input_doc):
            print(f"\r   - 正在处理第 {i + 1}/{len(input_doc)} 页...", end="")
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if to_grayscale: img = img.convert("L")
            with io.BytesIO() as f:
                img.save(f, format="JPEG", quality=quality, optimize=True)
                img_bytes = f.getvalue()
            img_page_rect = fitz.Rect(0, 0, pix.width, pix.height)
            new_page = output_doc.new_page(width=pix.width, height=pix.height)
            new_page.insert_image(img_page_rect, stream=img_bytes)
        print("\n   - 所有页面处理完毕，正在保存最终文件...")
        output_doc.save(output_path)
        input_doc.close(); output_doc.close()
        compressed_size_mb = get_file_size(output_path, 'mb')
        reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100 if original_size_mb > 0 else 0
        print(f"   [成功] -> {os.path.basename(output_path)} | 压缩后大小: {compressed_size_mb:.2f} MB | 体积减小: {reduction:.2f}%")
        return True
    except Exception as e:
        print(f"\n   [错误] 处理PDF {os.path.basename(filepath)} 时发生严重错误: {e}")
        return False

def compress_image(filepath, output_path, quality, to_grayscale, max_size):
    """极限压缩单个图片文件，通过缩放尺寸和降低质量实现。"""
    try:
        original_size_mb = get_file_size(filepath, 'mb')
        print(f"-> 开始极限压缩图片: {os.path.basename(filepath)} | 原始大小: {original_size_mb:.2f} MB")
        print(f"   (模式: 图片重编码, 质量: {quality}, 最大尺寸: {max_size or '不限制'}px)")
        with Image.open(filepath) as img:
            original_dims = img.size
            if img.mode in ("RGBA", "P", "LA"): img = img.convert("RGB")
            if max_size and max_size > 0 and (img.width > max_size or img.height > max_size):
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                print(f"      - 已缩小尺寸: 从 {original_dims[0]}x{original_dims[1]} -> {img.width}x{img.height}")
            if to_grayscale: img = img.convert("L")
            img.save(output_path, "JPEG", quality=quality, optimize=True, progressive=True, subsampling="4:2:0")
        compressed_size_mb = get_file_size(output_path, 'mb')
        reduction = (original_size_mb - compressed_size_mb) / original_size_mb * 100 if original_size_mb > 0 else 0
        print(f"   [成功] -> {os.path.basename(output_path)} | 压缩后大小: {compressed_size_mb:.2f} MB | 体积减小: {reduction:.2f}%")
        return True
    except Exception as e:
        print(f"\n   [错误] 处理图片 {os.path.basename(filepath)} 时发生严重错误: {e}")
        return False

def compress_path(input_path, output_path, dpi, pdf_quality, img_quality, max_size, to_grayscale):
    """新的主调用函数，处理单个文件或整个文件夹"""
    if input_path == output_path:
        print("错误：输入路径和输出路径不能相同！")
        return
    if not os.path.exists(output_path): os.makedirs(output_path)

    files_to_process, source_base_dir = [], ""
    if os.path.isfile(input_path):
        files_to_process.append(input_path)
        source_base_dir = os.path.dirname(input_path)
    elif os.path.isdir(input_path):
        source_base_dir = input_path
        for dirpath, _, filenames in os.walk(input_path):
            for filename in filenames: files_to_process.append(os.path.join(dirpath, filename))
    
    pdf_count, image_count, success_count = 0, 0, 0
    for filepath in files_to_process:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.pdf':
            pdf_count += 1
            output_file = get_output_path(filepath, source_base_dir, output_path)
            if compress_pdf_by_rendering(filepath, output_file, dpi, pdf_quality, to_grayscale):
                success_count += 1
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            image_count += 1
            output_file = get_output_path(filepath, source_base_dir, output_path, new_ext=".jpg")
            if compress_image(filepath, output_file, img_quality, to_grayscale, max_size):
                success_count += 1
    
    print("\n" + "="*50)
    print("所有极限压缩任务已完成！")
    print(f"总计发现 {pdf_count} 个PDF文件，{image_count} 个图片文件。")
    print(f"成功处理 {success_count} 个文件。")
    print(f"结果已保存到: {output_path}")
    print("="*50)

# ==============================================================================
# ==                      PDF压缩功能的UI面板 (QWidget)                       ==
# ==============================================================================
class PdfCompressorWidget(QWidget):
    def __init__(self):
        super().__init__()
        class CompressorWorker(Worker):
            def __init__(self, **kwargs): super().__init__(task_function=compress_path, **kwargs)
        self.worker_class = CompressorWorker
        self.initUI()
        # 初始化UI状态
        self.toggle_output_mode(self.auto_output_check.isChecked())

    def on_update_text(self, text):
        self.log_console.moveCursor(self.log_console.textCursor().End)
        self.log_console.insertPlainText(text)

    def initUI(self):
        # --- UI控件 ---
        self.input_path_edit = QLineEdit()
        self.input_file_btn = QPushButton('选择文件...')
        self.input_folder_btn = QPushButton('选择文件夹...')
        self.output_path_edit = QLineEdit()
        self.output_folder_btn = QPushButton('选择输出文件夹...')
        self.auto_output_check = QCheckBox('在源目录旁创建“压缩结果”文件夹')
        self.auto_output_check.setChecked(True)

        self.dpi_combo = QComboBox(); self.dpi_combo.addItems(['72 (极限)', '96 (推荐)', '120', '150'])
        self.dpi_combo.setCurrentIndex(1)
        self.pdf_quality_spin = QSpinBox(); self.pdf_quality_spin.setRange(10, 100); self.pdf_quality_spin.setValue(65)
        self.max_size_spin = QSpinBox(); self.max_size_spin.setRange(0, 8000); self.max_size_spin.setValue(1920); self.max_size_spin.setSuffix(" px")
        self.img_quality_spin = QSpinBox(); self.img_quality_spin.setRange(10, 100); self.img_quality_spin.setValue(65)
        self.grayscale_check = QCheckBox('强制转为灰度 (终极压缩)')
        self.compress_btn = QPushButton('开始压缩'); self.compress_btn.setObjectName("MergeButton")
        self.log_console = QTextEdit(); self.log_console.setReadOnly(True)
        self.info_panel = QTextEdit(); self.info_panel.setReadOnly(True)
        self.info_panel.setHtml("""
            <h2 style='color: #409EFF;'>功能说明</h2>
            <p>
                本功能通过<b>“渲染重组”</b>和<b>“图片重编码”</b>技术，对PDF和图片进行极限压缩，
                大幅减小文件体积，特别适合扫描件和包含大量图片的文档。
            </p>
            <h3 style='color: #E6A23C;'>压缩设置详解：</h3>
            <ul>
                <li><b>PDF渲染DPI：</b>将PDF每一页转换为图片时的分辨率(每英寸点数)。
                值越低，文件越小，但文字可能越模糊。<b>96 DPI</b> 是屏幕阅读的推荐平衡点。</li>
                
                <li><b>PDF图片质量：</b>重组PDF时，内部图片的JPEG压缩质量 (10-100)。
                <b>65</b> 是一个比较激进的压缩值，效果显著。</li>
                
                <li><b>图片最长边像素：</b>压缩独立的图片文件时，将其最长边缩放到此像素值。
                <b>0</b> 表示不缩放尺寸。<b>1920px (全高清)</b> 适合绝大多数屏幕查看场景。</li>
                
                <li><b>图片质量：</b>压缩独立图片时的JPEG质量。</li>
                
                <li><b>强制灰度：</b>将所有PDF页面和图片都转换为黑白灰度图。
                这是终极压缩手段，可获得最大压缩率，但会丢失所有色彩信息。</li>
            </ul>
            <h3 style='color: #E6A23C;'>注意事项：</h3>
            <p>
                此方法为<b>有损压缩</b>，会降低文档和图片的视觉质量。它不适合需要保留矢量特性
                （无限放大不模糊）或需要高保真色彩的场景。
            </p>
            <p>可以将图片和pdf放在一个文件夹上传，这里可以一次性全部压缩</p>
        """)

        # --- 布局 ---
        main_layout = QVBoxLayout(self)
        io_layout = QGridLayout()
        io_layout.addWidget(QLabel('输入源:'), 0, 0); io_layout.addWidget(self.input_path_edit, 0, 1, 1, 3)
        io_layout.addWidget(self.input_file_btn, 0, 4); io_layout.addWidget(self.input_folder_btn, 0, 5)
        io_layout.addWidget(QLabel('输出到:'), 1, 0); io_layout.addWidget(self.output_path_edit, 1, 1, 1, 3)
        io_layout.addWidget(self.output_folder_btn, 1, 4, 1, 2)
        io_layout.addWidget(self.auto_output_check, 2, 1, 1, 3)
        main_layout.addLayout(io_layout)

        settings_layout = QGridLayout()
        settings_layout.addWidget(QLabel('PDF渲染DPI:'), 0, 0); settings_layout.addWidget(self.dpi_combo, 0, 1)
        settings_layout.addWidget(QLabel('PDF图片质量:'), 0, 2); settings_layout.addWidget(self.pdf_quality_spin, 0, 3)
        settings_layout.addWidget(QLabel('图片最长边像素:'), 1, 0); settings_layout.addWidget(self.max_size_spin, 1, 1)
        settings_layout.addWidget(QLabel('图片质量:'), 1, 2); settings_layout.addWidget(self.img_quality_spin, 1, 3)
        main_layout.addLayout(settings_layout)
        main_layout.addWidget(self.grayscale_check)
        main_layout.addWidget(self.compress_btn)
        
        separator = QFrame(); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken); separator.setStyleSheet("background-color: #4C566A;")
        main_layout.addWidget(separator)
        
        bottom_layout = QHBoxLayout()
        log_area_widget = QWidget(); log_layout = QVBoxLayout(log_area_widget); log_layout.setContentsMargins(0,0,0,0)
        log_layout.addWidget(QLabel('日志输出:')); log_layout.addWidget(self.log_console)
        info_area_widget = QWidget(); info_layout = QVBoxLayout(info_area_widget); info_layout.setContentsMargins(0,0,0,0)
        info_layout.addWidget(QLabel('使用说明:')); info_layout.addWidget(self.info_panel)
        bottom_layout.addWidget(log_area_widget, 3); bottom_layout.addWidget(info_area_widget, 2)
        main_layout.addLayout(bottom_layout)

        # --- 连接信号 ---
        self.input_file_btn.clicked.connect(self.select_input_file)
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        self.compress_btn.clicked.connect(self.start_compress_process)
        self.auto_output_check.toggled.connect(self.toggle_output_mode)

    def toggle_output_mode(self, checked):
        if checked:
            self.output_path_edit.setReadOnly(True)
            self.output_folder_btn.setEnabled(False)
            self.update_auto_output_path()
        else:
            self.output_path_edit.setReadOnly(False)
            self.output_folder_btn.setEnabled(True)
            self.output_path_edit.clear()

    def update_auto_output_path(self):
        input_path = self.input_path_edit.text()
        if input_path and os.path.exists(input_path):
            if os.path.isfile(input_path):
                base_dir = os.path.dirname(input_path)
            else: # isdir
                base_dir = input_path
            output_dir = os.path.join(base_dir, "压缩结果")
            self.output_path_edit.setText(output_dir)
        else:
            self.output_path_edit.clear()

    def select_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "All Files (*.pdf *.jpg *.jpeg *.png *.bmp *.tiff)")
        if path: 
            self.input_path_edit.setText(path)
            if self.auto_output_check.isChecked():
                self.update_auto_output_path()

    def select_input_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path: 
            self.input_path_edit.setText(path)
            if self.auto_output_check.isChecked():
                self.update_auto_output_path()
            
    def select_output_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出文件夹")
        if path: self.output_path_edit.setText(path)

    def start_compress_process(self):
        input_path = self.input_path_edit.text().strip()
        output_path = self.output_path_edit.text().strip()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "路径错误", "输入源不存在！"); return
        if not output_path:
            QMessageBox.warning(self, "路径错误", "请选择输出文件夹！"); return

        self.log_console.clear()
        self.set_controls_enabled(False)
        self.thread = QThread()
        self.worker = self.worker_class(
            input_path=input_path, output_path=output_path,
            dpi=int(self.dpi_combo.currentText().split(' ')[0]),
            pdf_quality=self.pdf_quality_spin.value(),
            img_quality=self.img_quality_spin.value(),
            max_size=self.max_size_spin.value(),
            to_grayscale=self.grayscale_check.isChecked()
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.error.connect(self.on_compress_error)
        self.thread.finished.connect(self.on_compress_finished)
        self.thread.start()

    def set_controls_enabled(self, enabled):
        for w in [self.input_path_edit, self.input_file_btn, self.input_folder_btn,
                  self.output_path_edit, self.output_folder_btn, self.dpi_combo,
                  self.pdf_quality_spin, self.max_size_spin, self.img_quality_spin,
                  self.grayscale_check, self.compress_btn]:
            w.setEnabled(enabled)
        self.compress_btn.setText("开始压缩" if enabled else "正在压缩...")

    def on_compress_finished(self):
        print("\nGUI: 任务已完成。")
        self.set_controls_enabled(True)
        QMessageBox.information(self, "完成", "所有文件压缩已成功完成！")

    def on_compress_error(self, error_message):
        print(f"\nGUI: 任务发生错误。")
        self.set_controls_enabled(True)
        QMessageBox.critical(self, "错误", error_message)
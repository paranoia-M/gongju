# 文件: ui_styles.py

MODERN_STYLE = """
/* 主窗口和基础控件样式 */
QMainWindow, QWidget {
    background-color: #2E3440; /* Nord 暗色背景 */
    color: #ECEFF4; /* 亮色文字 */
   font-family: "Arial", "Helvetica", sans-serif; 
    font-size: 10pt;
}
/* 标签样式 */
QLabel {
    color: #D8DEE9;
}
/* 文本输入框和文本域样式 */
QLineEdit, QTextEdit {
    background-color: #3B4252;
    border: 1px solid #4C566A;
    border-radius: 4px;
    padding: 5px;
    color: #ECEFF4;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #88C0D0; /* 焦点状态下的边框颜色 */
}
/* 按钮通用样式 */
QPushButton {
    background-color: #5E81AC; /* Nord 蓝色 */
    color: #ECEFF4;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #81A1C1; /* 悬停时变亮 */
}
QPushButton:pressed {
    background-color: #4C566A; /* 按下时变暗 */
}
QPushButton:disabled {
    background-color: #4C566A;
    color: #6a7388;
}
/* 特殊按钮样式（例如 "开始合并"） */
#MergeButton {
    background-color: #A3BE8C; /* Nord 绿色，表示积极操作 */
    font-weight: bold;
}
#MergeButton:hover {
    background-color: #b4d1a0;
}
/* 复选框样式 */
QCheckBox {
    spacing: 5px;
}
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border-radius: 3px;
    border: 1px solid #4C566A;
}
QCheckBox::indicator:checked {
    background-color: #88C0D0; /* 选中时的颜色 */
}
/* 左侧菜单栏样式 */
QListWidget {
    background-color: #3B4252;
    border: none;
    outline: 0; /* 移除焦点时的虚线框 */
}
QListWidget::item {
    padding: 12px 15px;
    border-bottom: 1px solid #434C5E;
}
QListWidget::item:selected {
    background-color: #88C0D0; /* 选中项的背景色 */
    color: #2E3440; /* 选中项的文字颜色 */
    font-weight: bold;
}
QListWidget::item:hover {
    background-color: #4C566A;
}
/* 滚动条样式 */
QScrollBar:vertical {
    border: none;
    background: #2E3440;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #4C566A;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
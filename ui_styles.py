# 文件: ui_styles.py (全新青白色主题)

MODERN_STYLE = """
/* 
 * ==============================================================================
 * ==                           青白色 - 清爽主题样式表                          ==
 * ==============================================================================
 */

/* --- 主窗口和基础控件 --- */
QMainWindow, QWidget {
    background-color: #F5F7FA; /* 更柔和的淡灰色背景 */
    color: #303133; /* 主要文字颜色 (深灰色) */
    font-family: "Microsoft YaHei UI", "Segoe UI", "Arial", sans-serif;
    font-size: 14px; /* 提升基础字号，增强可读性 */
}

/* --- 标签 --- */
QLabel {
    color: #606266; /* 次要文字颜色 */
    padding: 2px;
}

/* --- 输入框、下拉框等 --- */
QLineEdit, QTextEdit, QSpinBox, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #DCDFE6;
    border-radius: 4px;
    padding: 8px; /* 增加内边距，使输入更舒适 */
    color: #303133;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #409EFF; /* 焦点状态下的主题色边框 */
}
QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QComboBox:disabled {
    background-color: #F5F7FA;
    color: #C0C4CC;
}

/* --- 按钮 --- */
QPushButton {
    background-color: #409EFF; /* 主题色 (青蓝色) */
    color: white;
    border: none;
    padding: 9px 20px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #66B1FF; /* 悬停时变亮 */
}
QPushButton:pressed {
    background-color: #3A8EE6; /* 按下时变暗 */
}
QPushButton:disabled {
    background-color: #A0CFFF;
    color: #FFFFFF;
}

/* --- 强调操作按钮 (例如 "开始XX") --- */
#MergeButton {
    background-color: #E6A23C; /* 绿色，表示成功/执行 */
}
#MergeButton:hover {
    background-color: #85CE61;
}
#MergeButton:pressed {
    background-color: #58A731;
}

/* --- 复选框 --- */
QCheckBox {
    spacing: 8px; /* 文字和框的间距 */
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 3px;
    border: 1px solid #DCDFE6;
    background-color: #FFFFFF;
}
QCheckBox::indicator:hover {
    border-color: #409EFF;
}
QCheckBox::indicator:checked {
    background-color: #409EFF;
    border-color: #409EFF;
}

/* --- 左侧菜单栏 --- */
QListWidget {
    background-color: #FFFFFF;
    border: none;
    outline: 0;
    border-right: 1px solid #E4E7ED; /* 右侧加一条细线分隔 */
}
QListWidget::item {
    padding: 15px 20px; /* 增加项目内边距 */
    border: none; /* 移除项目间的线 */
}
QListWidget::item:selected {
    background-color: #ECF5FF; /* 选中时淡蓝色背景 */
    color: #409EFF; /* 选中时主题色文字 */
    border-left: 3px solid #409EFF; /* 左侧加一个强调条 */
    padding-left: 17px;
}
QListWidget::item:hover:!selected {
    background-color: #F5F7FA;
}

/* --- 分隔线 --- */
QFrame[frameShape="4"] { /* QFrame.HLine */
    border: none;
    background-color: #E4E7ED;
    height: 1px;
}

/* --- 滚动条 --- */
QScrollBar:vertical {
    border: none;
    background: #F5F7FA;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #DCDFE6;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #C0C4CC;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
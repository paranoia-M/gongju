# 文件: utils.py

import traceback
from PyQt5.QtCore import QObject, pyqtSignal

class Stream(QObject):
    """用于将 print 输出重定向到GUI的文本框"""
    newText = pyqtSignal(str)
    def write(self, text): self.newText.emit(str(text))
    def flush(self): pass

class Worker(QObject):
    """
    通用的后台工作线程。
    接收一个任务函数和其关键字参数，在后台执行。
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, task_function, **kwargs):
        super().__init__()
        self.task_function = task_function
        self.kwargs = kwargs

    def run(self):
        """执行任务"""
        try:
            # 使用 **kwargs 解包关键字参数
            self.task_function(**self.kwargs)
        except Exception as e:
            error_info = traceback.format_exc()
            self.error.emit(f"发生了一个意外错误:\n{error_info}")
        finally:
            self.finished.emit()
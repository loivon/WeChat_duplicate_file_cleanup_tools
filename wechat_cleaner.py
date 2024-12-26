import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QFileDialog, QCheckBox, QLabel,
                             QProgressBar, QTextEdit, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from scanner import FileScanner
from db_manager import DatabaseManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.db_manager = DatabaseManager()
        
    def init_ui(self):
        self.setWindowTitle('微信文件清理工具')
        self.setGeometry(300, 300, 600, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 顶部文件选择区域
        top_layout = QHBoxLayout()
        self.path_label = QLabel('选择微信文件目录：')
        self.select_btn = QPushButton('选择目录')
        self.select_btn.clicked.connect(self.select_directory)
        top_layout.addWidget(self.path_label)
        top_layout.addWidget(self.select_btn)
        layout.addLayout(top_layout)
        
        # 文件类型选择区域
        self.file_types = {
            'Excel文件 (*.xlsx, *.xls)': ['.xlsx', '.xls'],
            'Word文件 (*.docx, *.doc)': ['.docx', '.doc'],
            'PPT文件 (*.pptx, *.ppt)': ['.pptx', '.ppt']
        }
        
        self.checkboxes = {}
        for file_type in self.file_types:
            cb = QCheckBox(file_type)
            cb.setChecked(True)
            self.checkboxes[file_type] = cb
            layout.addWidget(cb)
            
        # 分析按钮
        self.analyze_btn = QPushButton('开始分析')
        self.analyze_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # 结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)
        
        # 删除按钮
        self.delete_btn = QPushButton('删除重复文件')
        self.delete_btn.clicked.connect(self.delete_duplicates)
        self.delete_btn.setEnabled(False)
        layout.addWidget(self.delete_btn)
        
        self.selected_dir = None
        self.scanner = None
        
    def select_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择微信文件目录")
        if dir_path:
            self.selected_dir = dir_path
            self.path_label.setText(f'已选择目录：{dir_path}')
            
    def start_analysis(self):
        if not self.selected_dir:
            self.result_text.setText('请先选择微信文件目录！')
            return
            
        selected_extensions = []
        for file_type, cb in self.checkboxes.items():
            if cb.isChecked():
                selected_extensions.extend(self.file_types[file_type])
                
        self.scanner = FileScanner(self.selected_dir, selected_extensions, self.db_manager)
        self.scanner.progress_updated.connect(self.update_progress)
        self.scanner.scan_completed.connect(self.show_results)
        self.scanner.error_occurred.connect(self.show_error)
        self.scanner.start()
        
        self.analyze_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
    def show_results(self, stats):
        self.result_text.setText(stats)
        self.analyze_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)
        
    def delete_duplicates(self):
        reply = QMessageBox.question(self, '确认删除', 
                                   '确定要删除所有重复文件吗？此操作不可撤销！',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_duplicates()
            self.result_text.append('\n已删除所有重复文件！')
            self.delete_btn.setEnabled(False)
        
    def show_error(self, error_msg):
        self.result_text.setText(f"错误：\n{error_msg}")
        self.analyze_btn.setEnabled(True)
        self.select_btn.setEnabled(True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_()) 
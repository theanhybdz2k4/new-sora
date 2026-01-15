# -*- coding: utf-8 -*-
"""
Sora Automation Tool - GUI Application
"""

import sys
import os
import logging
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QFileDialog,
    QCheckBox, QComboBox, QSpinBox, QGroupBox, QProgressBar,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QFrame, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette

# Thêm đường dẫn root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser import BrowserCore
from core.excel_handler import ExcelHandler, TaskRow
from core.sora_automation import SoraAutomation
from core.thread_pool import ThreadPoolManager
from config.settings import (
    SORA_URL, DATA_DIR, OUTPUT_DIR,
    DEFAULT_TYPE, DEFAULT_ASPECT_RATIO, DEFAULT_DURATION,
    DEFAULT_RESOLUTION, DEFAULT_VARIATIONS
)

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(DATA_DIR, 'sora_tool.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Thread xử lý tasks"""
    
    progress = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str)
    task_completed = pyqtSignal(int, bool, str)  # row, success, message
    finished = pyqtSignal()
    login_required = pyqtSignal()
    
    def __init__(self, tasks: list, profile_name: str, headless: bool = False, image_folder: str = ""):
        super().__init__()
        self.tasks = tasks
        self.profile_name = profile_name
        self.headless = headless
        self.image_folder = image_folder
        self.is_running = True
        self.browser: Optional[BrowserCore] = None
        self.automation: Optional[SoraAutomation] = None
    
    def run(self):
        try:
            self.log_message.emit("Đang khởi tạo browser...")
            
            # Khởi tạo browser
            self.browser = BrowserCore(
                profile_name=self.profile_name,
                headless=self.headless
            )
            self.browser.init_browser()
            
            # Khởi tạo automation
            self.automation = SoraAutomation(self.browser)
            
            # Điều hướng đến Sora
            self.log_message.emit("Đang điều hướng đến Sora...")
            self.automation.navigate_to_sora()
            
            # Kiểm tra đăng nhập
            if not self.automation.is_logged_in():
                self.log_message.emit("Vui lòng đăng nhập vào Sora...")
                self.login_required.emit()
                
                if not self.automation.wait_for_login(timeout=300):
                    self.log_message.emit("Lỗi: Không thể đăng nhập!")
                    return
            
            self.log_message.emit("Đã đăng nhập thành công!")
            
            # Kiểm tra giao diện
            self.automation.check_and_switch_to_old_sora()
            
            # Xử lý từng task
            total = len(self.tasks)
            for idx, task in enumerate(self.tasks):
                if not self.is_running:
                    self.log_message.emit("Đã dừng xử lý!")
                    break
                
                self.progress.emit(idx + 1, total)
                self.log_message.emit(f"\n=== Xử lý task {idx + 1}/{total}: Dòng {task.row_number} ===")
                
                success, message = self.automation.process_task(task, self.image_folder)
                
                self.task_completed.emit(task.row_number, success, message)
                self.log_message.emit(f"Kết quả: {'✓ Thành công' if success else '✗ Thất bại'} - {message}")
                
                # Delay giữa các task
                if idx < total - 1 and self.is_running:
                    self.log_message.emit("Chờ 3 giây trước task tiếp theo...")
                    self.msleep(3000)
            
            self.log_message.emit("\n=== Hoàn thành tất cả tasks! ===")
            
        except Exception as e:
            self.log_message.emit(f"Lỗi: {str(e)}")
            logger.exception("Worker error")
        
        finally:
            if self.browser:
                self.browser.close()
            self.finished.emit()
    
    def stop(self):
        self.is_running = False


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng"""
    
    def __init__(self):
        super().__init__()
        
        self.excel_handler: Optional[ExcelHandler] = None
        self.worker: Optional[WorkerThread] = None
        self.pool_manager: Optional[ThreadPoolManager] = None
        self.pool_thread: Optional[QThread] = None
        self.tasks = []
        
        self.init_ui()
        self.apply_styles()
        self.load_settings()
    
    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Sora Automation Tool v1.57")
        self.setMinimumSize(1000, 700)
        
        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === Header ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("🎬 Sora Automation Tool")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        # === Splitter cho 2 panel ===
        splitter = QSplitter(Qt.Horizontal)
        
        # === Panel trái - Cài đặt ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # File Excel
        excel_group = QGroupBox("📁 File Excel")
        excel_layout = QHBoxLayout(excel_group)
        
        self.excel_path_edit = QLineEdit()
        self.excel_path_edit.setPlaceholderText("Chọn file Excel...")
        excel_layout.addWidget(self.excel_path_edit)
        
        browse_btn = QPushButton("Duyệt")
        browse_btn.clicked.connect(self.browse_excel)
        excel_layout.addWidget(browse_btn)
        
        create_template_btn = QPushButton("Tạo Template")
        create_template_btn.clicked.connect(self.create_template)
        excel_layout.addWidget(create_template_btn)
        
        left_layout.addWidget(excel_group)
        
        # Thư mục ảnh
        image_folder_group = QGroupBox("🖼️ Thư mục ảnh")
        image_folder_layout = QHBoxLayout(image_folder_group)
        
        self.image_folder_edit = QLineEdit()
        self.image_folder_edit.setPlaceholderText("Thư mục chứa ảnh...")
        image_folder_layout.addWidget(self.image_folder_edit)
        
        browse_image_btn = QPushButton("Duyệt")
        browse_image_btn.clicked.connect(self.browse_image_folder)
        image_folder_layout.addWidget(browse_image_btn)
        
        left_layout.addWidget(image_folder_group)
        
        # Profile
        profile_group = QGroupBox("👤 Profile")
        profile_layout = QHBoxLayout(profile_group)
        
        profile_layout.addWidget(QLabel("Tên Profile:"))
        self.profile_edit = QLineEdit("default")
        profile_layout.addWidget(self.profile_edit)
        
        left_layout.addWidget(profile_group)
        
        # Cài đặt mặc định
        settings_group = QGroupBox("⚙️ Cài đặt mặc định")
        settings_layout = QVBoxLayout(settings_group)
        
        # Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Loại:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["video", "image"])
        self.type_combo.setCurrentText(DEFAULT_TYPE)
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        settings_layout.addLayout(type_layout)
        
        # Aspect Ratio
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("Tỉ lệ:"))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["3:2", "1:1", "2:3", "16:9", "9:16", "4:3", "3:4"])
        self.ratio_combo.setCurrentText(DEFAULT_ASPECT_RATIO)
        ratio_layout.addWidget(self.ratio_combo)
        ratio_layout.addStretch()
        settings_layout.addLayout(ratio_layout)
        
        # Duration (chỉ cho video)
        self.duration_widget = QWidget()
        duration_layout = QHBoxLayout(self.duration_widget)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        self.duration_label = QLabel("Thời lượng:")
        duration_layout.addWidget(self.duration_label)
        self.duration_combo = QComboBox()
        self.duration_combo.addItems(["5s", "10s", "15s", "20s"])
        self.duration_combo.setCurrentText(DEFAULT_DURATION)
        duration_layout.addWidget(self.duration_combo)
        duration_layout.addStretch()
        settings_layout.addWidget(self.duration_widget)
        
        # Resolution (chỉ cho video)
        self.resolution_widget = QWidget()
        res_layout = QHBoxLayout(self.resolution_widget)
        res_layout.setContentsMargins(0, 0, 0, 0)
        self.resolution_label = QLabel("Độ phân giải:")
        res_layout.addWidget(self.resolution_label)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["480p", "720p", "1080p"])
        self.resolution_combo.setCurrentText(DEFAULT_RESOLUTION)
        res_layout.addWidget(self.resolution_combo)
        res_layout.addStretch()
        settings_layout.addWidget(self.resolution_widget)
        
        # Number of browsers
        browser_layout = QHBoxLayout()
        browser_layout.addWidget(QLabel("Số lượng Browser:"))
        self.num_browsers_spin = QSpinBox()
        self.num_browsers_spin.setMinimum(1)
        self.num_browsers_spin.setMaximum(10)
        self.num_browsers_spin.setValue(1)
        browser_layout.addWidget(self.num_browsers_spin)
        browser_layout.addStretch()
        settings_layout.addLayout(browser_layout)
        
        # Headless mode
        self.headless_check = QCheckBox("Chế độ Headless (chạy ẩn)")
        settings_layout.addWidget(self.headless_check)
        
        left_layout.addWidget(settings_group)
        
        # Nút điều khiển
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("📥 Load Tasks")
        self.load_btn.clicked.connect(self.load_tasks)
        control_layout.addWidget(self.load_btn)
        
        self.start_btn = QPushButton("▶️ Bắt đầu")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Dừng")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(control_layout)
        
        # Progress
        progress_layout = QVBoxLayout()
        self.progress_label = QLabel("Tiến độ: 0/0")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)
        
        left_layout.addLayout(progress_layout)
        
        left_layout.addStretch()
        
        splitter.addWidget(left_panel)
        
        # === Panel phải - Tasks & Log ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(10)
        
        # Bảng tasks
        tasks_group = QGroupBox("📋 Danh sách Tasks")
        tasks_layout = QVBoxLayout(tasks_group)
        
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(5)
        self.tasks_table.setHorizontalHeaderLabels(["Dòng", "Prompt", "Loại", "Trạng thái", "Kết quả"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tasks_table.setAlternatingRowColors(True)
        tasks_layout.addWidget(self.tasks_table)
        
        right_layout.addWidget(tasks_group, 1)
        
        # Log
        log_group = QGroupBox("📝 Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("Xóa Log")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_layout.addWidget(clear_log_btn)
        
        right_layout.addWidget(log_group, 1)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 650])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Sẵn sàng")
    
    def apply_styles(self):
        """Áp dụng styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            QWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #45475a;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                padding: 8px;
                color: #cdd6f4;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #89b4fa;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b4befe;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
            QTextEdit {
                background-color: #11111b;
                border: 1px solid #45475a;
                border-radius: 5px;
                color: #a6e3a1;
            }
            QTableWidget {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 5px;
                gridline-color: #45475a;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            QHeaderView::section {
                background-color: #45475a;
                color: #cdd6f4;
                padding: 8px;
                border: none;
            }
            QProgressBar {
                border: 1px solid #45475a;
                border-radius: 5px;
                text-align: center;
                background-color: #313244;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 4px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QStatusBar {
                background-color: #11111b;
                color: #6c7086;
            }
        """)
    
    def log(self, message: str):
        """Thêm message vào log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_type_changed(self, type_value: str):
        """Xử lý khi thay đổi loại (video/image)"""
        is_video = type_value == "video"
        
        # Hiện/ẩn Duration và Resolution
        self.duration_widget.setVisible(is_video)
        self.resolution_widget.setVisible(is_video)
    
    def browse_excel(self):
        """Chọn file Excel"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file Excel",
            DATA_DIR,
            "Excel Files (*.xlsx *.xls)"
        )
        
        if filepath:
            self.excel_path_edit.setText(filepath)
            self.load_tasks()
    
    def browse_image_folder(self):
        """Chọn thư mục chứa ảnh"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục ảnh",
            self.image_folder_edit.text() or DATA_DIR
        )
        
        if folder:
            self.image_folder_edit.setText(folder)
            self.log(f"Đã chọn thư mục ảnh: {folder}")
    
    def create_template(self):
        """Tạo file template"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu Template",
            os.path.join(DATA_DIR, "sora_template.xlsx"),
            "Excel Files (*.xlsx)"
        )
        
        if filepath:
            handler = ExcelHandler()
            handler.create_template(filepath)
            self.log(f"Đã tạo template: {filepath}")
            QMessageBox.information(self, "Thành công", f"Đã tạo template:\n{filepath}")
    
    def load_tasks(self):
        """Load tasks từ Excel"""
        filepath = self.excel_path_edit.text()
        
        if not filepath:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn file Excel!")
            return
        
        if not os.path.exists(filepath):
            QMessageBox.warning(self, "Lỗi", "File không tồn tại!")
            return
        
        self.excel_handler = ExcelHandler(filepath)
        if not self.excel_handler.load():
            QMessageBox.warning(self, "Lỗi", "Không thể đọc file Excel!")
            return
        
        self.tasks = self.excel_handler.get_tasks()
        
        # Hiển thị trong bảng
        self.tasks_table.setRowCount(len(self.tasks))
        
        for row, task in enumerate(self.tasks):
            self.tasks_table.setItem(row, 0, QTableWidgetItem(str(task.row_number)))
            
            prompt_item = QTableWidgetItem(task.prompt[:50] + "..." if len(task.prompt) > 50 else task.prompt)
            prompt_item.setToolTip(task.prompt)
            self.tasks_table.setItem(row, 1, prompt_item)
            
            self.tasks_table.setItem(row, 2, QTableWidgetItem(task.type))
            self.tasks_table.setItem(row, 3, QTableWidgetItem(task.status or "Pending"))
            self.tasks_table.setItem(row, 4, QTableWidgetItem(task.result))
        
        self.log(f"Đã load {len(self.tasks)} task(s) từ Excel")
        self.start_btn.setEnabled(len(self.tasks) > 0)
        self.status_bar.showMessage(f"Đã load {len(self.tasks)} task(s)")
    
    def start_processing(self):
        """Bắt đầu xử lý"""
        if not self.tasks:
            QMessageBox.warning(self, "Lỗi", "Không có task nào để xử lý!")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.load_btn.setEnabled(False)
        
        self.progress_bar.setValue(0)
        
        num_browsers = self.num_browsers_spin.value()
        
        if num_browsers == 1:
            # Chế độ single browser (như cũ)
            self.worker = WorkerThread(
                tasks=self.tasks,
                profile_name=self.profile_edit.text(),
                headless=self.headless_check.isChecked(),
                image_folder=self.image_folder_edit.text()
            )
            
            self.worker.progress.connect(self.on_progress)
            self.worker.log_message.connect(self.log)
            self.worker.task_completed.connect(self.on_task_completed)
            self.worker.finished.connect(self.on_finished)
            self.worker.login_required.connect(self.on_login_required)
            
            self.worker.start()
            self.log("Bắt đầu xử lý (1 browser)...")
        else:
            # Chế độ multi-browser
            self.pool_manager = ThreadPoolManager(
                max_workers=num_browsers,
                headless=self.headless_check.isChecked(),
                image_folder=self.image_folder_edit.text()
            )
            
            self.pool_manager.log_message.connect(self.log)
            self.pool_manager.task_completed.connect(self._on_pool_task_completed)
            self.pool_manager.all_completed.connect(self.on_finished)
            self.pool_manager.login_required.connect(self._on_pool_login_required)
            self.pool_manager.task_started.connect(self._on_task_started)
            
            # Chạy trong thread riêng
            self.pool_thread = QThread()
            self.pool_manager.moveToThread(self.pool_thread)
            self.pool_thread.started.connect(
                lambda: self.pool_manager.process_tasks(self.tasks)
            )
            self.pool_thread.start()
            
            self.log(f"Bắt đầu xử lý ({num_browsers} browsers)...")
    
    def stop_processing(self):
        """Dừng xử lý"""
        if self.worker:
            self.worker.stop()
        if self.pool_manager:
            self.pool_manager.stop()
        self.log("Đang dừng...")
    
    def on_progress(self, current: int, total: int):
        """Cập nhật tiến độ"""
        self.progress_label.setText(f"Tiến độ: {current}/{total}")
        self.progress_bar.setValue(int(current / total * 100))
        self.status_bar.showMessage(f"Đang xử lý: {current}/{total}")
    
    def on_task_completed(self, row: int, success: bool, message: str):
        """Cập nhật khi task hoàn thành"""
        # Cập nhật Excel
        if self.excel_handler:
            status = "Completed" if success else "Failed"
            self.excel_handler.update_status(row, status, message)
        
        # Cập nhật bảng
        for idx in range(self.tasks_table.rowCount()):
            if self.tasks_table.item(idx, 0).text() == str(row):
                status_item = QTableWidgetItem("✓ Hoàn thành" if success else "✗ Thất bại")
                status_item.setForeground(QColor("#a6e3a1" if success else "#f38ba8"))
                self.tasks_table.setItem(idx, 3, status_item)
                self.tasks_table.setItem(idx, 4, QTableWidgetItem(message))
                break
    
    def _on_pool_task_completed(self, row: int, success: bool, message: str, profile: str):
        """Xử lý khi task hoàn thành từ pool"""
        # Cập nhật tiến độ
        completed = sum(1 for i in range(self.tasks_table.rowCount()) 
                       if self.tasks_table.item(i, 3) and 
                       self.tasks_table.item(i, 3).text() in ["✓ Hoàn thành", "✗ Thất bại"])
        total = len(self.tasks)
        self.on_progress(completed + 1, total)
        
        # Cập nhật task
        self.on_task_completed(row, success, message)
    
    def _on_pool_login_required(self, profile: str):
        """Thông báo cần đăng nhập cho profile"""
        QMessageBox.information(
            self,
            "Đăng nhập",
            f"Vui lòng đăng nhập vào Sora trong cửa sổ browser ({profile}).\n"
            "Sau khi đăng nhập xong, tool sẽ tự động tiếp tục."
        )
    
    def _on_task_started(self, row: int, profile: str):
        """Xử lý khi task bắt đầu"""
        for idx in range(self.tasks_table.rowCount()):
            if self.tasks_table.item(idx, 0).text() == str(row):
                status_item = QTableWidgetItem(f"🔄 {profile}")
                status_item.setForeground(QColor("#89b4fa"))
                self.tasks_table.setItem(idx, 3, status_item)
                break
    
    def on_login_required(self):
        """Thông báo cần đăng nhập"""
        QMessageBox.information(
            self,
            "Đăng nhập",
            "Vui lòng đăng nhập vào Sora trong cửa sổ browser.\n"
            "Sau khi đăng nhập xong, tool sẽ tự động tiếp tục."
        )
    
    def on_finished(self):
        """Xử lý khi hoàn thành"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)
        self.status_bar.showMessage("Hoàn thành!")
        
        # Cleanup pool thread
        if self.pool_thread and self.pool_thread.isRunning():
            self.pool_thread.quit()
            self.pool_thread.wait()
        
        QMessageBox.information(self, "Hoàn thành", "Đã xử lý xong tất cả tasks!")
    
    def load_settings(self):
        """Load settings từ file"""
        settings = QSettings("SoraTool", "Sora157")
        
        # Load các giá trị đã lưu
        self.type_combo.setCurrentText(settings.value("type", DEFAULT_TYPE))
        self.ratio_combo.setCurrentText(settings.value("ratio", DEFAULT_ASPECT_RATIO))
        self.duration_combo.setCurrentText(settings.value("duration", DEFAULT_DURATION))
        self.resolution_combo.setCurrentText(settings.value("resolution", DEFAULT_RESOLUTION))
        self.num_browsers_spin.setValue(int(settings.value("num_browsers", 1)))
        self.headless_check.setChecked(settings.value("headless", False, type=bool))
        self.profile_edit.setText(settings.value("profile", "default"))
        
        # Load file Excel cuối cùng
        last_excel = settings.value("last_excel", "")
        if last_excel and os.path.exists(last_excel):
            self.excel_path_edit.setText(last_excel)
        
        # Load thư mục ảnh
        image_folder = settings.value("image_folder", "")
        if image_folder and os.path.exists(image_folder):
            self.image_folder_edit.setText(image_folder)
        
        # Trigger on_type_changed để cập nhật UI
        self.on_type_changed(self.type_combo.currentText())
        
        logger.info("Đã load settings")
    
    def save_settings(self):
        """Lưu settings vào file"""
        settings = QSettings("SoraTool", "Sora157")
        
        settings.setValue("type", self.type_combo.currentText())
        settings.setValue("ratio", self.ratio_combo.currentText())
        settings.setValue("duration", self.duration_combo.currentText())
        settings.setValue("resolution", self.resolution_combo.currentText())
        settings.setValue("num_browsers", self.num_browsers_spin.value())
        settings.setValue("headless", self.headless_check.isChecked())
        settings.setValue("profile", self.profile_edit.text())
        settings.setValue("last_excel", self.excel_path_edit.text())
        settings.setValue("image_folder", self.image_folder_edit.text())
        
        logger.info("Đã lưu settings")
    
    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        # Lưu settings trước khi thoát
        self.save_settings()
        
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Xác nhận",
                "Đang xử lý tasks. Bạn có chắc muốn thoát?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

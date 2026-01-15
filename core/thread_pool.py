# -*- coding: utf-8 -*-
"""
Thread Pool Manager - Quản lý nhiều browser chạy song song
"""

import logging
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from threading import Lock

from PyQt5.QtCore import QObject, pyqtSignal

from core.browser import BrowserCore
from core.sora_automation import SoraAutomation
from core.excel_handler import TaskRow

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """Kết quả từ một worker"""
    task: TaskRow
    success: bool
    message: str
    profile_name: str


class ThreadPoolManager(QObject):
    """Quản lý pool các browser workers"""
    
    # Signals
    task_started = pyqtSignal(int, str)  # row_number, profile
    task_completed = pyqtSignal(int, bool, str, str)  # row, success, message, profile
    log_message = pyqtSignal(str)
    all_completed = pyqtSignal()
    login_required = pyqtSignal(str)  # profile_name
    
    def __init__(self, max_workers: int = 3, headless: bool = False):
        super().__init__()
        self.max_workers = max_workers
        self.headless = headless
        self.executor: Optional[ThreadPoolExecutor] = None
        self.is_running = True
        self.active_browsers: Dict[str, BrowserCore] = {}
        self.lock = Lock()
        self._logged_in_profiles = set()
    
    def _get_profile_name(self, index: int) -> str:
        """Tạo tên profile theo index"""
        return f"profile_{index + 1}"
    
    def _ensure_logged_in(self, profile_name: str, browser: BrowserCore, automation: SoraAutomation) -> bool:
        """Đảm bảo profile đã đăng nhập"""
        # Điều hướng đến Sora
        if not automation.navigate_to_sora():
            return False
        
        # Kiểm tra đăng nhập
        if automation.is_logged_in():
            self._logged_in_profiles.add(profile_name)
            return True
        
        # Chưa đăng nhập - thông báo và chờ
        self.log_message.emit(f"[{profile_name}] Vui lòng đăng nhập...")
        self.login_required.emit(profile_name)
        
        if automation.wait_for_login(timeout=300):
            self._logged_in_profiles.add(profile_name)
            return True
        
        return False
    
    def _process_task(self, task: TaskRow, profile_index: int) -> WorkerResult:
        """Xử lý một task với browser riêng"""
        profile_name = self._get_profile_name(profile_index)
        
        try:
            self.log_message.emit(f"[{profile_name}] Đang xử lý dòng {task.row_number}...")
            self.task_started.emit(task.row_number, profile_name)
            
            # Tạo browser mới cho profile này
            browser = BrowserCore(profile_name=profile_name, headless=self.headless)
            browser.init_browser()
            
            with self.lock:
                self.active_browsers[profile_name] = browser
            
            automation = SoraAutomation(browser)
            
            # Đảm bảo đã đăng nhập
            if not self._ensure_logged_in(profile_name, browser, automation):
                return WorkerResult(task, False, "Không thể đăng nhập", profile_name)
            
            # Kiểm tra giao diện Sora
            automation.check_and_switch_to_old_sora()
            
            # Xử lý task
            success, message = automation.process_task(task)
            
            return WorkerResult(task, success, message, profile_name)
            
        except Exception as e:
            logger.exception(f"Error processing task {task.row_number}")
            return WorkerResult(task, False, str(e), profile_name)
        
        finally:
            # Đóng browser sau khi xử lý xong
            with self.lock:
                if profile_name in self.active_browsers:
                    try:
                        self.active_browsers[profile_name].close()
                    except:
                        pass
                    del self.active_browsers[profile_name]
    
    def process_tasks(self, tasks: List[TaskRow], keep_browsers_open: bool = False):
        """
        Xử lý danh sách tasks với nhiều browser
        
        Args:
            tasks: Danh sách tasks cần xử lý
            keep_browsers_open: Giữ browsers mở để reuse
        """
        self.is_running = True
        
        # Chia tasks cho các workers
        # Mỗi worker xử lý 1 task tại một thời điểm
        self.log_message.emit(f"Bắt đầu xử lý {len(tasks)} tasks với {self.max_workers} browsers...")
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                self.executor = executor
                
                # Submit tasks
                futures = {}
                for idx, task in enumerate(tasks):
                    if not self.is_running:
                        break
                    
                    profile_idx = idx % self.max_workers
                    future = executor.submit(self._process_task, task, profile_idx)
                    futures[future] = task
                
                # Thu thập kết quả
                for future in as_completed(futures):
                    if not self.is_running:
                        break
                    
                    result = future.result()
                    self.task_completed.emit(
                        result.task.row_number,
                        result.success,
                        result.message,
                        result.profile_name
                    )
                    
                    status = "✓" if result.success else "✗"
                    self.log_message.emit(
                        f"[{result.profile_name}] Dòng {result.task.row_number}: {status} {result.message}"
                    )
        
        except Exception as e:
            self.log_message.emit(f"Lỗi: {str(e)}")
            logger.exception("ThreadPool error")
        
        finally:
            self._cleanup()
            self.all_completed.emit()
    
    def _cleanup(self):
        """Dọn dẹp resources"""
        with self.lock:
            for profile, browser in list(self.active_browsers.items()):
                try:
                    browser.close()
                except:
                    pass
            self.active_browsers.clear()
    
    def stop(self):
        """Dừng tất cả workers"""
        self.is_running = False
        self.log_message.emit("Đang dừng tất cả browsers...")
        
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)
        
        self._cleanup()


class MultiBrowserWorkerThread(QObject):
    """Thread chạy ThreadPoolManager"""
    
    progress = pyqtSignal(int, int)  # current, total
    log_message = pyqtSignal(str)
    task_completed = pyqtSignal(int, bool, str)  # row, success, message
    finished = pyqtSignal()
    login_required = pyqtSignal(str)  # profile_name
    
    def __init__(self, tasks: List[TaskRow], num_browsers: int = 3, headless: bool = False):
        super().__init__()
        self.tasks = tasks
        self.num_browsers = num_browsers
        self.headless = headless
        self.pool_manager: Optional[ThreadPoolManager] = None
        self._completed_count = 0
        self._total_count = 0
    
    def run(self):
        """Chạy xử lý"""
        self._total_count = len(self.tasks)
        self._completed_count = 0
        
        self.pool_manager = ThreadPoolManager(
            max_workers=self.num_browsers,
            headless=self.headless
        )
        
        # Kết nối signals
        self.pool_manager.log_message.connect(self.log_message.emit)
        self.pool_manager.task_completed.connect(self._on_task_completed)
        self.pool_manager.all_completed.connect(self.finished.emit)
        self.pool_manager.login_required.connect(self.login_required.emit)
        
        # Chạy
        self.pool_manager.process_tasks(self.tasks)
    
    def _on_task_completed(self, row: int, success: bool, message: str, profile: str):
        """Xử lý khi task hoàn thành"""
        self._completed_count += 1
        self.progress.emit(self._completed_count, self._total_count)
        self.task_completed.emit(row, success, message)
    
    def stop(self):
        """Dừng xử lý"""
        if self.pool_manager:
            self.pool_manager.stop()

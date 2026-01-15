# -*- coding: utf-8 -*-
"""
Sora Automation Module - Tự động hóa tương tác với Sora
"""

import os
import time
import logging
import re
import requests
from typing import Optional, Tuple
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from core.browser import BrowserCore
from core.excel_handler import TaskRow
from config.settings import (
    SORA_URL, GENERATION_TIMEOUT, DOWNLOAD_TIMEOUT,
    OUTPUT_DIR, SELECTORS
)

logger = logging.getLogger(__name__)


class SoraAutomation:
    """Lớp tự động hóa tương tác với Sora"""
    
    def __init__(self, browser: BrowserCore):
        """
        Khởi tạo automation
        
        Args:
            browser: Instance của BrowserCore
        """
        self.browser = browser
        self.driver = browser.driver
    
    def navigate_to_sora(self) -> bool:
        """Điều hướng đến Sora"""
        return self.browser.navigate(SORA_URL)
    
    def is_logged_in(self) -> bool:
        """Kiểm tra đã đăng nhập chưa"""
        time.sleep(2)
        
        # Kiểm tra các dấu hiệu đã đăng nhập
        # Thường là có prompt input hoặc không có nút login
        try:
            current_url = self.browser.get_current_url()
            
            # Nếu đang ở trang login thì chưa đăng nhập
            if "login" in current_url.lower() or "auth" in current_url.lower():
                return False
            
            # Tìm prompt input
            prompt_input = self.browser.wait_for_element(
                SELECTORS["prompt_input"], 
                timeout=5
            )
            
            return prompt_input is not None
            
        except Exception as e:
            logger.error(f"Lỗi kiểm tra đăng nhập: {e}")
            return False
    
    def wait_for_login(self, timeout: int = 300) -> bool:
        """
        Chờ người dùng đăng nhập thủ công
        
        Args:
            timeout: Thời gian chờ tối đa (giây)
            
        Returns:
            True nếu đăng nhập thành công
        """
        logger.info("Đang chờ đăng nhập...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_logged_in():
                logger.info("Đăng nhập thành công!")
                return True
            time.sleep(2)
        
        logger.error("Timeout chờ đăng nhập")
        return False
    
    def check_and_switch_to_old_sora(self) -> bool:
        """
        Kiểm tra và chuyển sang giao diện Sora cũ nếu cần
        
        Returns:
            True nếu đang ở giao diện cũ hoặc chuyển thành công
        """
        try:
            # Tìm menu button
            menu_btn = self.browser.wait_for_element(
                SELECTORS["menu_button"],
                timeout=5
            )
            
            if menu_btn:
                menu_btn.click()
                time.sleep(1)
                
                # Tìm nút switch to old Sora
                switch_btn = self.browser.wait_for_element(
                    SELECTORS["switch_old_sora"],
                    timeout=3
                )
                
                if switch_btn:
                    switch_btn.click()
                    time.sleep(3)
                    logger.info("Đã chuyển sang giao diện Sora cũ")
                    return True
                else:
                    # Đã ở giao diện cũ
                    # Đóng menu
                    self.browser.execute_script("document.body.click();")
                    return True
            
            return True
            
        except Exception as e:
            logger.warning(f"Không thể kiểm tra giao diện: {e}")
            return True
    def upload_images(self, image_names: str, image_folder: str = "") -> bool:
        """
        Upload nhiều ảnh từ máy tính
        
        Args:
            image_names: Tên các file ảnh, cách nhau bằng dấu phẩy (ví dụ: "nv1.png, nv2.png")
            image_folder: Thư mục chứa ảnh
            
        Returns:
            True nếu upload ít nhất 1 ảnh thành công
        """
        if not image_names or not image_names.strip():
            return False
        
        # Parse danh sách tên ảnh
        image_list = [name.strip() for name in image_names.split(",") if name.strip()]
        
        if not image_list:
            return False
        
        success_count = 0
        
        for image_name in image_list:
            # Ghép đường dẫn đầy đủ
            if image_folder:
                image_path = os.path.join(image_folder, image_name)
            else:
                image_path = image_name
            
            if not os.path.exists(image_path):
                logger.warning(f"Ảnh không tồn tại: {image_path}")
                continue
            
            logger.info(f"Đang upload ảnh: {image_path}")
            
            try:
                # Click nút "+" hoặc "Add images"
                add_image_selectors = [
                    "button[aria-label*='Add']",
                    "button:has-text('+')",
                    "[data-testid='add-image']",
                    ".add-image-btn",
                    "button[aria-label*='image']"
                ]
                
                clicked = False
                for selector in add_image_selectors:
                    if self.browser.click_element(selector):
                        clicked = True
                        break
                
                if not clicked:
                    # Thử XPath
                    xpath = "//button[contains(@aria-label, 'Add')] | //button[contains(text(), '+')]"
                    self.browser.click_element(xpath, by=By.XPATH)
                
                time.sleep(1)
                
                # Click "Upload from device"
                upload_selectors = [
                    "button:has-text('Upload from device')",
                    "div:has-text('Upload from device')",
                    "[data-testid='upload-from-device']",
                    "button[aria-label*='Upload']"
                ]
                
                for selector in upload_selectors:
                    element = self.browser.wait_for_element(selector, timeout=3)
                    if element:
                        element.click()
                        time.sleep(1)
                        break
                else:
                    # Thử XPath
                    xpath = "//button[contains(text(), 'Upload from device')] | //div[contains(text(), 'Upload from device')]"
                    self.browser.click_element(xpath, by=By.XPATH)
                    time.sleep(1)
                
                # Tìm input file và gửi đường dẫn ảnh
                file_inputs = self.browser.find_elements("input[type='file']")
                if file_inputs:
                    file_input = file_inputs[-1]
                    file_input.send_keys(os.path.abspath(image_path))
                    logger.info(f"Đã chọn file ảnh: {image_name}")
                    time.sleep(3)  # Chờ upload xong
                    success_count += 1
                else:
                    logger.error("Không tìm thấy input file")
                
            except Exception as e:
                logger.error(f"Lỗi upload ảnh {image_name}: {e}")
                continue
        
        logger.info(f"Đã upload {success_count}/{len(image_list)} ảnh")
        return success_count > 0
    
    def enter_prompt(self, prompt: str) -> bool:
        """
        Nhập prompt vào ô input
        
        Args:
            prompt: Nội dung prompt
            
        Returns:
            True nếu nhập thành công
        """
        logger.info(f"Đang nhập prompt: {prompt[:50]}...")
        
        # Thử nhiều selector
        selectors = [
            "textarea[placeholder*='prompt']",
            "textarea[placeholder*='Describe']",
            "div[contenteditable='true']",
            "textarea",
            "[data-testid='prompt-input']",
            ".prompt-input"
        ]
        
        for selector in selectors:
            element = self.browser.wait_for_element(selector, timeout=5)
            if element:
                try:
                    element.clear()
                    time.sleep(0.3)
                    element.send_keys(prompt)
                    logger.info("Đã nhập prompt thành công")
                    return True
                except Exception as e:
                    logger.debug(f"Không thể nhập với selector {selector}: {e}")
                    continue
        
        logger.error("Không tìm thấy ô nhập prompt")
        return False
    
    def set_generation_type(self, gen_type: str) -> bool:
        """
        Thiết lập loại generation (image/video)
        
        Args:
            gen_type: 'image' hoặc 'video'
            
        Returns:
            True nếu thiết lập thành công
        """
        logger.info(f"Đang thiết lập loại: {gen_type}")
        
        try:
            # Tìm và click vào type selector
            type_selectors = [
                f"button:has-text('{gen_type}')",
                f"[data-type='{gen_type}']",
                f".type-selector button:contains('{gen_type}')"
            ]
            
            for selector in type_selectors:
                if self.browser.click_element(selector):
                    logger.info(f"Đã chọn loại: {gen_type}")
                    return True
            
            # Thử tìm bằng XPath
            xpath = f"//button[contains(text(), '{gen_type.capitalize()}')]"
            if self.browser.click_element(xpath, by=By.XPATH):
                return True
            
        except Exception as e:
            logger.warning(f"Không thể thiết lập loại: {e}")
        
        return False
    
    def set_aspect_ratio(self, ratio: str) -> bool:
        """Thiết lập tỉ lệ khung hình"""
        logger.info(f"Đang thiết lập tỉ lệ: {ratio}")
        
        try:
            # Click vào aspect ratio selector
            self.browser.click_element(SELECTORS["aspect_ratio_selector"])
            time.sleep(0.5)
            
            # Chọn ratio
            ratio_xpath = f"//button[contains(text(), '{ratio}')] | //div[contains(text(), '{ratio}')]"
            return self.browser.click_element(ratio_xpath, by=By.XPATH)
            
        except Exception as e:
            logger.warning(f"Không thể thiết lập tỉ lệ: {e}")
            return False
    
    def set_duration(self, duration: str) -> bool:
        """Thiết lập thời lượng video"""
        logger.info(f"Đang thiết lập thời lượng: {duration}")
        
        try:
            self.browser.click_element(SELECTORS["duration_selector"])
            time.sleep(0.5)
            
            # Chuyển đổi format (10s -> 10)
            duration_value = duration.replace("s", "").strip()
            duration_xpath = f"//button[contains(text(), '{duration_value}')] | //div[contains(text(), '{duration}')]"
            return self.browser.click_element(duration_xpath, by=By.XPATH)
            
        except Exception as e:
            logger.warning(f"Không thể thiết lập thời lượng: {e}")
            return False
    
    def set_resolution(self, resolution: str) -> bool:
        """Thiết lập độ phân giải"""
        logger.info(f"Đang thiết lập độ phân giải: {resolution}")
        
        try:
            self.browser.click_element(SELECTORS["resolution_selector"])
            time.sleep(0.5)
            
            resolution_xpath = f"//button[contains(text(), '{resolution}')] | //div[contains(text(), '{resolution}')]"
            return self.browser.click_element(resolution_xpath, by=By.XPATH)
            
        except Exception as e:
            logger.warning(f"Không thể thiết lập độ phân giải: {e}")
            return False
    
    def click_generate(self) -> bool:
        """Click nút Generate"""
        logger.info("Đang click nút Generate...")
        
        generate_selectors = [
            "button[data-testid='generate']",
            "button:has-text('Create')",
            "button:has-text('Generate')",
            "button.generate-button",
            "[data-testid='submit-button']"
        ]
        
        for selector in generate_selectors:
            if self.browser.click_element(selector):
                logger.info("Đã click Generate")
                return True
        
        # Thử XPath
        xpaths = [
            "//button[contains(text(), 'Create')]",
            "//button[contains(text(), 'Generate')]",
            "//button[@type='submit']"
        ]
        
        for xpath in xpaths:
            if self.browser.click_element(xpath, by=By.XPATH):
                logger.info("Đã click Generate")
                return True
        
        logger.error("Không tìm thấy nút Generate")
        return False
    
    def wait_for_generation(self, timeout: int = None) -> bool:
        """
        Chờ quá trình generation hoàn thành
        
        Args:
            timeout: Thời gian chờ tối đa
            
        Returns:
            True nếu generation hoàn thành
        """
        timeout = timeout or GENERATION_TIMEOUT
        logger.info(f"Đang chờ generation (timeout: {timeout}s)...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Kiểm tra có đang generating không
            generating = self.browser.find_elements(SELECTORS["generating_indicator"])
            
            if not generating:
                # Kiểm tra đã complete chưa
                complete = self.browser.find_elements(SELECTORS["generation_complete"])
                if complete:
                    logger.info("Generation hoàn thành!")
                    return True
            
            # Kiểm tra có video/image mới không
            videos = self.browser.find_elements("video")
            images = self.browser.find_elements("img[data-generated='true'], .generated-image")
            
            if videos or images:
                time.sleep(2)  # Chờ thêm để đảm bảo load xong
                logger.info("Phát hiện nội dung đã generate!")
                return True
            
            time.sleep(2)
        
        logger.warning("Timeout chờ generation")
        return False
    
    def download_content(self, output_path: str, content_type: str = "video") -> Tuple[bool, str]:
        """
        Download nội dung đã generate
        
        Args:
            output_path: Đường dẫn lưu file
            content_type: 'video' hoặc 'image'
            
        Returns:
            Tuple (success, filepath)
        """
        logger.info(f"Đang download {content_type}...")
        
        # Tạo thư mục output nếu chưa có
        if output_path:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = OUTPUT_DIR
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "mp4" if content_type == "video" else "png"
            output_path = os.path.join(output_dir, f"sora_{timestamp}.{ext}")
        
        try:
            # Click nút download
            download_btn_selectors = [
                "button[aria-label*='download']",
                "button[aria-label*='Download']",
                "[data-testid='download-button']",
                "button.download-btn"
            ]
            
            for selector in download_btn_selectors:
                btn = self.browser.wait_for_clickable(selector, timeout=5)
                if btn:
                    btn.click()
                    time.sleep(1)
                    break
            else:
                # Thử XPath
                xpath = "//button[contains(@aria-label, 'ownload')] | //button[contains(text(), 'Download')]"
                self.browser.click_element(xpath, by=By.XPATH)
                time.sleep(1)
            
            # Nếu có menu download, chọn loại
            if content_type == "video":
                video_option = self.browser.wait_for_element(
                    SELECTORS["download_video_option"],
                    timeout=3
                )
                if video_option:
                    video_option.click()
                    time.sleep(1)
            else:
                image_option = self.browser.wait_for_element(
                    SELECTORS["download_image_option"],
                    timeout=3
                )
                if image_option:
                    image_option.click()
                    time.sleep(1)
            
            # Chờ download hoàn thành
            time.sleep(3)
            
            # Kiểm tra file đã download
            # (Trong thực tế cần kiểm tra thư mục download)
            logger.info(f"Download hoàn thành: {output_path}")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Lỗi download: {e}")
            return False, ""
    
    def get_generated_content_url(self, content_type: str = "video") -> Optional[str]:
        """
        Lấy URL của nội dung đã generate
        
        Args:
            content_type: 'video' hoặc 'image'
            
        Returns:
            URL hoặc None
        """
        try:
            if content_type == "video":
                videos = self.browser.find_elements("video")
                for video in videos:
                    src = video.get_attribute("src")
                    if src:
                        return src
                    # Thử lấy từ source tag
                    sources = video.find_elements(By.TAG_NAME, "source")
                    for source in sources:
                        src = source.get_attribute("src")
                        if src:
                            return src
            else:
                images = self.browser.find_elements("img[data-generated='true'], .generated-image img")
                for img in images:
                    src = img.get_attribute("src")
                    if src and "data:" not in src:
                        return src
            
            return None
            
        except Exception as e:
            logger.error(f"Lỗi lấy URL: {e}")
            return None
    
    def download_from_url(self, url: str, output_path: str) -> bool:
        """
        Download file từ URL
        
        Args:
            url: URL của file
            output_path: Đường dẫn lưu
            
        Returns:
            True nếu thành công
        """
        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Đã download: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi download từ URL: {e}")
            return False
    
    def process_task(self, task: TaskRow) -> Tuple[bool, str]:
        """
        Xử lý một task
        
        Args:
            task: TaskRow object
            
        Returns:
            Tuple (success, message)
        """
        logger.info(f"=== Bắt đầu xử lý task dòng {task.row_number} ===")
        logger.info(f"Prompt: {task.prompt[:100]}...")
        if task.image_path:
            logger.info(f"Image: {task.image_path}")
        
        try:
            # Upload ảnh nếu có
            if task.image_path:
                if not self.upload_image(task.image_path):
                    logger.warning("Đã bỏ qua upload ảnh, tiếp tục với prompt")
            
            # Nhập prompt
            if not self.enter_prompt(task.prompt):
                return False, "Không thể nhập prompt"
            
            time.sleep(1)
            
            # Thiết lập các options
            self.set_generation_type(task.type)
            self.set_aspect_ratio(task.aspect_ratio)
            
            if task.type == "video":
                self.set_duration(task.duration)
            
            self.set_resolution(task.resolution)
            
            time.sleep(1)
            
            # Click generate
            if not self.click_generate():
                return False, "Không thể click Generate"
            
            # Chờ generation
            if not self.wait_for_generation():
                return False, "Timeout chờ generation"
            
            time.sleep(2)
            
            # Download
            success, filepath = self.download_content(task.output_path, task.type)
            
            if success:
                return True, f"Đã lưu: {filepath}"
            else:
                return False, "Lỗi download"
            
        except Exception as e:
            logger.error(f"Lỗi xử lý task: {e}")
            return False, str(e)

# -*- coding: utf-8 -*-
"""
Cấu hình cho Sora Automation Tool
"""

import os

# Đường dẫn gốc
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Thư mục data
DATA_DIR = os.path.join(BASE_DIR, "data")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")

# Tạo thư mục nếu chưa tồn tại
for dir_path in [DATA_DIR, PROFILES_DIR, OUTPUT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# URL
SORA_URL = "https://sora.com"
SORA_LOGIN_URL = "https://sora.com"

# Browser settings
HEADLESS_MODE = False
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Timeouts
PAGE_LOAD_TIMEOUT = 60
ELEMENT_TIMEOUT = 30
GENERATION_TIMEOUT = 300  # 5 phút cho việc generate
DOWNLOAD_TIMEOUT = 120

# Excel settings
EXCEL_TEMPLATE_COLUMNS = [
    "Prompt",           # Nội dung prompt
    "ImagePath",        # Đường dẫn ảnh để upload (tùy chọn)
    "Type",             # image hoặc video
    "AspectRatio",      # 16:9, 9:16, 1:1
    "Duration",         # 5s, 10s, 15s, 20s (cho video)
    "Resolution",       # 480p, 720p, 1080p
    "Variations",       # Số lượng variations
    "OutputPath",       # Đường dẫn lưu file
    "Status",           # Trạng thái xử lý
    "Result"            # Kết quả
]

# Selectors (CSS/XPath)
SELECTORS = {
    # Prompt input
    "prompt_input": "textarea[placeholder*='prompt'], textarea[placeholder*='Describe'], div[contenteditable='true']",
    
    # Generate button
    "generate_button": "button[data-testid='generate'], button:has-text('Create'), button:has-text('Generate')",
    
    # Download button
    "download_button": "button[aria-label*='download'], button[aria-label*='Download'], button:has-text('Download')",
    
    # Download menu options
    "download_video_option": "button:has-text('Video'), div:has-text('Video')",
    "download_image_option": "button:has-text('Image'), div:has-text('Image')",
    
    # Settings
    "aspect_ratio_selector": "button[aria-label*='aspect'], div[data-testid='aspect-ratio']",
    "duration_selector": "button[aria-label*='duration'], div[data-testid='duration']",
    "resolution_selector": "button[aria-label*='resolution'], div[data-testid='resolution']",
    
    # Interface switch (old/new Sora)
    "menu_button": "button[aria-label='More options'], button[aria-label='Menu']",
    "switch_old_sora": "div:has-text('Switch to old Sora'), button:has-text('Switch to old Sora')",
    
    # Generation status
    "generating_indicator": "div[data-testid='generating'], div:has-text('Generating')",
    "generation_complete": "div[data-testid='complete'], video, img[data-generated='true']"
}

# Default values
DEFAULT_TYPE = "video"
DEFAULT_ASPECT_RATIO = "3:2"
DEFAULT_DURATION = "10s"
DEFAULT_RESOLUTION = "720p"
DEFAULT_VARIATIONS = 1

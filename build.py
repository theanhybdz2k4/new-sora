# -*- coding: utf-8 -*-
"""
Build script để đóng gói thành .exe
"""

import PyInstaller.__main__
import os
import shutil

# Đường dẫn
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT_DIR, "dist")
BUILD_DIR = os.path.join(ROOT_DIR, "build")

def build():
    """Đóng gói ứng dụng"""
    
    # Xóa build cũ
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
    
    # PyInstaller options
    PyInstaller.__main__.run([
        'main.py',
        '--name=Sora157',
        '--onedir',
        '--windowed',
        '--icon=assets/icon.ico' if os.path.exists('assets/icon.ico') else '',
        '--add-data=config;config',
        '--hidden-import=PyQt5',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtGui',
        '--hidden-import=selenium',
        '--hidden-import=undetected_chromedriver',
        '--hidden-import=openpyxl',
        '--hidden-import=requests',
        '--collect-all=undetected_chromedriver',
        '--noconfirm',
        '--clean',
    ])
    
    # Tạo thư mục data trong dist
    data_dir = os.path.join(DIST_DIR, "Sora157", "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print("\n✓ Build hoàn thành!")
    print(f"  Output: {os.path.join(DIST_DIR, 'Sora157')}")


if __name__ == "__main__":
    build()

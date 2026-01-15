# -*- coding: utf-8 -*-
"""
Sora Automation Tool - Main Entry Point
"""

import sys
import os

# Thêm đường dẫn root vào Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from gui.main_window import main

if __name__ == "__main__":
    main()

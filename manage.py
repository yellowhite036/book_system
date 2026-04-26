#!/usr/bin/env python
"""Django 指令入口檔。"""
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VENDOR_DIR = BASE_DIR / "vendor"

# 如果專案內有 vendor 套件目錄，就先加入 Python 載入路徑。
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))


def main():
    """執行 Django 管理指令。"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

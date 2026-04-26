"""WSGI 部署入口設定檔。"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VENDOR_DIR = BASE_DIR / "vendor"

# 如果專案內有 vendor 套件目錄，就先加入 Python 載入路徑。
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

from django.core.wsgi import get_wsgi_application

# 指定 Django 設定檔位置。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'library_system.settings')

# 建立 WSGI application，供同步伺服器載入。
application = get_wsgi_application()

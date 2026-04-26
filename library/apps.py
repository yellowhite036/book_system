from django.apps import AppConfig


# 定義 library app 的基本設定。
class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'

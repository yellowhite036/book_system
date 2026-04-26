from django.contrib import admin
from django.urls import include, path

# 主專案路由：管理後台走 admin，主要系統頁面與 API 交給 library app。
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('library.urls')),
]

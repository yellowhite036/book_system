from django.urls import path

from . import views


# 定義圖書館模組的頁面與 API 路由。
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("api/me/", views.current_user, name="current-user"),
    path("api/books/", views.book_list, name="book-list"),
    path("api/loans/", views.loan_list, name="loan-list"),
    path("api/borrow/", views.borrow_book, name="borrow-book"),
    path("api/return/", views.return_book, name="return-book"),
    path("api/chatbot/", views.chatbot, name="chatbot"),
]

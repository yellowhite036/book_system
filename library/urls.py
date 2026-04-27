from django.urls import path

from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("api/me/", views.current_user, name="current-user"),
    path("api/books/", views.book_list, name="book-list"),
    path("api/loans/", views.loan_list, name="loan-list"),
    path("api/requests/", views.request_list, name="request-list"),
    path("api/admin/requests/", views.admin_request_list, name="admin-request-list"),
    path("api/admin/requests/<int:request_id>/approve/", views.admin_request_approve, name="admin-request-approve"),
    path("api/admin/requests/<int:request_id>/reject/", views.admin_request_reject, name="admin-request-reject"),
    path("api/borrow/", views.borrow_book, name="borrow-book"),
    path("api/return/", views.return_book, name="return-book"),
    path("api/chatbot/", views.chatbot, name="chatbot"),
]

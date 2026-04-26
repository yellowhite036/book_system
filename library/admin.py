from django.contrib import admin

from .models import Book, LibraryUser, Loan


# 註冊使用者模型到 Django 後台，方便管理資料。
@admin.register(LibraryUser)
class LibraryUserAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")


# 註冊書籍模型到 Django 後台，方便查看館藏狀況。
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "isbn", "available_copies", "total_copies")
    search_fields = ("title", "author", "isbn", "category")
    list_filter = ("category",)


# 註冊借閱模型到 Django 後台，方便追蹤借閱狀態。
@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "borrowed_at", "due_date", "returned_at", "loan_status")
    list_filter = ("due_date", "returned_at")
    search_fields = ("user__name", "book__title")

    @staticmethod
    # 根據還書時間與逾期狀態回傳對應的借閱文字。
    def loan_status(obj):
        if obj.returned_at:
            return "Returned"
        if obj.is_overdue:
            return "Overdue"
        return "Borrowed"

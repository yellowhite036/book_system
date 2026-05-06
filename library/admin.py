from django.contrib import admin

from .models import Book, LibraryUser, Loan, Question


# 註冊使用者模型到 Django 後台，方便管理資料。
@admin.register(LibraryUser)
class LibraryUserAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "auth_user")
    search_fields = ("name", "email", "auth_user__username")


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
            return "已歸還"
        if obj.is_overdue:
            return "已逾期"
        return "借閱中"


# 註冊提問模型，並自定義回覆邏輯。
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("user", "content_preview", "is_answered_status", "created_at")
    list_filter = ("answered_at", "created_at")
    readonly_fields = ("user", "content", "created_at")
    fields = ("user", "content", "answer", "created_at", "answered_at")

    def content_preview(self, obj):
        return obj.content[:30] + ("..." if len(obj.content) > 30 else "")
    content_preview.short_description = "問題內容"

    def is_answered_status(self, obj):
        return "已回覆" if obj.answer else "待處理"
    is_answered_status.short_description = "狀態"

    def save_model(self, request, obj, form, change):
        # 如果填寫了回覆且尚未設定回覆時間，則自動帶入現在時間。
        if obj.answer and not obj.answered_at:
            from django.utils import timezone
            obj.answered_at = timezone.now()
        super().save_model(request, obj, form, change)

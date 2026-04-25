from django.contrib import admin

from .models import Book, LibraryUser, Loan


@admin.register(LibraryUser)
class LibraryUserAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "isbn", "available_copies", "total_copies")
    search_fields = ("title", "author", "isbn", "category")
    list_filter = ("category",)


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "borrowed_at", "due_date", "returned_at", "loan_status")
    list_filter = ("due_date", "returned_at")
    search_fields = ("user__name", "book__title")

    @staticmethod
    def loan_status(obj):
        if obj.returned_at:
            return "Returned"
        if obj.is_overdue:
            return "Overdue"
        return "Borrowed"

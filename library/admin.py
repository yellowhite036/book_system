from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone

from .models import Book, LibraryUser, Loan, LoanRequest


@admin.register(LibraryUser)
class LibraryUserAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "auth_user")
    search_fields = ("name", "email", "auth_user__username")


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
            return "已歸還"
        if obj.is_overdue:
            return "已逾期"
        return "借閱中"


@admin.action(description="核准選取的申請")
def approve_requests(modeladmin, request, queryset):
    approved_count = 0

    for item in queryset.select_related("book", "loan", "user"):
        if item.status != LoanRequest.STATUS_PENDING:
            continue

        if item.request_type == LoanRequest.REQUEST_BORROW:
            if item.book.available_copies <= 0:
                modeladmin.message_user(
                    request,
                    f"《{item.book.title}》目前沒有可借數量，無法核准借書申請。",
                    level=messages.WARNING,
                )
                continue

            due_date = timezone.localdate() + timedelta(days=14)
            Loan.objects.create(
                user=item.user,
                book=item.book,
                borrowed_at=timezone.now(),
                due_date=due_date,
            )
            item.book.available_copies -= 1
            item.book.save(update_fields=["available_copies"])

        elif item.request_type == LoanRequest.REQUEST_RETURN:
            if not item.loan or item.loan.returned_at:
                modeladmin.message_user(
                    request,
                    f"{item.user.name} 的還書申請已失效或該借閱已歸還。",
                    level=messages.WARNING,
                )
                continue

            item.loan.returned_at = timezone.now()
            item.loan.save(update_fields=["returned_at"])
            item.book.available_copies += 1
            item.book.save(update_fields=["available_copies"])

        item.status = LoanRequest.STATUS_APPROVED
        item.reviewed_at = timezone.now()
        item.reviewed_by = request.user
        item.review_note = "已由管理員核准"
        item.save(update_fields=["status", "reviewed_at", "reviewed_by", "review_note"])
        approved_count += 1

    modeladmin.message_user(request, f"已核准 {approved_count} 筆申請。")


@admin.action(description="拒絕選取的申請")
def reject_requests(modeladmin, request, queryset):
    updated = queryset.filter(status=LoanRequest.STATUS_PENDING).update(
        status=LoanRequest.STATUS_REJECTED,
        reviewed_at=timezone.now(),
        reviewed_by=request.user,
        review_note="已由管理員拒絕",
    )
    modeladmin.message_user(request, f"已拒絕 {updated} 筆申請。")


@admin.register(LoanRequest)
class LoanRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "request_type", "status", "created_at", "reviewed_at", "reviewed_by")
    list_filter = ("request_type", "status", "created_at")
    search_fields = ("user__name", "book__title", "user__auth_user__username")
    readonly_fields = ("created_at", "reviewed_at", "reviewed_by")
    actions = [approve_requests, reject_requests]

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class LibraryUser(models.Model):
    # 儲存可以登入並借還書的圖書館使用者資料。
    auth_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="library_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    # 儲存圖書館書籍資料以及目前館藏數量。
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.title} - {self.author}"


class Loan(models.Model):
    # 儲存已核准成立的實際借閱紀錄。
    user = models.ForeignKey(LibraryUser, on_delete=models.CASCADE, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loans")
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["returned_at", "due_date", "-borrowed_at"]

    def __str__(self):
        return f"{self.user} -> {self.book}"

    @property
    def is_returned(self):
        return self.returned_at is not None

    @property
    def is_overdue(self):
        return not self.is_returned and self.due_date < timezone.localdate()


class LoanRequest(models.Model):
    # 儲存借書或還書申請，必須經過 admin 核准後才會生效。
    REQUEST_BORROW = "borrow"
    REQUEST_RETURN = "return"
    REQUEST_TYPE_CHOICES = [
        (REQUEST_BORROW, "Borrow"),
        (REQUEST_RETURN, "Return"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    user = models.ForeignKey(LibraryUser, on_delete=models.CASCADE, related_name="loan_requests")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loan_requests")
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="requests", null=True, blank=True)
    request_type = models.CharField(max_length=10, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_loan_requests",
    )
    review_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} {self.request_type} {self.book} ({self.status})"

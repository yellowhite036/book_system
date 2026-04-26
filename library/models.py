from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


# 儲存可以登入並借還書的圖書館使用者資料。
class LibraryUser(models.Model):
    auth_user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="library_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    # 在 Django 後台與除錯輸出中顯示使用者名稱。
    def __str__(self):
        return self.name


# 儲存圖書館書籍資料以及目前館藏數量。
class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    isbn = models.CharField(max_length=20, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    # 在後台與紀錄中顯示較易讀的書籍名稱格式。
    def __str__(self):
        return f"{self.title} - {self.author}"


# 儲存每一筆借閱紀錄，連接使用者與書籍。
class Loan(models.Model):
    user = models.ForeignKey(LibraryUser, on_delete=models.CASCADE, related_name="loans")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="loans")
    borrowed_at = models.DateTimeField(default=timezone.now)
    due_date = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["returned_at", "due_date", "-borrowed_at"]

    # 在後台與紀錄中顯示借閱關係。
    def __str__(self):
        return f"{self.user} -> {self.book}"

    @property
    # 判斷這筆借閱是否已完成還書。
    def is_returned(self):
        return self.returned_at is not None

    @property
    # 只有尚未歸還且超過到期日時，才算逾期。
    def is_overdue(self):
        return not self.is_returned and self.due_date < timezone.localdate()

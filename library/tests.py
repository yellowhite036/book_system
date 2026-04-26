from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Book, LibraryUser, Loan


# 測試借閱模型中的逾期判斷是否正確。
class LoanModelTests(TestCase):
    # 建立一筆昨天到期的借閱資料，確認系統會判定為逾期。
    def test_overdue_detection(self):
        auth_user = User.objects.create_user(username="tester", password="library123")
        user = LibraryUser.objects.create(
            auth_user=auth_user,
            name="Tester",
            email="tester@example.com",
        )
        book = Book.objects.create(
            title="Test Book",
            author="Author",
            isbn="9789860009999",
            total_copies=1,
            available_copies=1,
        )
        loan = Loan.objects.create(
            user=user,
            book=book,
            due_date=timezone.localdate() - timedelta(days=1),
        )
        self.assertTrue(loan.is_overdue)

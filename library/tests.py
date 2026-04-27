from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Book, LibraryUser, Loan, LoanRequest


class LoanModelTests(TestCase):
    # 測試借閱模型中的逾期判斷是否正確。
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

    # 測試借書申請建立後，預設狀態應為待審核。
    def test_loan_request_defaults_to_pending(self):
        auth_user = User.objects.create_user(username="requester", password="library123")
        user = LibraryUser.objects.create(
            auth_user=auth_user,
            name="Requester",
            email="requester@example.com",
        )
        book = Book.objects.create(
            title="Approval Book",
            author="Author",
            isbn="9789860010000",
            total_copies=2,
            available_copies=2,
        )
        request_record = LoanRequest.objects.create(
            user=user,
            book=book,
            request_type=LoanRequest.REQUEST_BORROW,
        )
        self.assertEqual(request_record.status, LoanRequest.STATUS_PENDING)

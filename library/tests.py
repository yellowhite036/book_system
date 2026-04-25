from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Book, LibraryUser, Loan


class LoanModelTests(TestCase):
    def test_overdue_detection(self):
        user = LibraryUser.objects.create(name="Tester", email="tester@example.com")
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

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .chatbot import get_chatbot_default_mode
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


class IndexViewTests(TestCase):
    def test_index_context_includes_initial_chatbot_mode(self):
        auth_user = User.objects.create_user(username="viewer", password="library123")
        LibraryUser.objects.create(
            auth_user=auth_user,
            name="Viewer",
            email="viewer@example.com",
        )

        self.client.login(username="viewer", password="library123")
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["initial_chatbot_mode"],
            get_chatbot_default_mode(),
        )


class RegisterViewTests(TestCase):
    def test_register_creates_library_user_and_logs_in(self):
        response = self.client.post(
            "/register/",
            {
                "name": "New Reader",
                "email": "reader@example.com",
                "username": "reader",
                "password": "library123",
                "confirm_password": "library123",
            },
        )

        self.assertRedirects(response, "/")
        self.assertTrue(User.objects.filter(username="reader").exists())
        self.assertTrue(LibraryUser.objects.filter(email="reader@example.com").exists())

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(username="reader", password="library123")

        response = self.client.post(
            "/register/",
            {
                "name": "New Reader",
                "email": "reader@example.com",
                "username": "reader",
                "password": "library123",
                "confirm_password": "library123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "這個帳號已經被使用。")
        self.assertFalse(LibraryUser.objects.filter(email="reader@example.com").exists())

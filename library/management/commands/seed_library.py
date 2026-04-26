from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from library.models import Book, LibraryUser, Loan


# 建立自訂管理指令，用來快速匯入示範資料。
class Command(BaseCommand):
    help = "Seed sample books, users, and loans for the demo library system."

    # 建立示範使用者、書籍，以及一筆逾期和一筆正常借閱資料。
    def handle(self, *args, **options):
        users = [
            {"name": "Alice Chen", "email": "alice@example.com"},
            {"name": "Brian Lin", "email": "brian@example.com"},
            {"name": "Cindy Wu", "email": "cindy@example.com"},
        ]
        books = [
            {
                "title": "Python Web Development",
                "author": "James Lee",
                "isbn": "9789860000001",
                "category": "Programming",
                "description": "A beginner-friendly guide to building web services with Python.",
                "total_copies": 3,
                "available_copies": 3,
            },
            {
                "title": "RESTful API Design",
                "author": "Sarah Wang",
                "isbn": "9789860000002",
                "category": "Backend",
                "description": "Covers API resource modeling, status codes, and clean endpoint design.",
                "total_copies": 2,
                "available_copies": 2,
            },
            {
                "title": "Intro to Retrieval Augmented Generation",
                "author": "Kevin Huang",
                "isbn": "9789860000003",
                "category": "AI",
                "description": "Explains embeddings, retrieval pipelines, and how RAG improves chatbot quality.",
                "total_copies": 2,
                "available_copies": 2,
            },
        ]

        # 若資料已存在就更新，否則建立新的示範使用者與書籍。
        created_users = [LibraryUser.objects.update_or_create(email=row["email"], defaults=row)[0] for row in users]
        created_books = [Book.objects.update_or_create(isbn=row["isbn"], defaults=row)[0] for row in books]

        # 建立一筆逾期中的借閱資料，方便展示逾期功能。
        overdue_loan, created = Loan.objects.get_or_create(
            user=created_users[0],
            book=created_books[0],
            returned_at__isnull=True,
            defaults={
                "borrowed_at": timezone.now() - timedelta(days=20),
                "due_date": timezone.localdate() - timedelta(days=6),
            },
        )
        if created:
            overdue_loan.book.available_copies = max(0, overdue_loan.book.available_copies - 1)
            overdue_loan.book.save(update_fields=["available_copies"])

        # 建立一筆尚未到期的借閱資料，方便展示一般借閱狀態。
        active_loan, created = Loan.objects.get_or_create(
            user=created_users[1],
            book=created_books[1],
            returned_at__isnull=True,
            defaults={
                "borrowed_at": timezone.now() - timedelta(days=3),
                "due_date": timezone.localdate() + timedelta(days=11),
            },
        )
        if created:
            active_loan.book.available_copies = max(0, active_loan.book.available_copies - 1)
            active_loan.book.save(update_fields=["available_copies"])

        self.stdout.write(self.style.SUCCESS("Sample library data created."))

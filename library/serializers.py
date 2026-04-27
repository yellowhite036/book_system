from rest_framework import serializers

from .models import Book, LibraryUser, Loan, LoanRequest


class LibraryUserSerializer(serializers.ModelSerializer):
    # 將目前登入的圖書館使用者資料轉成 API 可回傳的 JSON 格式。
    username = serializers.CharField(source="auth_user.username", read_only=True)

    class Meta:
        model = LibraryUser
        fields = ["id", "name", "email", "username"]


class BookSerializer(serializers.ModelSerializer):
    # 將 Book 模型資料轉成 API 可回傳的 JSON 格式。
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "isbn",
            "category",
            "description",
            "total_copies",
            "available_copies",
        ]


class LoanSerializer(serializers.ModelSerializer):
    # 將 Loan 模型資料轉成 JSON，並額外提供借閱狀態欄位。
    user_name = serializers.CharField(source="user.name", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_returned = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            "id",
            "user",
            "user_name",
            "book",
            "book_title",
            "borrowed_at",
            "due_date",
            "returned_at",
            "is_overdue",
            "is_returned",
        ]


class LoanRequestSerializer(serializers.ModelSerializer):
    # 將借還書申請資料轉成 JSON，顯示給前端查看審核狀態。
    user_name = serializers.CharField(source="user.name", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    reviewed_by_username = serializers.CharField(source="reviewed_by.username", read_only=True)

    class Meta:
        model = LoanRequest
        fields = [
            "id",
            "user",
            "user_name",
            "book",
            "book_title",
            "loan",
            "request_type",
            "status",
            "created_at",
            "reviewed_at",
            "reviewed_by_username",
            "review_note",
        ]

from rest_framework import serializers

from .models import Book, LibraryUser, Loan, Question


# 將目前登入的圖書館使用者資料轉成 API 可回傳的 JSON 格式。
class LibraryUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="auth_user.username", read_only=True)

    class Meta:
        model = LibraryUser
        fields = ["id", "name", "email", "username"]


# 將 Book 模型資料轉成 API 可回傳的 JSON 格式。
class BookSerializer(serializers.ModelSerializer):
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


# 將 Loan 模型資料轉成 JSON，並額外提供借閱狀態欄位。
class LoanSerializer(serializers.ModelSerializer):
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


# 將使用者提問轉成 JSON 格式。
class QuestionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    is_answered = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "user_name",
            "content",
            "answer",
            "created_at",
            "answered_at",
            "is_answered",
        ]

    def get_is_answered(self, obj):
        return obj.answer is not None and obj.answer != ""

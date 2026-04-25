from rest_framework import serializers

from .models import Book, LibraryUser, Loan


# Convert LibraryUser model data into JSON for the API.
class LibraryUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibraryUser
        fields = ["id", "name", "email"]


# Convert Book model data into JSON for the API.
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


# Convert Loan model data into JSON and expose computed status fields.
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

from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .chatbot import build_chatbot_reply
from .models import Book, LibraryUser, Loan
from .serializers import BookSerializer, LibraryUserSerializer, LoanSerializer


# Render the single-page web UI.
def index(request):
    return render(request, "library/index.html")


@api_view(["GET"])
# Return all users so the frontend can choose who is borrowing books.
def user_list(request):
    users = LibraryUser.objects.all().order_by("name")
    return Response(LibraryUserSerializer(users, many=True).data)


@api_view(["GET"])
# Return the full book catalog.
def book_list(request):
    books = Book.objects.all().order_by("title")
    return Response(BookSerializer(books, many=True).data)


@api_view(["GET"])
# Return loan records, optionally filtered to one user.
def loan_list(request):
    loans = Loan.objects.select_related("user", "book").all()
    user_id = request.GET.get("user_id")
    if user_id:
        loans = loans.filter(user_id=user_id)
    return Response(LoanSerializer(loans, many=True).data)


@api_view(["POST"])
# Create a loan and decrease the available inventory count.
def borrow_book(request):
    user = get_object_or_404(LibraryUser, pk=request.data.get("user_id"))
    book = get_object_or_404(Book, pk=request.data.get("book_id"))

    # Use a transaction so the loan record and inventory update stay consistent.
    with transaction.atomic():
        book.refresh_from_db()
        if book.available_copies <= 0:
            return Response({"detail": "No copies are currently available for this book."}, status=status.HTTP_400_BAD_REQUEST)

        due_date = timezone.localdate() + timedelta(days=14)
        loan = Loan.objects.create(user=user, book=book, due_date=due_date)
        book.available_copies -= 1
        book.save(update_fields=["available_copies"])

    return Response(
        {
            "detail": f"{user.name} borrowed '{book.title}'.",
            "loan": LoanSerializer(loan).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
# Mark a loan as returned and restore one available copy.
def return_book(request):
    loan = get_object_or_404(Loan.objects.select_related("book", "user"), pk=request.data.get("loan_id"))
    if loan.returned_at:
        return Response({"detail": "This loan has already been returned."}, status=status.HTTP_400_BAD_REQUEST)

    # Use a transaction so the loan status and inventory update succeed together.
    with transaction.atomic():
        loan.returned_at = timezone.now()
        loan.save(update_fields=["returned_at"])
        loan.book.available_copies += 1
        loan.book.save(update_fields=["available_copies"])

    return Response(
        {
            "detail": f"{loan.user.name} returned '{loan.book.title}'.",
            "loan": LoanSerializer(loan).data,
        }
    )


@api_view(["POST"])
# Pass the user's message into the chatbot helper and return its answer.
def chatbot(request):
    user = None
    user_id = request.data.get("user_id")
    if user_id:
        user = LibraryUser.objects.filter(pk=user_id).first()

    reply = build_chatbot_reply(request.data.get("message"), user=user)
    return Response({"reply": reply})

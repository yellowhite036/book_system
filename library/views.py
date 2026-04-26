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


# 顯示系統首頁的單頁式操作介面。
def index(request):
    return render(request, "library/index.html")


@api_view(["GET"])
# 回傳所有使用者，讓前端可以選擇目前操作的借閱者。
def user_list(request):
    users = LibraryUser.objects.all().order_by("name")
    return Response(LibraryUserSerializer(users, many=True).data)


@api_view(["GET"])
# 回傳完整書單資料。
def book_list(request):
    books = Book.objects.all().order_by("title")
    return Response(BookSerializer(books, many=True).data)


@api_view(["GET"])
# 回傳借閱紀錄，也支援依使用者篩選。
def loan_list(request):
    loans = Loan.objects.select_related("user", "book").all()
    user_id = request.GET.get("user_id")
    if user_id:
        loans = loans.filter(user_id=user_id)
    return Response(LoanSerializer(loans, many=True).data)


@api_view(["POST"])
# 建立借閱紀錄，並同步扣除可借數量。
def borrow_book(request):
    user = get_object_or_404(LibraryUser, pk=request.data.get("user_id"))
    book = get_object_or_404(Book, pk=request.data.get("book_id"))

    # 使用交易機制，確保借閱紀錄與庫存更新同時成功。
    with transaction.atomic():
        book.refresh_from_db()
        if book.available_copies <= 0:
            return Response({"detail": "這本書目前沒有可借數量。"}, status=status.HTTP_400_BAD_REQUEST)

        due_date = timezone.localdate() + timedelta(days=14)
        loan = Loan.objects.create(user=user, book=book, due_date=due_date)
        book.available_copies -= 1
        book.save(update_fields=["available_copies"])

    return Response(
        {
            "detail": f"{user.name} 已借閱《{book.title}》。",
            "loan": LoanSerializer(loan).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
# 將借閱標記為已歸還，並恢復一本可借館藏。
def return_book(request):
    loan = get_object_or_404(Loan.objects.select_related("book", "user"), pk=request.data.get("loan_id"))
    if loan.returned_at:
        return Response({"detail": "這筆借閱已經完成歸還。"}, status=status.HTTP_400_BAD_REQUEST)

    # 使用交易機制，確保還書狀態與庫存更新一致。
    with transaction.atomic():
        loan.returned_at = timezone.now()
        loan.save(update_fields=["returned_at"])
        loan.book.available_copies += 1
        loan.book.save(update_fields=["available_copies"])

    return Response(
        {
            "detail": f"{loan.user.name} 已歸還《{loan.book.title}》。",
            "loan": LoanSerializer(loan).data,
        }
    )


@api_view(["POST"])
# 將使用者訊息交給 chatbot 邏輯處理，並回傳回答內容。
def chatbot(request):
    user = None
    user_id = request.data.get("user_id")
    if user_id:
        user = LibraryUser.objects.filter(pk=user_id).first()

    reply = build_chatbot_reply(request.data.get("message"), user=user)
    return Response({"reply": reply})

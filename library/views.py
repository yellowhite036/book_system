from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .chatbot import build_chatbot_reply, get_chatbot_default_mode
from .models import Book, LibraryUser, Loan, Question
from .serializers import BookSerializer, LibraryUserSerializer, LoanSerializer, QuestionSerializer


# 取得目前登入者對應的圖書館使用者資料。
def get_current_library_user(request):
    if not request.user.is_authenticated:
        return None
    return LibraryUser.objects.filter(auth_user=request.user).first()


# 顯示登入頁面，已登入者直接進入首頁。
def login_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    error_message = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("index")
        error_message = "帳號或密碼錯誤，請重新輸入。"

    return render(request, "library/login.html", {"error_message": error_message})


# 登出目前使用者並返回登入頁面。
def register_view(request):
    if request.user.is_authenticated:
        return redirect("index")

    error_message = ""
    form_data = {
        "name": "",
        "email": "",
        "username": "",
    }

    if request.method == "POST":
        form_data = {
            "name": request.POST.get("name", "").strip(),
            "email": request.POST.get("email", "").strip(),
            "username": request.POST.get("username", "").strip(),
        }
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([form_data["name"], form_data["email"], form_data["username"], password, confirm_password]):
            error_message = "請完整填寫註冊資料。"
        elif password != confirm_password:
            error_message = "兩次輸入的密碼不一致。"
        elif User.objects.filter(username=form_data["username"]).exists():
            error_message = "這個帳號已經被使用。"
        elif LibraryUser.objects.filter(email=form_data["email"]).exists():
            error_message = "這個 Email 已經註冊過。"
        else:
            with transaction.atomic():
                auth_user = User.objects.create_user(
                    username=form_data["username"],
                    email=form_data["email"],
                    password=password,
                )
                LibraryUser.objects.create(
                    auth_user=auth_user,
                    name=form_data["name"],
                    email=form_data["email"],
                )
            login(request, auth_user)
            return redirect("index")

    return render(
        request,
        "library/register.html",
        {
            "error_message": error_message,
            "form_data": form_data,
        },
    )


@login_required
def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("login"))


# 顯示系統首頁的單頁式操作介面。
@login_required
def index(request):
    return render(
        request,
        "library/index.html",
        {
            "initial_chatbot_mode": get_chatbot_default_mode(),
        },
    )


# 回傳目前登入的圖書館使用者資料。
@api_view(["GET"])
def current_user(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    data = LibraryUserSerializer(user).data
    data["chatbot_mode"] = get_chatbot_default_mode()
    return Response(data)


# 回傳完整書單資料。
@api_view(["GET"])
def book_list(request):
    if not request.user.is_authenticated:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    books = Book.objects.all().order_by("title")
    return Response(BookSerializer(books, many=True).data)


# 回傳目前登入者自己的借閱紀錄。
@api_view(["GET"])
def loan_list(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    loans = Loan.objects.select_related("user", "book").filter(user=user)
    return Response(LoanSerializer(loans, many=True).data)


# 建立借閱紀錄，並同步扣除可借數量。
@api_view(["POST"])
def borrow_book(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

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


# 將借閱標記為已歸還，並恢復一本可借館藏。
@api_view(["POST"])
def return_book(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

    loan = get_object_or_404(
        Loan.objects.select_related("book", "user"),
        pk=request.data.get("loan_id"),
        user=user,
    )
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


# 將使用者訊息交給 chatbot 邏輯處理，並回傳回答內容。
@api_view(["POST"])
def chatbot(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

    result = build_chatbot_reply(request.data.get("message"), user=user)
    return Response(
        {
            "reply": result["reply"],
            "mode": result["mode_label"],
            "mode_code": result["mode_code"],
        }
    )


# 回傳目前使用者的問題列表。
@api_view(["GET"])
def question_list(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    questions = Question.objects.filter(user=user)
    return Response(QuestionSerializer(questions, many=True).data)


# 提交新問題。
@api_view(["POST"])
def ask_question(request):
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

    content = request.data.get("content", "").strip()
    if not content:
        return Response({"detail": "問題內容不能為空。"}, status=status.HTTP_400_BAD_REQUEST)

    question = Question.objects.create(user=user, content=content)
    return Response(
        {
            "detail": "問題已提交，請稍候管理員回覆。",
            "question": QuestionSerializer(question).data,
        },
        status=status.HTTP_201_CREATED,
    )

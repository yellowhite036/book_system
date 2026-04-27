from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .chatbot import build_chatbot_reply, get_chatbot_default_mode
from .models import Book, LibraryUser, Loan, LoanRequest
from .serializers import BookSerializer, LibraryUserSerializer, LoanRequestSerializer, LoanSerializer


def get_current_library_user(request):
    # 取得目前登入者對應的圖書館使用者資料。
    if not request.user.is_authenticated:
        return None

    library_user = LibraryUser.objects.filter(auth_user=request.user).first()
    if library_user:
        return library_user

    if request.user.email:
        library_user, _ = LibraryUser.objects.get_or_create(
            email=request.user.email,
            defaults={
                "auth_user": request.user,
                "name": request.user.get_full_name() or request.user.username,
            },
        )
    else:
        library_user = LibraryUser.objects.create(
            auth_user=request.user,
            name=request.user.get_full_name() or request.user.username,
            email=f"{request.user.username}@library.local",
        )

    if library_user.auth_user_id != request.user.id:
        library_user.auth_user = request.user
        library_user.save(update_fields=["auth_user"])

    return library_user


def login_view(request):
    # 顯示登入頁面，已登入者直接進入首頁。
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


@login_required
def logout_view(request):
    # 登出目前使用者並返回登入頁面。
    logout(request)
    return HttpResponseRedirect(reverse("login"))


@login_required
def index(request):
    # 顯示系統首頁的單頁式操作介面。
    return render(
        request,
        "library/index.html",
        {
            "initial_chatbot_mode": get_chatbot_default_mode(),
        },
    )


@api_view(["GET"])
def current_user(request):
    # 回傳目前登入的圖書館使用者資料。
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

    data = LibraryUserSerializer(user).data
    data["chatbot_mode"] = get_chatbot_default_mode()
    data["is_admin"] = bool(request.user.is_staff or request.user.is_superuser)
    return Response(data)


@api_view(["GET"])
def book_list(request):
    # 回傳完整書單資料。
    if not request.user.is_authenticated:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    books = Book.objects.all().order_by("title")
    return Response(BookSerializer(books, many=True).data)


@api_view(["GET"])
def loan_list(request):
    # 回傳目前登入者自己的借閱紀錄。
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    loans = Loan.objects.select_related("user", "book").filter(user=user)
    return Response(LoanSerializer(loans, many=True).data)


@api_view(["GET"])
def request_list(request):
    # 回傳目前登入者自己的借還書申請紀錄。
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    requests = LoanRequest.objects.select_related("user", "book", "reviewed_by").filter(user=user)
    return Response(LoanRequestSerializer(requests, many=True).data)


@api_view(["GET"])
def admin_request_list(request):
    # 回傳所有待審核申請，僅限 admin 使用。
    if not request.user.is_authenticated:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({"detail": "只有管理員可以查看待審核申請。"}, status=status.HTTP_403_FORBIDDEN)

    requests = LoanRequest.objects.select_related("user", "book", "reviewed_by", "loan").filter(
        status=LoanRequest.STATUS_PENDING
    )
    return Response(LoanRequestSerializer(requests, many=True).data)


@api_view(["POST"])
def admin_request_approve(request, request_id):
    # 管理員核准借還書申請。
    if not request.user.is_authenticated:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({"detail": "只有管理員可以核准申請。"}, status=status.HTTP_403_FORBIDDEN)

    request_record = get_object_or_404(
        LoanRequest.objects.select_related("user", "book", "loan"),
        pk=request_id,
    )
    if request_record.status != LoanRequest.STATUS_PENDING:
        return Response({"detail": "這筆申請不是待審核狀態。"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if request_record.request_type == LoanRequest.REQUEST_BORROW:
            request_record.book.refresh_from_db()
            if request_record.book.available_copies <= 0:
                return Response({"detail": "這本書目前沒有可借數量，無法核准。"}, status=status.HTTP_400_BAD_REQUEST)

            loan = Loan.objects.create(
                user=request_record.user,
                book=request_record.book,
                borrowed_at=timezone.now(),
                due_date=timezone.localdate() + timedelta(days=14),
            )
            request_record.book.available_copies -= 1
            request_record.book.save(update_fields=["available_copies"])
            request_record.loan = loan

        elif request_record.request_type == LoanRequest.REQUEST_RETURN:
            if not request_record.loan or request_record.loan.returned_at:
                return Response({"detail": "這筆還書申請已失效或借閱已完成歸還。"}, status=status.HTTP_400_BAD_REQUEST)

            request_record.loan.returned_at = timezone.now()
            request_record.loan.save(update_fields=["returned_at"])
            request_record.book.available_copies += 1
            request_record.book.save(update_fields=["available_copies"])

        request_record.status = LoanRequest.STATUS_APPROVED
        request_record.reviewed_at = timezone.now()
        request_record.reviewed_by = request.user
        request_record.review_note = "已由管理員核准"
        request_record.save(
            update_fields=["status", "reviewed_at", "reviewed_by", "review_note", "loan"]
        )

    return Response({"detail": "申請已核准。"})


@api_view(["POST"])
def admin_request_reject(request, request_id):
    # 管理員拒絕借還書申請。
    if not request.user.is_authenticated:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({"detail": "只有管理員可以拒絕申請。"}, status=status.HTTP_403_FORBIDDEN)

    request_record = get_object_or_404(LoanRequest, pk=request_id)
    if request_record.status != LoanRequest.STATUS_PENDING:
        return Response({"detail": "這筆申請不是待審核狀態。"}, status=status.HTTP_400_BAD_REQUEST)

    request_record.status = LoanRequest.STATUS_REJECTED
    request_record.reviewed_at = timezone.now()
    request_record.reviewed_by = request.user
    request_record.review_note = "已由管理員拒絕"
    request_record.save(update_fields=["status", "reviewed_at", "reviewed_by", "review_note"])
    return Response({"detail": "申請已拒絕。"})


@api_view(["POST"])
def borrow_book(request):
    # 建立借書申請，待 admin 核准後才會真正借出。
    user = get_current_library_user(request)
    if user is None:
        return Response({"detail": "請先登入。"}, status=status.HTTP_401_UNAUTHORIZED)

    book = get_object_or_404(Book, pk=request.data.get("book_id"))
    has_pending = LoanRequest.objects.filter(
        user=user,
        book=book,
        request_type=LoanRequest.REQUEST_BORROW,
        status=LoanRequest.STATUS_PENDING,
    ).exists()
    if has_pending:
        return Response({"detail": "你已經送出這本書的借書申請，請等待管理員審核。"}, status=status.HTTP_400_BAD_REQUEST)

    request_record = LoanRequest.objects.create(
        user=user,
        book=book,
        request_type=LoanRequest.REQUEST_BORROW,
    )
    return Response(
        {
            "detail": f"已送出《{book.title}》的借書申請，等待管理員審核。",
            "request": LoanRequestSerializer(request_record).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def return_book(request):
    # 建立還書申請，待 admin 核准後才會真正歸還。
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

    has_pending = LoanRequest.objects.filter(
        user=user,
        loan=loan,
        request_type=LoanRequest.REQUEST_RETURN,
        status=LoanRequest.STATUS_PENDING,
    ).exists()
    if has_pending:
        return Response({"detail": "你已經送出這筆借閱的還書申請，請等待管理員審核。"}, status=status.HTTP_400_BAD_REQUEST)

    request_record = LoanRequest.objects.create(
        user=user,
        book=loan.book,
        loan=loan,
        request_type=LoanRequest.REQUEST_RETURN,
    )
    return Response(
        {
            "detail": f"已送出《{loan.book.title}》的還書申請，等待管理員審核。",
            "request": LoanRequestSerializer(request_record).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def chatbot(request):
    # 將使用者訊息交給 chatbot 邏輯處理，並回傳回答內容。
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

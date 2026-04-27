import json
import logging
import os
import urllib.error
import urllib.request
from collections import Counter

from django.utils import timezone

from .models import Loan

logger = logging.getLogger(__name__)


# 內建的小型知識庫，用來模擬 RAG 檢索式回答。
KNOWLEDGE_BASE = [
    {
        "title": "借書規則",
        "content": "使用者可以借閱目前仍有可借數量的書籍。借書成功後，系統會建立借閱紀錄，並預設給予十四天的借閱期限。",
        "keywords": ["借書", "借閱規則", "借閱", "規則", "borrow"],
    },
    {
        "title": "還書規則",
        "content": "使用者還書後，系統會將該筆借閱標記為已歸還，並自動把書籍的可借數量加一。",
        "keywords": ["還書", "歸還", "return"],
    },
    {
        "title": "逾期規則",
        "content": "如果今天日期已超過借閱到期日，而且該書尚未歸還，系統就會將這筆借閱顯示為逾期。",
        "keywords": ["逾期", "到期", "期限", "due", "overdue"],
    },
    {
        "title": "系統功能",
        "content": "這個系統可以查看書單、登入個人帳號、借書、還書、查看借閱期限，並提供簡易客服 chatbot 問答。",
        "keywords": ["功能", "系統", "chatbot", "客服", "rag", "llm", "登入"],
    },
]


# 將英文與數字切成可比對的片段，方便做簡單關鍵字比對。
def _tokenize(text):
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return [token for token in normalized.split() if token]


# 根據關鍵字與中英文內容，找出最相關的知識片段。
def _retrieve_context(message):
    lowered_message = message.lower()
    query_tokens = Counter(_tokenize(message))
    ranked = []

    for item in KNOWLEDGE_BASE:
        content = f"{item['title']} {item['content']}"
        content_tokens = Counter(_tokenize(content))
        token_score = sum((query_tokens & content_tokens).values())
        keyword_score = sum(2 for keyword in item["keywords"] if keyword.lower() in lowered_message or keyword in message)
        title_score = 3 if item["title"] in message else 0
        total_score = token_score + keyword_score + title_score
        ranked.append((total_score, item))

    ranked.sort(key=lambda row: row[0], reverse=True)
    return [item for score, item in ranked if score > 0][:3]


# 判斷是否只是簡單打招呼。
def _is_greeting(message):
    normalized = message.strip().lower()
    greetings = {"hi", "hello", "hey", "你好", "嗨", "哈囉", "您好", "早安", "午安", "晚安"}
    return normalized in greetings


# 判斷訊息是否在問歷史借閱紀錄。
def _is_history_question(message, lowered_message):
    history_keywords = ["借過", "歷史借閱", "借閱紀錄", "借閱歷史", "以前借過", "曾經借過", "history", "borrowed before"]
    return any(keyword in message or keyword in lowered_message for keyword in history_keywords)


# 判斷訊息是否在問目前尚未歸還的借閱狀態。
def _is_active_loan_question(message, lowered_message):
    active_keywords = ["目前借", "現在借", "還沒還", "未歸還", "到期", "逾期", "我的書", "my loan", "due", "overdue", "active loan"]
    return any(keyword in message or keyword in lowered_message for keyword in active_keywords)


# 判斷訊息是否在問已歸還紀錄。
def _is_return_history_question(message, lowered_message):
    return_keywords = ["還過", "有還書嗎", "歸還紀錄", "還書紀錄", "已歸還", "returned", "return history"]
    return any(keyword in message or keyword in lowered_message for keyword in return_keywords)


# 將目前登入者的借閱資料整理成可放入 prompt 的文字。
def _build_user_context(user):
    if user is None:
        return "目前沒有登入中的圖書館使用者資料。"

    all_loans = Loan.objects.select_related("book").filter(user=user).order_by("-borrowed_at")
    active_loans = all_loans.filter(returned_at__isnull=True)
    returned_loans = all_loans.filter(returned_at__isnull=False)
    today = timezone.localdate()

    lines = [
        f"使用者姓名：{user.name}",
        f"使用者電子郵件：{user.email}",
        f"今日日期：{today}",
    ]

    if active_loans.exists():
        lines.append("目前尚未歸還的書籍：")
        for loan in active_loans[:10]:
            overdue_text = "已逾期" if loan.due_date < today else "未逾期"
            lines.append(f"- 《{loan.book.title}》到期日：{loan.due_date}，狀態：{overdue_text}")
    else:
        lines.append("目前尚未歸還的書籍：無")

    if returned_loans.exists():
        lines.append("已歸還紀錄：")
        for loan in returned_loans[:10]:
            lines.append(f"- 《{loan.book.title}》借閱日：{loan.borrowed_at.date()}，歸還日：{loan.returned_at.date()}")
    else:
        lines.append("已歸還紀錄：無")

    return "\n".join(lines)


# 將知識庫片段整理成可放入 prompt 的文字。
def _build_knowledge_context(message):
    retrieved = _retrieve_context(message)
    if not retrieved:
        retrieved = KNOWLEDGE_BASE[:2]

    lines = ["圖書館規則與系統知識："]
    for item in retrieved:
        lines.append(f"- {item['title']}：{item['content']}")
    return "\n".join(lines), retrieved


# 本地 fallback 回覆，用於沒有 API key 或 API 呼叫失敗時。
def _build_local_reply(message, user=None):
    lowered_message = message.lower()
    responses = []

    if _is_greeting(message):
        responses.append("你好，我可以協助你查詢借書規則、還書規則、目前借閱狀態、歷史借閱紀錄與歸還紀錄。")
        return "\n".join(responses)

    _, retrieved = _build_knowledge_context(message)
    if retrieved:
        responses.append("以下是和你問題最相關的資訊：")
        for item in retrieved:
            responses.append(f"- {item['title']}：{item['content']}")

    if user and _is_return_history_question(message, lowered_message):
        returned_loans = Loan.objects.select_related("book").filter(user=user, returned_at__isnull=False).order_by("-returned_at")
        if returned_loans.exists():
            responses.append(f"{user.name} 已歸還過的書籍如下：")
            for loan in returned_loans[:10]:
                responses.append(f"- 《{loan.book.title}》，借閱日：{loan.borrowed_at.date()}，歸還日：{loan.returned_at.date()}")
        else:
            responses.append(f"{user.name} 目前沒有已歸還的借閱紀錄。")

    elif user and _is_history_question(message, lowered_message):
        all_loans = Loan.objects.select_related("book").filter(user=user).order_by("-borrowed_at")
        if all_loans.exists():
            responses.append(f"{user.name} 曾借閱過的書籍如下：")
            for loan in all_loans[:10]:
                status_text = "已歸還" if loan.returned_at else "尚未歸還"
                responses.append(f"- 《{loan.book.title}》，借閱日：{loan.borrowed_at.date()}，狀態：{status_text}")
        else:
            responses.append(f"{user.name} 目前還沒有任何借閱紀錄。")

    elif user and _is_active_loan_question(message, lowered_message):
        active_loans = Loan.objects.select_related("book").filter(user=user, returned_at__isnull=True)
        if active_loans.exists():
            today = timezone.localdate()
            responses.append(f"{user.name} 目前尚未歸還的書籍如下：")
            for loan in active_loans[:10]:
                overdue_text = "已逾期" if loan.due_date < today else "未逾期"
                responses.append(f"- 《{loan.book.title}》到期日：{loan.due_date}，狀態：{overdue_text}")
        else:
            responses.append(f"{user.name} 目前沒有尚未歸還的書籍。")

    if any(keyword in lowered_message for keyword in ["rag", "llm", "chatbot"]):
        responses.append("目前這是簡化版的 RAG 風格客服，先用知識庫檢索加上借閱資料回覆。若需要，也可以再接真正的 LLM API。")

    if not responses:
        responses.append("我先根據目前系統資料回答你，但這個問題需要更明確一點。你可以改問：借書規則、我目前借了什麼、我借過哪些書、我有還過書嗎。")

    return "\n".join(responses)


# 呼叫 OpenAI Responses API，讓模型根據目前資料生成回覆。
def _call_openai_llm(message, user=None):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.info("Chatbot fallback: OPENAI_API_KEY not set.")
        return None, "not_configured"

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/responses").strip()
    knowledge_context, _ = _build_knowledge_context(message)
    user_context = _build_user_context(user)

    instructions = (
        "你是線上圖書館管理系統的客服助理。"
        "你只能根據提供的圖書館規則與使用者借閱資料回答。"
        "請一律使用繁體中文回答。"
        "如果使用者只是打招呼，請自然地打招呼並簡短介紹你能協助的項目。"
        "如果資料不足，請直接說明目前資料不足，不要自行捏造。"
        "回答要自然、精簡、清楚，優先直接回答使用者問題。"
    )

    prompt = (
        f"{knowledge_context}\n\n"
        f"{user_context}\n\n"
        f"使用者問題：{message}\n\n"
        "請根據以上資料回答使用者。"
    )

    payload = {
        "model": model,
        "instructions": instructions,
        "input": prompt,
        "text": {"verbosity": "medium"},
    }

    request = urllib.request.Request(
        base_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
            output_text = (data.get("output_text") or "").strip()
            if output_text:
                logger.info("Chatbot mode: OpenAI LLM response generated with model '%s'.", model)
                return output_text, "llm_success"
            logger.warning("Chatbot fallback: OpenAI API returned no output_text.")
            return None, "api_no_output"
    except urllib.error.HTTPError as exc:
        logger.warning("Chatbot fallback: OpenAI API HTTPError %s.", exc.code)
        return None, f"api_http_{exc.code}"
    except urllib.error.URLError as exc:
        logger.warning("Chatbot fallback: OpenAI API URLError %s.", exc.reason)
        return None, "api_network_error"
    except (TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Chatbot fallback: OpenAI API exception %s.", exc)
        return None, "api_exception"


# 將模式代碼轉成前端可顯示的文字。
def get_chatbot_mode_label(mode_code):
    labels = {
        "llm_success": "LLM 模式",
        "not_configured": "本地模式（未設定 API）",
        "api_no_output": "本地模式（API 無回覆）",
        "api_http_401": "本地模式（API 金鑰錯誤）",
        "api_http_403": "本地模式（API 權限不足）",
        "api_http_429": "本地模式（API 額度或頻率限制）",
        "api_network_error": "本地模式（API 網路失敗）",
        "api_exception": "本地模式（API 呼叫失敗）",
        "local_only": "本地模式",
    }
    return labels.get(mode_code, "本地模式（API 失敗）")


# 取得預設模式顯示文字。
def get_chatbot_default_mode():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if api_key:
        return "本地模式（等待測試）"
    return "本地模式（未設定 API）"


# 對外主要入口：優先走 LLM API，失敗時退回本地客服。
def build_chatbot_reply(message, user=None):
    message = (message or "").strip()
    if not message:
        return {
            "reply": "請輸入想詢問的內容，例如：借書規則、我的書什麼時候到期、我借過哪些書。",
            "mode_code": "local_only",
            "mode_label": get_chatbot_mode_label("local_only"),
        }

    llm_reply, mode_code = _call_openai_llm(message, user=user)
    if llm_reply:
        return {
            "reply": llm_reply,
            "mode_code": mode_code,
            "mode_label": get_chatbot_mode_label(mode_code),
        }

    logger.info("Chatbot mode: local fallback response generated.")
    return {
        "reply": _build_local_reply(message, user=user),
        "mode_code": mode_code,
        "mode_label": get_chatbot_mode_label(mode_code),
    }

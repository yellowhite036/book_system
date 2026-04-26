from collections import Counter

from django.utils import timezone

from .models import Loan


# 內建的小型知識庫，用來模擬 RAG 檢索式回答。
KNOWLEDGE_BASE = [
    {
        "title": "借書規則",
        "content": "使用者可以借閱目前仍有可借數量的書籍。借書成功後，系統會建立借閱紀錄，並預設給予十四天的借閱期限。",
        "keywords": ["借書", "借閱", "規則", "期限", "borrow"],
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
        keyword_score = sum(2 for keyword in item["keywords"] if keyword.lower() in lowered_message)
        title_score = 3 if item["title"] in message else 0
        total_score = token_score + keyword_score + title_score
        ranked.append((total_score, item))

    ranked.sort(key=lambda row: row[0], reverse=True)
    return [item for score, item in ranked if score > 0][:2]


# 組合 chatbot 回覆內容，包含知識庫與目前使用者的借閱狀態。
def build_chatbot_reply(message, user=None):
    message = (message or "").strip()
    if not message:
        return "請輸入想詢問的內容，例如：借書規則、我的書什麼時候到期、如何判斷是否逾期。"

    responses = []
    retrieved = _retrieve_context(message)
    if retrieved:
        responses.append("以下是和你問題最相關的資訊：")
        for item in retrieved:
            responses.append(f"- {item['title']}：{item['content']}")
    else:
        responses.append("我先根據目前系統資料回答你。")

    loan_keywords = ["我的", "借閱", "借書", "還書", "到期", "逾期", "my", "loan", "due", "overdue", "return"]
    lowered_message = message.lower()
    if user and any(keyword in message or keyword in lowered_message for keyword in loan_keywords):
        active_loans = Loan.objects.select_related("book").filter(user=user, returned_at__isnull=True)
        if active_loans.exists():
            today = timezone.localdate()
            responses.append(f"{user.name} 目前尚未歸還的書籍如下：")
            for loan in active_loans:
                overdue_text = "已逾期" if loan.due_date < today else "未逾期"
                responses.append(f"- 《{loan.book.title}》到期日：{loan.due_date}，狀態：{overdue_text}")
        else:
            responses.append(f"{user.name} 目前沒有尚未歸還的書籍。")

    if any(keyword in lowered_message for keyword in ["rag", "llm", "chatbot"]):
        responses.append("目前這是簡化版的 RAG 風格客服，先用知識庫檢索加上借閱資料回覆。若需要，也可以再接真正的 LLM API。")

    return "\n".join(responses)

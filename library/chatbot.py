from collections import Counter

from django.utils import timezone

from .models import Loan


# A tiny built-in knowledge base used to simulate RAG-style retrieval.
KNOWLEDGE_BASE = [
    {
        "title": "Borrowing policy",
        "content": "Users can borrow available books from the catalog. After borrowing, the system creates a loan record and assigns a due date.",
    },
    {
        "title": "Return policy",
        "content": "When a book is returned, the loan record is marked as returned and the available copy count is increased automatically.",
    },
    {
        "title": "Overdue policy",
        "content": "A loan is overdue when the current date is later than the due date and the book has not been returned yet.",
    },
    {
        "title": "System usage",
        "content": "The web page lets staff and users browse books, borrow, return, and check due dates or overdue status in one place.",
    },
]


# Split a question into simple searchable tokens.
def _tokenize(text):
    normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return [token for token in normalized.split() if token]


# Rank knowledge snippets by token overlap with the user's message.
def _retrieve_context(message):
    query_tokens = Counter(_tokenize(message))
    ranked = []
    for item in KNOWLEDGE_BASE:
        content = f"{item['title']} {item['content']}"
        score = sum((query_tokens & Counter(_tokenize(content))).values())
        ranked.append((score, item))
    ranked.sort(key=lambda row: row[0], reverse=True)
    return [item for score, item in ranked if score > 0][:2]


# Build the chatbot reply from knowledge snippets plus live loan data.
def build_chatbot_reply(message, user=None):
    message = (message or "").strip()
    if not message:
        return "Please enter a question, such as how to borrow a book, how overdue status works, or when a loan is due."

    responses = []
    retrieved = _retrieve_context(message)
    if retrieved:
        responses.append("I found these related library rules:")
        for item in retrieved:
            responses.append(f"- {item['title']}: {item['content']}")
    else:
        responses.append("I will answer based on the current library data.")

    lower_message = message.lower()
    loan_keywords = ["my", "loan", "due", "overdue", "borrowed", "return"]
    # If the message looks loan-related, include the selected user's active loans.
    if user and any(keyword in lower_message for keyword in loan_keywords):
        active_loans = Loan.objects.select_related("book").filter(user=user, returned_at__isnull=True)
        if active_loans.exists():
            today = timezone.localdate()
            responses.append(f"{user.name}'s active loans:")
            for loan in active_loans:
                overdue_text = "overdue" if loan.due_date < today else "not overdue"
                responses.append(f"- {loan.book.title}: due {loan.due_date}, status: {overdue_text}")
        else:
            responses.append(f"{user.name} has no active loans right now.")

    if "rag" in lower_message or "llm" in lower_message or "chatbot" in lower_message:
        responses.append("This demo chatbot uses a simplified RAG-style knowledge lookup. A real LLM can be connected later through an external API.")

    return "\n".join(responses)

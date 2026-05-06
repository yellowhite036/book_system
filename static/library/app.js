// 集中管理前端狀態，方便頁面重新渲染。
const state = {
  currentUser: null,
  books: [],
  loans: [],
  questions: [],
};

// 先取得頁面上會重複使用的 DOM 元素。
const userName = document.querySelector("#userName");
const userSummary = document.querySelector("#userSummary");
const booksContainer = document.querySelector("#booksContainer");
const loansContainer = document.querySelector("#loansContainer");
const chatMessages = document.querySelector("#chatMessages");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");
const chatbotModeTag = document.querySelector("#chatbotModeTag");

const questionsContainer = document.querySelector("#questionsContainer");
const askForm = document.querySelector("#askForm");
const askInput = document.querySelector("#askInput");
const askFeedback = document.querySelector("#askFeedback");
const refreshQuestionsBtn = document.querySelector("#refreshQuestionsBtn");

const csrfMeta = document.querySelector('meta[name="csrf-token"]');

// 從瀏覽器 cookie 取出 Django 的 CSRF token。
function getCookie(name) {
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const cookie of cookies) {
    const trimmed = cookie.trim();
    if (trimmed.startsWith(`${name}=`)) {
      return decodeURIComponent(trimmed.slice(name.length + 1));
    }
  }
  return "";
}

// 優先從頁面 meta 取得 CSRF token，取不到時再退回 cookie。
function getCsrfToken() {
  if (csrfMeta && csrfMeta.content && csrfMeta.content !== "NOTPROVIDED") {
    return csrfMeta.content;
  }
  return getCookie("csrftoken");
}

// 包裝 fetch，統一處理 JSON 與錯誤訊息。
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    ...options,
  });

  if (response.status === 401) {
    window.location.href = "/login/";
    throw new Error("尚未登入。");
  }

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "操作失敗。");
  }
  return response.json();
}

// 將後端日期格式化成台灣常見顯示方式。
function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("zh-TW");
}

// 顯示目前登入者名稱。
function renderCurrentUser() {
  if (!state.currentUser) {
    userName.textContent = "未登入";
    return;
  }
  userName.textContent = `${state.currentUser.name}（${state.currentUser.username}）`;
  renderChatbotMode(state.currentUser.chatbot_mode);
}

// 顯示目前客服是走本地模式還是 LLM 模式。
function renderChatbotMode(mode) {
  if (!chatbotModeTag) return;
  chatbotModeTag.textContent = mode || "本地模式";
}

// 顯示所有書籍，並標示目前是否仍可借閱。
function renderBooks() {
  if (!state.books.length) {
    booksContainer.innerHTML = '<div class="empty-state">目前沒有館藏資料。</div>';
    return;
  }

  booksContainer.innerHTML = state.books
    .map((book) => `
      <article class="book-item">
        <h3>${book.title}</h3>
        <div class="book-meta">
          <span>作者：${book.author}</span>
          <span>分類：${book.category || "未分類"}</span>
          <span>ISBN：${book.isbn}</span>
        </div>
        <p>${book.description || "暫無簡介"}</p>
        <div class="book-actions">
          <span class="status-chip ${book.available_copies > 0 ? "ok" : "danger"}">
            可借數量：${book.available_copies}/${book.total_copies}
          </span>
          <button data-book-id="${book.id}" ${book.available_copies <= 0 ? "disabled" : ""}>借書</button>
        </div>
      </article>
    `)
    .join("");
}

// 顯示目前登入者自己的借閱紀錄與狀態。
function renderLoans() {
  const activeCount = state.loans.filter((loan) => !loan.is_returned).length;
  userSummary.textContent = state.currentUser
    ? `${state.currentUser.name} 目前共有 ${activeCount} 本未歸還書籍。`
    : "正在讀取使用者資料。";

  if (!state.loans.length) {
    loansContainer.innerHTML = '<div class="empty-state">你目前沒有借閱紀錄。</div>';
    return;
  }

  loansContainer.innerHTML = state.loans
    .map((loan) => {
      let statusClass = "ok";
      let statusText = "借閱中";
      if (loan.is_returned) {
        statusClass = "warn";
        statusText = "已歸還";
      } else if (loan.is_overdue) {
        statusClass = "danger";
        statusText = "已逾期";
      }

      return `
        <article class="loan-item">
          <h3>${loan.book_title}</h3>
          <div class="loan-meta">
            <span>借閱日期：${formatDate(loan.borrowed_at)}</span>
            <span>到期日：${formatDate(loan.due_date)}</span>
            ${loan.returned_at ? `<span>歸還日：${formatDate(loan.returned_at)}</span>` : ""}
          </div>
          <div class="book-actions">
            <span class="status-chip ${statusClass}">${statusText}</span>
            <button data-loan-id="${loan.id}" ${loan.is_returned ? "disabled" : ""}>還書</button>
          </div>
        </article>
      `;
    })
    .join("");
}

// 顯示提問列表與管理員回覆。
function renderQuestions() {
  if (!state.questions.length) {
    questionsContainer.innerHTML = '<div class="empty-state">目前沒有提問紀錄。</div>';
    return;
  }

  questionsContainer.innerHTML = state.questions
    .map((q) => `
      <article class="question-item ${q.is_answered ? "answered" : ""}">
        <div class="question-content">
          <span class="q-tag">問</span>
          <p>${q.content}</p>
          <small>${formatDate(q.created_at)}</small>
        </div>
        ${q.answer ? `
          <div class="answer-content">
            <span class="a-tag">答</span>
            <p>${q.answer}</p>
            <small>${formatDate(q.answered_at)}</small>
          </div>
        ` : `
          <div class="answer-content pending">
            <p class="muted-text">等待管理員回覆中...</p>
          </div>
        `}
      </article>
    `)
    .join("");
}

// 在對話區塊加入一則訊息。
function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 從後端載入目前登入者資料。
async function loadCurrentUser() {
  state.currentUser = await apiFetch("/api/me/");
  renderCurrentUser();
}

// 從後端載入書單並重新渲染書籍區塊。
async function loadBooks() {
  state.books = await apiFetch("/api/books/");
  renderBooks();
}

// 從後端載入目前登入者自己的借閱紀錄。
async function loadLoans() {
  state.loans = await apiFetch("/api/loans/");
  renderLoans();
}

// 從後端載入提問紀錄。
async function loadQuestions() {
  state.questions = await apiFetch("/api/questions/");
  renderQuestions();
}

// 平行更新所有主要資料，讓畫面刷新更快。
async function refreshAll() {
  await Promise.all([loadCurrentUser(), loadBooks(), loadLoans(), loadQuestions()]);
}

// 顯示提問區的提示訊息。
function showAskFeedback(text, isError = false) {
  askFeedback.textContent = text;
  askFeedback.className = `feedback-msg ${isError ? "error" : "success"}`;
  setTimeout(() => {
    askFeedback.textContent = "";
    askFeedback.className = "feedback-msg";
  }, 5000);
}

// 針對提問呼叫 API。
async function handleAsk(content) {
  const data = await apiFetch("/api/questions/ask/", {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  showAskFeedback(data.detail);
  await loadQuestions();
}

// 針對選擇的書籍呼叫借書 API。
async function handleBorrow(bookId) {
  const data = await apiFetch("/api/borrow/", {
    method: "POST",
    body: JSON.stringify({
      book_id: bookId,
    }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadBooks(), loadLoans()]);
}

// 針對指定借閱紀錄呼叫還書 API。
async function handleReturn(loanId) {
  const data = await apiFetch("/api/return/", {
    method: "POST",
    body: JSON.stringify({ loan_id: loanId }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadBooks(), loadLoans()]);
}

// 監聽書單區的借書按鈕點擊事件。
booksContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-book-id]");
  if (!button) return;
  try {
    await handleBorrow(button.dataset.bookId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// 監聽借閱區的還書按鈕點擊事件。
loansContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-loan-id]");
  if (!button) return;
  try {
    await handleReturn(button.dataset.loanId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// 提供手動刷新書單與借閱狀態的按鈕。
document.querySelector("#refreshBooksBtn").addEventListener("click", loadBooks);
document.querySelector("#refreshLoansBtn").addEventListener("click", loadLoans);
document.querySelector("#refreshQuestionsBtn").addEventListener("click", loadQuestions);

// 監聽提問表單提交。
askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = askInput.value.trim();
  if (!content) return;

  try {
    await handleAsk(content);
    askInput.value = "";
  } catch (error) {
    showAskFeedback(error.message, true);
  }
});

// 將輸入訊息送到 chatbot，並把回覆顯示在畫面上。
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  chatInput.value = "";

  try {
    const data = await apiFetch("/api/chatbot/", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    renderChatbotMode(data.mode);
    appendMessage("bot", data.reply);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// 頁面開啟時先載入初始資料。
refreshAll().catch((error) => {
  appendMessage("bot", `系統初始化失敗：${error.message}`);
});

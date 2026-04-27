const state = {
  currentUser: null,
  books: [],
  loans: [],
  requests: [],
  adminRequests: [],
};

const userName = document.querySelector("#userName");
const userSummary = document.querySelector("#userSummary");
const userRole = document.querySelector("#userRole");
const booksContainer = document.querySelector("#booksContainer");
const loansContainer = document.querySelector("#loansContainer");
const requestsContainer = document.querySelector("#requestsContainer");
const adminPanel = document.querySelector("#adminPanel");
const adminRequestsContainer = document.querySelector("#adminRequestsContainer");
const chatMessages = document.querySelector("#chatMessages");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");
const chatbotModeTag = document.querySelector("#chatbotModeTag");
const csrfMeta = document.querySelector('meta[name="csrf-token"]');

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

function getCsrfToken() {
  if (csrfMeta && csrfMeta.content && csrfMeta.content !== "NOTPROVIDED") {
    return csrfMeta.content;
  }
  return getCookie("csrftoken");
}

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

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("zh-TW");
}

function renderCurrentUser() {
  if (!state.currentUser) {
    userName.textContent = "未登入";
    return;
  }

  userName.textContent = `${state.currentUser.name}（${state.currentUser.username}）`;
  userRole.textContent = state.currentUser.is_admin ? "目前角色：管理員" : "目前角色：一般使用者";
  userSummary.textContent = `${state.currentUser.name} 目前共有 ${state.loans.filter((loan) => !loan.is_returned).length} 本未歸還書籍。`;
  renderChatbotMode(state.currentUser.chatbot_mode);
  adminPanel.hidden = !state.currentUser.is_admin;
}

function renderChatbotMode(mode) {
  if (!chatbotModeTag) return;
  chatbotModeTag.textContent = mode || "本地模式";
}

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
          <button data-book-id="${book.id}" ${book.available_copies <= 0 ? "disabled" : ""}>送出借書申請</button>
        </div>
      </article>
    `)
    .join("");
}

function renderLoans() {
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
            <button data-loan-id="${loan.id}" ${loan.is_returned ? "disabled" : ""}>送出還書申請</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderRequests() {
  if (!state.requests.length) {
    requestsContainer.innerHTML = '<div class="empty-state">你目前沒有借還書申請。</div>';
    return;
  }

  requestsContainer.innerHTML = state.requests
    .map((item) => {
      const statusTextMap = {
        pending: "待審核",
        approved: "已核准",
        rejected: "已拒絕",
      };
      const statusClassMap = {
        pending: "warn",
        approved: "ok",
        rejected: "danger",
      };
      const requestTypeText = item.request_type === "borrow" ? "借書申請" : "還書申請";

      return `
        <article class="loan-item">
          <h3>${item.book_title}</h3>
          <div class="loan-meta">
            <span>申請類型：${requestTypeText}</span>
            <span>送出時間：${formatDate(item.created_at)}</span>
            ${item.reviewed_at ? `<span>審核時間：${formatDate(item.reviewed_at)}</span>` : ""}
            ${item.reviewed_by_username ? `<span>審核者：${item.reviewed_by_username}</span>` : ""}
          </div>
          <div class="book-actions">
            <span class="status-chip ${statusClassMap[item.status] || "warn"}">${statusTextMap[item.status] || item.status}</span>
            <span>${item.review_note || "等待管理員處理"}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAdminRequests() {
  if (!state.currentUser?.is_admin) {
    adminRequestsContainer.innerHTML = "";
    return;
  }

  if (!state.adminRequests.length) {
    adminRequestsContainer.innerHTML = '<div class="empty-state">目前沒有待審核申請。</div>';
    return;
  }

  adminRequestsContainer.innerHTML = state.adminRequests
    .map((item) => {
      const requestTypeText = item.request_type === "borrow" ? "借書申請" : "還書申請";
      return `
        <article class="loan-item">
          <h3>${item.user_name} - ${item.book_title}</h3>
          <div class="loan-meta">
            <span>申請類型：${requestTypeText}</span>
            <span>送出時間：${formatDate(item.created_at)}</span>
          </div>
          <div class="book-actions">
            <span class="status-chip warn">待審核</span>
            <div>
              <button class="approve-btn" data-request-id="${item.id}">同意</button>
              <button class="reject-btn ghost-btn" data-request-id="${item.id}">拒絕</button>
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function loadCurrentUser() {
  state.currentUser = await apiFetch("/api/me/");
  renderCurrentUser();
}

async function loadBooks() {
  state.books = await apiFetch("/api/books/");
  renderBooks();
}

async function loadLoans() {
  state.loans = await apiFetch("/api/loans/");
  renderLoans();
  if (state.currentUser) {
    userSummary.textContent = `${state.currentUser.name} 目前共有 ${state.loans.filter((loan) => !loan.is_returned).length} 本未歸還書籍。`;
  }
}

async function loadRequests() {
  state.requests = await apiFetch("/api/requests/");
  renderRequests();
}

async function loadAdminRequests() {
  if (!state.currentUser?.is_admin) return;
  state.adminRequests = await apiFetch("/api/admin/requests/");
  renderAdminRequests();
}

async function refreshAll() {
  await loadCurrentUser();
  await Promise.all([loadBooks(), loadLoans(), loadRequests()]);
  if (state.currentUser?.is_admin) {
    await loadAdminRequests();
  }
}

async function handleBorrow(bookId) {
  const data = await apiFetch("/api/borrow/", {
    method: "POST",
    body: JSON.stringify({ book_id: bookId }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadRequests(), loadAdminRequests()]);
}

async function handleReturn(loanId) {
  const data = await apiFetch("/api/return/", {
    method: "POST",
    body: JSON.stringify({ loan_id: loanId }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadRequests(), loadAdminRequests()]);
}

async function handleApproveRequest(requestId) {
  const data = await apiFetch(`/api/admin/requests/${requestId}/approve/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadBooks(), loadLoans(), loadRequests(), loadAdminRequests()]);
}

async function handleRejectRequest(requestId) {
  const data = await apiFetch(`/api/admin/requests/${requestId}/reject/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadRequests(), loadAdminRequests()]);
}

booksContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-book-id]");
  if (!button) return;
  try {
    await handleBorrow(button.dataset.bookId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

loansContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-loan-id]");
  if (!button) return;
  try {
    await handleReturn(button.dataset.loanId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

adminRequestsContainer.addEventListener("click", async (event) => {
  const approveButton = event.target.closest(".approve-btn");
  const rejectButton = event.target.closest(".reject-btn");

  try {
    if (approveButton) {
      await handleApproveRequest(approveButton.dataset.requestId);
    }
    if (rejectButton) {
      await handleRejectRequest(rejectButton.dataset.requestId);
    }
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

document.querySelector("#refreshBooksBtn").addEventListener("click", loadBooks);
document.querySelector("#refreshLoansBtn").addEventListener("click", loadLoans);
document.querySelector("#refreshRequestsBtn").addEventListener("click", loadRequests);
document.querySelector("#refreshAdminRequestsBtn").addEventListener("click", loadAdminRequests);

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

refreshAll().catch((error) => {
  appendMessage("bot", `系統初始化失敗：${error.message}`);
});

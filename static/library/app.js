// Keep the frontend state in one place so the page can re-render easily.
const state = {
  users: [],
  books: [],
  loans: [],
  selectedUserId: null,
};

// Cache the main DOM elements used throughout the page.
const userSelect = document.querySelector("#userSelect");
const userSummary = document.querySelector("#userSummary");
const booksContainer = document.querySelector("#booksContainer");
const loansContainer = document.querySelector("#loansContainer");
const chatMessages = document.querySelector("#chatMessages");
const chatForm = document.querySelector("#chatForm");
const chatInput = document.querySelector("#chatInput");

// Wrap fetch so every API call uses JSON and shared error handling.
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Operation failed.");
  }
  return response.json();
}

// Format backend dates into a Taiwan-friendly display string.
function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("zh-TW");
}

// Render the user dropdown and keep the current selection.
function renderUsers() {
  userSelect.innerHTML = state.users
    .map((user) => `<option value="${user.id}">${user.name}</option>`)
    .join("");
  if (!state.selectedUserId && state.users.length) {
    state.selectedUserId = String(state.users[0].id);
  }
  userSelect.value = state.selectedUserId || "";
}

// Render all books and show whether each one can still be borrowed.
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

// Render the selected user's loan records and status labels.
function renderLoans() {
  const currentUser = state.users.find((user) => String(user.id) === state.selectedUserId);
  const userLoans = state.loans.filter((loan) => String(loan.user) === state.selectedUserId);

  userSummary.textContent = currentUser
    ? `${currentUser.name} 目前共有 ${userLoans.filter((loan) => !loan.is_returned).length} 本未歸還書籍。`
    : "請先選擇使用者。";

  if (!userLoans.length) {
    loansContainer.innerHTML = '<div class="empty-state">這位使用者目前沒有借閱紀錄。</div>';
    return;
  }

  loansContainer.innerHTML = userLoans
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

// Append one chat bubble to the conversation area.
function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Load users from the backend, then update the dropdown.
async function loadUsers() {
  state.users = await apiFetch("/api/users/");
  renderUsers();
}

// Load the book catalog and redraw the book area.
async function loadBooks() {
  state.books = await apiFetch("/api/books/");
  renderBooks();
}

// Load loan records and redraw the selected user's status.
async function loadLoans() {
  state.loans = await apiFetch("/api/loans/");
  renderLoans();
}

// Refresh all page data in parallel for a faster UI update.
async function refreshAll() {
  await Promise.all([loadUsers(), loadBooks(), loadLoans()]);
}

// Call the borrow API for the selected user and chosen book.
async function handleBorrow(bookId) {
  const data = await apiFetch("/api/borrow/", {
    method: "POST",
    body: JSON.stringify({
      user_id: state.selectedUserId,
      book_id: bookId,
    }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadBooks(), loadLoans()]);
}

// Call the return API for the selected loan.
async function handleReturn(loanId) {
  const data = await apiFetch("/api/return/", {
    method: "POST",
    body: JSON.stringify({ loan_id: loanId }),
  });
  appendMessage("bot", data.detail);
  await Promise.all([loadBooks(), loadLoans()]);
}

// Listen for borrow button clicks inside the book list.
booksContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-book-id]");
  if (!button) return;
  try {
    await handleBorrow(button.dataset.bookId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// Listen for return button clicks inside the loan list.
loansContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-loan-id]");
  if (!button) return;
  try {
    await handleReturn(button.dataset.loanId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// When the selected user changes, only the loan area needs to be redrawn.
userSelect.addEventListener("change", (event) => {
  state.selectedUserId = event.target.value;
  renderLoans();
});

// Manual refresh buttons for books and loans.
document.querySelector("#refreshBooksBtn").addEventListener("click", loadBooks);
document.querySelector("#refreshLoansBtn").addEventListener("click", loadLoans);

// Submit the current message to the chatbot and print the response.
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;

  appendMessage("user", message);
  chatInput.value = "";

  try {
    const data = await apiFetch("/api/chatbot/", {
      method: "POST",
      body: JSON.stringify({
        user_id: state.selectedUserId,
        message,
      }),
    });
    appendMessage("bot", data.reply);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

// Load the initial dashboard data when the page opens.
refreshAll().catch((error) => {
  appendMessage("bot", `系統初始化失敗：${error.message}`);
});

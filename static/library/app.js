// =============================================================================
// 全域狀態
// 將所有畫面需要的資料集中在一個物件，方便追蹤與重新渲染。
// 任何資料變動都應先更新這裡，再呼叫對應的 render 函式。
// =============================================================================
const state = {
  users: [],           // 所有使用者清單，來自 GET /api/users/
  books: [],           // 所有館藏書籍，來自 GET /api/books/
  loans: [],           // 所有借閱紀錄，來自 GET /api/loans/
  selectedUserId: null, // 目前在下拉選單中選中的使用者 ID（字串型別）
};

// =============================================================================
// DOM 快取
// 在頁面初始化時一次性取得常用元素，避免在每次渲染時重複查詢 DOM。
// =============================================================================
const userSelect      = document.querySelector("#userSelect");      // 使用者下拉選單
const userSummary     = document.querySelector("#userSummary");     // 使用者借閱摘要文字
const booksContainer  = document.querySelector("#booksContainer");  // 書籍列表容器
const loansContainer  = document.querySelector("#loansContainer");  // 借閱紀錄容器
const chatMessages    = document.querySelector("#chatMessages");    // 聊天訊息顯示區
const chatForm        = document.querySelector("#chatForm");        // 聊天輸入表單
const chatInput       = document.querySelector("#chatInput");       // 聊天文字輸入框

// =============================================================================
// 工具函式
// =============================================================================

/**
 * 統一封裝 fetch，讓所有 API 呼叫共用相同的 headers 與錯誤處理。
 *
 * - 自動帶入 Content-Type: application/json
 * - 若 HTTP 狀態碼非 2xx，會嘗試解析後端回傳的 `detail` 欄位作為錯誤訊息
 * - 成功時直接回傳解析好的 JSON 物件
 *
 * @param {string} url - API 路徑，例如 "/api/books/"
 * @param {RequestInit} options - 可選的 fetch 選項，例如 method、body
 * @returns {Promise<any>} 後端回傳的 JSON 資料
 */
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
    },
    ...options,
  });

  // 非成功狀態碼時，取出後端錯誤訊息並拋出例外
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Operation failed.");
  }

  return response.json();
}

/**
 * 將後端回傳的 ISO 日期字串轉換成台灣慣用的顯示格式。
 * 例如："2024-06-01T00:00:00Z" → "2024/6/1"
 *
 * @param {string} dateString - ISO 格式的日期字串
 * @returns {string} 本地化後的日期字串
 */
function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("zh-TW");
}

// =============================================================================
// 渲染函式
// 每個 render 函式只負責把 state 中的資料轉成 HTML，不做任何 API 呼叫。
// =============================================================================

/**
 * 渲染使用者下拉選單。
 * - 若 state.selectedUserId 尚未設定，自動選取第一位使用者
 * - 重新渲染後維持原本的選取狀態，避免切換時跳回第一筆
 */
function renderUsers() {
  userSelect.innerHTML = state.users
    .map((user) => `<option value="${user.id}">${user.name}</option>`)
    .join("");

  // 初次載入時自動選取第一位使用者
  if (!state.selectedUserId && state.users.length) {
    state.selectedUserId = String(state.users[0].id);
  }

  userSelect.value = state.selectedUserId || "";
}

/**
 * 渲染書籍館藏列表。
 * - 若館藏為空，顯示提示訊息
 * - 依 available_copies 顯示可借數量，並在庫存為 0 時將借書按鈕設為 disabled
 * - 每本書以 data-book-id 屬性記錄 ID，供事件委派使用
 */
function renderBooks() {
  // 館藏為空時顯示提示
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
          <!-- 可借數量為 0 時顯示紅色警示，否則顯示綠色 -->
          <span class="status-chip ${book.available_copies > 0 ? "ok" : "danger"}">
            可借數量：${book.available_copies}/${book.total_copies}
          </span>
          <!-- 庫存為 0 時按鈕自動停用，防止多借 -->
          <button data-book-id="${book.id}" ${book.available_copies <= 0 ? "disabled" : ""}>借書</button>
        </div>
      </article>
    `)
    .join("");
}

/**
 * 渲染目前選中使用者的借閱紀錄。
 * - 在 userSummary 顯示未歸還書籍數量
 * - 依 is_returned / is_overdue 顯示三種狀態：借閱中、已歸還、已逾期
 * - 已歸還的借閱紀錄，還書按鈕設為 disabled
 * - 每筆借閱以 data-loan-id 屬性記錄 ID，供事件委派使用
 */
function renderLoans() {
  // 找出目前選中的使用者物件，以及其對應的借閱紀錄
  const currentUser = state.users.find((user) => String(user.id) === state.selectedUserId);
  const userLoans   = state.loans.filter((loan) => String(loan.user) === state.selectedUserId);

  // 更新借閱摘要：顯示使用者姓名與未歸還數量
  userSummary.textContent = currentUser
    ? `${currentUser.name} 目前共有 ${userLoans.filter((loan) => !loan.is_returned).length} 本未歸還書籍。`
    : "請先選擇使用者。";

  // 若無借閱紀錄，顯示提示訊息
  if (!userLoans.length) {
    loansContainer.innerHTML = '<div class="empty-state">這位使用者目前沒有借閱紀錄。</div>';
    return;
  }

  loansContainer.innerHTML = userLoans
    .map((loan) => {
      // 預設為「借閱中」（綠色）
      let statusClass = "ok";
      let statusText  = "借閱中";

      // 已歸還優先判斷（黃色警示）
      if (loan.is_returned) {
        statusClass = "warn";
        statusText  = "已歸還";
      // 未歸還但已超過到期日（紅色警示）
      } else if (loan.is_overdue) {
        statusClass = "danger";
        statusText  = "已逾期";
      }

      return `
        <article class="loan-item">
          <h3>${loan.book_title}</h3>
          <div class="loan-meta">
            <span>借閱日期：${formatDate(loan.borrowed_at)}</span>
            <span>到期日：${formatDate(loan.due_date)}</span>
            <!-- 僅已歸還的紀錄才會有 returned_at 欄位 -->
            ${loan.returned_at ? `<span>歸還日：${formatDate(loan.returned_at)}</span>` : ""}
          </div>
          <div class="book-actions">
            <span class="status-chip ${statusClass}">${statusText}</span>
            <!-- 已歸還的紀錄不可再次還書 -->
            <button data-loan-id="${loan.id}" ${loan.is_returned ? "disabled" : ""}>還書</button>
          </div>
        </article>
      `;
    })
    .join("");
}

/**
 * 在聊天區域新增一則訊息泡泡。
 * - role 為 "user" 時靠右顯示，"bot" 時靠左顯示（由 CSS 控制）
 * - 新增後自動捲動到最底部，確保最新訊息可見
 *
 * @param {"user"|"bot"} role - 訊息來源角色
 * @param {string} text - 要顯示的訊息內容
 */
function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  // 自動捲到最新訊息
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// =============================================================================
// 資料載入函式
// 每個 load 函式負責打一支 API、更新對應的 state，並呼叫 render。
// =============================================================================

/** 從後端取得使用者清單，並更新下拉選單。 */
async function loadUsers() {
  state.users = await apiFetch("/api/users/");
  renderUsers();
}

/** 從後端取得書籍館藏，並重繪書籍列表。 */
async function loadBooks() {
  state.books = await apiFetch("/api/books/");
  renderBooks();
}

/**
 * 從後端取得所有借閱紀錄，並重繪目前使用者的借閱狀態。
 * 注意：後端回傳的是全部使用者的紀錄，前端在 renderLoans 中再過濾。
 */
async function loadLoans() {
  state.loans = await apiFetch("/api/loans/");
  renderLoans();
}

/**
 * 並行載入所有資料，縮短頁面初始化等待時間。
 * 使用 Promise.all 讓三支 API 同時發出，而非依序等待。
 */
async function refreshAll() {
  await Promise.all([loadUsers(), loadBooks(), loadLoans()]);
}

// =============================================================================
// 業務邏輯：借書 / 還書
// =============================================================================

/**
 * 對後端送出借書請求，並在聊天框顯示結果。
 * 借書成功或失敗後，同步重新整理書籍庫存與借閱紀錄。
 *
 * @param {string|number} bookId - 要借的書籍 ID
 */
async function handleBorrow(bookId) {
  const data = await apiFetch("/api/borrow/", {
    method: "POST",
    body: JSON.stringify({
      user_id: state.selectedUserId,
      book_id: bookId,
    }),
  });
  // 在聊天框顯示後端回傳的操作結果訊息
  appendMessage("bot", data.detail);
  // 借書後同步更新書籍可借數量與使用者借閱紀錄
  await Promise.all([loadBooks(), loadLoans()]);
}

/**
 * 對後端送出還書請求，並在聊天框顯示結果。
 * 還書成功後，同步重新整理書籍庫存與借閱紀錄。
 *
 * @param {string|number} loanId - 要歸還的借閱紀錄 ID
 */
async function handleReturn(loanId) {
  const data = await apiFetch("/api/return/", {
    method: "POST",
    body: JSON.stringify({ loan_id: loanId }),
  });
  appendMessage("bot", data.detail);
  // 還書後同步更新書籍可借數量與使用者借閱紀錄
  await Promise.all([loadBooks(), loadLoans()]);
}

// =============================================================================
// 事件監聽
// 使用事件委派（event delegation）處理動態產生的按鈕，
// 避免每次重新渲染都要重新綁定事件。
// =============================================================================

/**
 * 監聽書籍列表區域的點擊事件。
 * 透過 closest() 找到帶有 data-book-id 的按鈕，再呼叫借書邏輯。
 * 若發生錯誤（例如後端拒絕借書），將錯誤訊息顯示在聊天框。
 */
booksContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-book-id]");
  if (!button) return; // 點到非借書按鈕的區域則忽略
  try {
    await handleBorrow(button.dataset.bookId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

/**
 * 監聽借閱紀錄區域的點擊事件。
 * 透過 closest() 找到帶有 data-loan-id 的按鈕，再呼叫還書邏輯。
 * 若發生錯誤，將錯誤訊息顯示在聊天框。
 */
loansContainer.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-loan-id]");
  if (!button) return; // 點到非還書按鈕的區域則忽略
  try {
    await handleReturn(button.dataset.loanId);
  } catch (error) {
    appendMessage("bot", error.message);
  }
});

/**
 * 監聽使用者下拉選單的變更事件。
 * 切換使用者時只需重繪借閱紀錄，不需重新打 API。
 */
userSelect.addEventListener("change", (event) => {
  state.selectedUserId = event.target.value;
  renderLoans();
});

// 手動重新整理按鈕：只重新載入對應區塊的資料
document.querySelector("#refreshBooksBtn").addEventListener("click", loadBooks);
document.querySelector("#refreshLoansBtn").addEventListener("click", loadLoans);

/**
 * 監聽聊天表單的送出事件。
 * 1. 取得輸入文字，若為空則忽略
 * 2. 在對話框顯示使用者訊息
 * 3. 清空輸入框
 * 4. 呼叫 POST /api/chatbot/，帶入目前使用者 ID 與訊息內容
 * 5. 將機器人回覆顯示在對話框；若失敗則顯示錯誤訊息
 */
chatForm.addEventListener("submit", async (event) => {
  event.preventDefault(); // 阻止表單預設的頁面跳轉行為

  const message = chatInput.value.trim();
  if (!message) return; // 空訊息不送出

  appendMessage("user", message);
  chatInput.value = ""; // 送出後立即清空輸入框

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

// =============================================================================
// 頁面初始化
// 頁面載入時立即取得所有資料。若初始化失敗，在聊天框顯示錯誤提示。
// =============================================================================
refreshAll().catch((error) => {
  appendMessage("bot", `系統初始化失敗：${error.message}`);
});
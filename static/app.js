const el = (id) => document.getElementById(id);

const messages = el("messages");
const form = el("form");
const input = el("input");
const sendBtn = el("send");
const statusEl = el("status");

const sessionId = "s-" + Math.random().toString(36).slice(2, 10);

let busy = false;

const BOT_AVATAR = '<span class="bot-emoji">🏠</span>';

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */

function scrollToEnd() {
  messages.scrollTop = messages.scrollHeight;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  statusEl.textContent = value ? "Thinking…" : "Ready";
  statusEl.className = "status";
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { detail: text };
  }

  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`);
  }
  return data;
}

/* ------------------------------------------------------------------ */
/* rendering                                                           */
/* ------------------------------------------------------------------ */

function addMessage(role, text) {
  const welcome = messages.querySelector(".welcome");
  if (welcome) welcome.remove();

  const wrapper = document.createElement("div");
  wrapper.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  if (role === "bot") {
    avatar.classList.add("bot-avatar");
    avatar.innerHTML = BOT_AVATAR;
  } else {
    avatar.textContent = "🧑";
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrapper.append(avatar, bubble);
  messages.appendChild(wrapper);
  scrollToEnd();
}

function showTyping() {
  const wrapper = document.createElement("div");
  wrapper.className = "msg bot";
  wrapper.id = "typing";
  wrapper.innerHTML =
    `<div class="avatar bot-avatar">${BOT_AVATAR}</div>` +
    '<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  messages.appendChild(wrapper);
  scrollToEnd();
}

function removeTyping() {
  el("typing")?.remove();
}

/* ------------------------------------------------------------------ */
/* actions                                                             */
/* ------------------------------------------------------------------ */

async function sendText() {
  const text = input.value.trim();
  if (!text || busy) return;

  input.value = "";
  input.style.height = "auto";
  addMessage("user", text);
  showTyping();
  setBusy(true);

  try {
    const data = await post("/api/chat", { message: text, session_id: sessionId });
    removeTyping();
    addMessage("bot", data.answer);
  } catch (error) {
    removeTyping();
    addMessage("bot error", `⚠️ ${error.message}`);
  } finally {
    setBusy(false);
    input.focus();
  }
}

/* ------------------------------------------------------------------ */
/* events                                                              */
/* ------------------------------------------------------------------ */

form.addEventListener("submit", (e) => {
  e.preventDefault();
  sendText();
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendText();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

messages.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    input.value = chip.dataset.prompt;
    input.focus();
  })
);

el("newChat").addEventListener("click", () => location.reload());

/* ------------------------------------------------------------------ */
/* startup                                                             */
/* ------------------------------------------------------------------ */

fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    statusEl.textContent = `Ready · ${data.cities} cities in ${data.database}`;
    statusEl.classList.add("ok");
  })
  .catch(() => {
    statusEl.textContent = "Server unreachable";
    statusEl.classList.add("err");
  });

input.focus();

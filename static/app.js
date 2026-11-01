const el = (id) => document.getElementById(id);

const messages = el("messages");
const form = el("form");
const input = el("input");
const sendBtn = el("send");
const statusEl = el("status");
const imageInput = el("imageInput");
const preview = el("preview");
const previewImg = el("previewImg");
const clearImageBtn = el("clearImage");
const micBtn = el("mic");
const recorderBar = el("recorder");
const recTime = el("recTime");
const cancelRec = el("cancelRec");

const sessionId = "s-" + Math.random().toString(36).slice(2, 10);

let selectedImage = null;
let mediaRecorder = null;
let audioChunks = [];
let recStart = 0;
let recTimer = null;
let busy = false;

/* ------------------------------------------------------------------ */
/* helpers                                                             */
/* ------------------------------------------------------------------ */

function scrollToEnd() {
  messages.scrollTop = messages.scrollHeight;
}

const BOT_AVATAR = '<span class="bot-emoji">🏠</span>';

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function setBusy(value) {
  busy = value;
  sendBtn.disabled = value;
  input.disabled = false;
  statusEl.textContent = value ? "Thinking…" : "Ready";
  statusEl.className = "status";
}

async function post(url, body, isForm = false) {
  const response = await fetch(url, {
    method: "POST",
    headers: isForm ? undefined : { "Content-Type": "application/json" },
    body: isForm ? body : JSON.stringify(body),
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

function addMessage(role, text, extra, keepWelcome) {
  if (!keepWelcome) {
    const welcome = messages.querySelector(".welcome");
    if (welcome) welcome.remove();
  }

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

  if (extra) {
    if (extra.imageUrl) {
      const img = document.createElement("img");
      img.className = "attached";
      img.src = extra.imageUrl;
      bubble.appendChild(img);
    }
    if (extra.hasAudio) {
      const tag = document.createElement("div");
      tag.className = "audio-tag";
      tag.textContent = "🎤 Voice message";
      bubble.appendChild(tag);
    }
    if (extra.transcript) {
      const t = document.createElement("div");
      t.className = "transcript";
      t.textContent = extra.transcript;
      bubble.appendChild(t);
    }
  }

  const content = document.createElement("div");
  content.textContent = text;
  bubble.appendChild(content);

  wrapper.append(avatar, bubble);
  messages.appendChild(wrapper);
  scrollToEnd();
  return wrapper;
}

function showTyping() {
  const wrapper = document.createElement("div");
  wrapper.className = "msg bot";
  wrapper.id = "typing";
  wrapper.innerHTML = `<div class="avatar bot-avatar">${BOT_AVATAR}</div>` +
    '<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
  messages.appendChild(wrapper);
  scrollToEnd();
  return wrapper;
}

function removeTyping() {
  el("typing")?.remove();
}

function showError(text) {
  addMessage("bot error", `⚠️ ${text}`);
}

function showBanner(text) {
  const banner = document.createElement("div");
  banner.className = "banner";
  banner.textContent = text;
  messages.insertBefore(banner, messages.firstChild);
  scrollToEnd();
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
  const typing = showTyping();
  setBusy(true);

  try {
    const data = await post("/api/chat", { message: text, session_id: sessionId });
    removeTyping();
    addMessage("bot", data.answer);
  } catch (error) {
    removeTyping();
    showError(error.message);
  } finally {
    setBusy(false);
    input.focus();
  }
}

async function sendImage() {
  if (!selectedImage || busy) return;

  const file = selectedImage;
  clearSelectedImage();
  addMessage("user", "", { imageUrl: URL.createObjectURL(file) });
  const typing = showTyping();
  setBusy(true);

  const payload = new FormData();
  payload.append("image", file);
  payload.append("message", input.value.trim() || "Describe this image in detail.");
  payload.append("session_id", sessionId);
  input.value = "";

  try {
    const data = await post("/api/chat/image", payload, true);
    removeTyping();
    addMessage("bot", data.answer);
  } catch (error) {
    removeTyping();
    showError(error.message);
  } finally {
    setBusy(false);
    input.focus();
  }
}

async function sendAudio(blob) {
  const typing = showTyping();
  setBusy(true);

  const ext = (blob.type.split("/")[1] || "webm").split(";")[0];
  const payload = new FormData();
  payload.append("audio", new File([blob], `voice.${ext}`, { type: blob.type }));
  payload.append("message", input.value.trim());
  payload.append("session_id", sessionId);
  input.value = "";

  try {
    const data = await post("/api/chat/audio", payload, true);
    removeTyping();
    addMessage("bot", data.answer, { hasAudio: true, transcript: data.transcript });
  } catch (error) {
    removeTyping();
    showError(error.message);
  } finally {
    setBusy(false);
    input.focus();
  }
}

/* ------------------------------------------------------------------ */
/* image attachment                                                    */
/* ------------------------------------------------------------------ */

function selectImage(file) {
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    showError("That file is not an image.");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError("Image is too large. Maximum size is 10 MB.");
    return;
  }
  selectedImage = file;
  previewImg.src = URL.createObjectURL(file);
  preview.classList.remove("hidden");
}

function clearSelectedImage() {
  selectedImage = null;
  imageInput.value = "";
  preview.classList.add("hidden");
  previewImg.removeAttribute("src");
}

/* ------------------------------------------------------------------ */
/* voice recording                                                     */
/* ------------------------------------------------------------------ */

function stopTimers() {
  clearInterval(recTimer);
  recTimer = null;
}

async function startRecording() {
  if (busy) return;

  if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
    showError("Voice recording is not supported in this browser. Try Chrome or Edge.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => e.data.size && audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
      audioChunks = [];
      resetRecorderUI();
      if (blob.size > 0) await sendAudio(blob);
    };

    mediaRecorder.start();
    recStart = Date.now();
    recTimer = setInterval(() => {
      recTime.textContent = formatTime((Date.now() - recStart) / 1000);
    }, 250);

    micBtn.classList.add("recording");
    recorderBar.classList.remove("hidden");
    recTime.textContent = "0:00";
  } catch {
    showError("Microphone access was denied. Please allow microphone permission.");
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") mediaRecorder.stop();
}

function cancelRecording() {
  if (mediaRecorder) {
    mediaRecorder.onstop = null;
    if (mediaRecorder.state !== "inactive") mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
  }
  audioChunks = [];
  resetRecorderUI();
}

function resetRecorderUI() {
  stopTimers();
  mediaRecorder = null;
  micBtn.classList.remove("recording");
  recorderBar.classList.add("hidden");
}

/* ------------------------------------------------------------------ */
/* events                                                              */
/* ------------------------------------------------------------------ */

form.addEventListener("submit", (e) => {
  e.preventDefault();
  if (selectedImage) sendImage();
  else sendText();
});

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (selectedImage) sendImage();
    else sendText();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});

imageInput.addEventListener("change", () => selectImage(imageInput.files[0]));
clearImageBtn.addEventListener("click", clearSelectedImage);

micBtn.addEventListener("click", () => {
  if (mediaRecorder) stopRecording();
  else startRecording();
});
cancelRec.addEventListener("click", cancelRecording);

messages.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    input.value = chip.dataset.prompt;
    input.focus();
  })
);

el("newChat").addEventListener("click", async () => {
  messages.innerHTML = "";
  clearSelectedImage();
  input.value = "";
  await post("/api/reset", new URLSearchParams({ session_id: sessionId }))
    .catch(() => {});
  location.reload();
});

document.addEventListener("paste", (e) => {
  const file = [...(e.clipboardData?.files || [])][0];
  if (file?.type.startsWith("image/")) selectImage(file);
});

/* ------------------------------------------------------------------ */
/* startup                                                             */
/* ------------------------------------------------------------------ */

fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    if (!data.api_key_configured) {
      statusEl.textContent = "GROQ_API_KEY missing — see .env";
      statusEl.classList.add("err");
      return;
    }
    if (data.quota && data.quota.ok === false) {
      statusEl.textContent = "Groq unavailable";
      statusEl.classList.add("err");
      statusEl.title = data.quota.message || "";
      showBanner(data.quota.message || "EstateBot cannot reach Groq right now.");
      return;
    }
    statusEl.textContent = "Ready";
    statusEl.classList.add("ok");
  })
  .catch(() => {
    statusEl.textContent = "Server unreachable";
    statusEl.classList.add("err");
  });

input.focus();
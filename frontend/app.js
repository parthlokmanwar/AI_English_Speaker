/* ═══════════════════════════════════════════════════════════
   FluentRound — app.js
   Author: Antigravity AI
   Description: Full client-side logic for the FluentRound app.
═══════════════════════════════════════════════════════════ */

// ── Backend URL — CHANGE THIS AFTER DEPLOYING TO RENDER ──────────────────────
const API_BASE_URL = "http://localhost:8000"; // Change to your Render URL after deployment

// ─────────────────────────────────────────────────────────────────────────────
//  STATE
// ─────────────────────────────────────────────────────────────────────────────
let conversationHistory    = []; // [{role, content}, ...]
let sessionScores          = []; // all non-zero integer scores
let sessionVocabSuggestions = []; // all better_words strings
let sessionGrammarErrors   = []; // all grammar_error strings
let currentMode            = "";
let isRecording            = false;
let isMayaSpeaking         = false;
let recognition            = null;
let totalMessages          = 0;   // total user + maya exchanges counted

// ─────────────────────────────────────────────────────────────────────────────
//  DOM REFERENCES
// ─────────────────────────────────────────────────────────────────────────────
const modeScreen        = document.getElementById("mode-screen");
const chatScreen        = document.getElementById("chat-screen");
const chatArea          = document.getElementById("chat-area");
const messageInput      = document.getElementById("message-input");
const micBtn            = document.getElementById("mic-btn");
const sendBtn           = document.getElementById("send-btn");
const modeBadge         = document.getElementById("mode-badge");
const endSessionBtn     = document.getElementById("end-session-btn");
const feedbackContent   = document.getElementById("feedback-content");
const feedbackDrawerContent = document.getElementById("feedback-drawer-content");
const browserWarning    = document.getElementById("browser-warning");

// Mobile drawer
const feedbackFab       = document.getElementById("feedback-fab");
const feedbackDrawer    = document.getElementById("feedback-drawer");
const drawerOverlay     = document.getElementById("drawer-overlay");
const closeDrawerBtn    = document.getElementById("close-drawer-btn");

// Modal
const summaryModal      = document.getElementById("summary-modal");
const closeModalBtn     = document.getElementById("close-modal-btn");
const newSessionBtn     = document.getElementById("new-session-btn");

// Mode cards
const modeCards         = document.querySelectorAll(".mode-card");

// ─────────────────────────────────────────────────────────────────────────────
//  TOAST NOTIFICATIONS
// ─────────────────────────────────────────────────────────────────────────────
function showToast(message, type = "red") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  const icon = type === "red" ? "🚫" : type === "yellow" ? "⚠️" : "✅";
  toast.innerHTML = `<span aria-hidden="true">${icon}</span> ${message}`;
  container.appendChild(toast);

  // Auto-dismiss after 4 seconds
  setTimeout(() => {
    toast.classList.add("fade-out");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  }, 4000);
}

// ─────────────────────────────────────────────────────────────────────────────
//  UTILITY — Scroll chat to bottom
// ─────────────────────────────────────────────────────────────────────────────
function scrollToBottom() {
  chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: "smooth" });
}

// ─────────────────────────────────────────────────────────────────────────────
//  UTILITY — Set controls enabled/disabled
// ─────────────────────────────────────────────────────────────────────────────
function setControlsEnabled(enabled) {
  sendBtn.disabled  = !enabled;
  micBtn.disabled   = !enabled || isMayaSpeaking;
  messageInput.disabled = !enabled;
}

// ─────────────────────────────────────────────────────────────────────────────
//  CHAT BUBBLES
// ─────────────────────────────────────────────────────────────────────────────
function addBubble(text, sender) {
  const row = document.createElement("div");
  row.className = `message-row message-row--${sender}`;

  if (sender === "maya") {
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "🤖";
    row.appendChild(avatar);
  }

  const bubble = document.createElement("div");
  bubble.className = `message-bubble message-bubble--${sender}`;
  bubble.textContent = text;
  row.appendChild(bubble);

  chatArea.appendChild(row);
  scrollToBottom();
  return row;
}

// ─────────────────────────────────────────────────────────────────────────────
//  TYPING INDICATOR
// ─────────────────────────────────────────────────────────────────────────────
let typingRow = null;

function showTypingIndicator() {
  typingRow = document.createElement("div");
  typingRow.className = "typing-indicator";
  typingRow.setAttribute("aria-label", "Maya is typing");
  typingRow.innerHTML = `
    <div class="message-avatar" aria-hidden="true">🤖</div>
    <div class="typing-bubble" aria-hidden="true">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatArea.appendChild(typingRow);
  scrollToBottom();
}

function hideTypingIndicator() {
  if (typingRow) {
    typingRow.remove();
    typingRow = null;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  FEEDBACK PANEL
// ─────────────────────────────────────────────────────────────────────────────
function buildFeedbackHTML(feedback) {
  const { grammar_errors = [], better_words = [], filler_words = [], fluency_tip = "", score = 0 } = feedback;

  // Score class
  let scoreClass = "score-low";
  if (score >= 7) scoreClass = "score-high";
  else if (score >= 5) scoreClass = "score-mid";

  const scoreWidth = `${Math.round((score / 10) * 100)}%`;

  // Grammar Errors
  const grammarHTML = grammar_errors.length > 0
    ? `<ul class="feedback-section__list">${grammar_errors.map(e =>
        `<li class="feedback-section__item feedback-section__item--grammar">${escapeHTML(e)}</li>`
      ).join("")}</ul>`
    : `<p class="feedback-all-good">✅ All good!</p>`;

  // Better Words
  const vocabHTML = better_words.length > 0
    ? `<ul class="feedback-section__list">${better_words.map(w =>
        `<li class="feedback-section__item feedback-section__item--vocab">${escapeHTML(w)}</li>`
      ).join("")}</ul>`
    : `<p class="feedback-all-good">✅ All good!</p>`;

  // Filler Words
  const fillerHTML = filler_words.length > 0
    ? `<div class="filler-tags">${filler_words.map(f =>
        `<span class="filler-tag">${escapeHTML(f)}</span>`
      ).join("")}</div>`
    : `<p class="feedback-all-good">✅ None detected!</p>`;

  // Fluency Tip
  const tipHTML = fluency_tip
    ? `<div class="fluency-tip-box">${escapeHTML(fluency_tip)}</div>`
    : `<p class="feedback-all-good">Keep going!</p>`;

  return `
    <div class="score-section">
      <div class="score-label">⭐ Fluency Score</div>
      <div class="score-display">
        <span class="score-number ${scoreClass}">${score}</span>
        <span class="score-denom">/ 10</span>
      </div>
      <div class="score-bar-track">
        <div class="score-bar-fill ${scoreClass}" style="--score-width: ${scoreWidth}"></div>
      </div>
    </div>

    <div class="feedback-section">
      <div class="feedback-section__title">🔴 Grammar Errors</div>
      ${grammarHTML}
    </div>

    <div class="feedback-section">
      <div class="feedback-section__title">🔵 Better Words</div>
      ${vocabHTML}
    </div>

    <div class="feedback-section">
      <div class="feedback-section__title">🟠 Filler Words</div>
      ${fillerHTML}
    </div>

    <div class="feedback-section">
      <div class="feedback-section__title">🟢 Fluency Tip</div>
      ${tipHTML}
    </div>
  `;
}

function updateFeedbackPanels(feedback) {
  const html = buildFeedbackHTML(feedback);
  feedbackContent.innerHTML = html;
  feedbackDrawerContent.innerHTML = html;
}

// ─────────────────────────────────────────────────────────────────────────────
//  ESCAPE HTML
// ─────────────────────────────────────────────────────────────────────────────
function escapeHTML(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ─────────────────────────────────────────────────────────────────────────────
//  TTS PLAYBACK
// ─────────────────────────────────────────────────────────────────────────────
async function playTTS(text) {
  isMayaSpeaking = true;
  micBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE_URL}/tts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      console.error("TTS request failed:", response.status);
      isMayaSpeaking = false;
      micBtn.disabled = false;
      return;
    }

    const audioBlob = await response.blob();
    const audioUrl  = URL.createObjectURL(audioBlob);
    const audio     = new Audio(audioUrl);

    audio.onended = () => {
      isMayaSpeaking = false;
      URL.revokeObjectURL(audioUrl);
      micBtn.disabled = false;
    };

    audio.onerror = () => {
      isMayaSpeaking = false;
      URL.revokeObjectURL(audioUrl);
      micBtn.disabled = false;
      console.error("Audio playback error.");
    };

    await audio.play();
  } catch (err) {
    isMayaSpeaking = false;
    micBtn.disabled = false;
    console.error("TTS failed:", err);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  FETCH GREETING AND START SESSION
// ─────────────────────────────────────────────────────────────────────────────
async function startSession(mode) {
  try {
    const res = await fetch(`${API_BASE_URL}/greeting?mode=${mode}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const greetingText = data.greeting || "Hi! I'm Maya. Let's practice English together!";

    addBubble(greetingText, "maya");
    conversationHistory.push({ role: "assistant", content: greetingText });
    totalMessages++;

    // Speak greeting
    await playTTS(greetingText);
  } catch (err) {
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      showToast("Cannot connect to server. Is the backend running?", "red");
    } else {
      console.error("Greeting fetch failed:", err);
      const fallback = "Hi! I'm Maya, your English practice partner. How can I help you today?";
      addBubble(fallback, "maya");
      conversationHistory.push({ role: "assistant", content: fallback });
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SEND MESSAGE
// ─────────────────────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text) return;

  messageInput.value = "";
  addBubble(text, "user");
  conversationHistory.push({ role: "user", content: text });
  totalMessages++;

  showTypingIndicator();
  setControlsEnabled(false);

  try {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory.slice(0, -1), // history before current message
        mode: currentMode,
      }),
    });

    hideTypingIndicator();

    // Handle specific error codes
    if (res.status === 429) {
      showToast("Rate limit hit. Please wait 30 seconds before sending again.", "yellow");
      setControlsEnabled(true);
      return;
    }

    if (!res.ok) {
      showToast("Something went wrong on the server. Try again.", "red");
      setControlsEnabled(true);
      return;
    }

    const data = await res.json();
    const reply    = data.reply    || "Sorry, I didn't catch that. Could you try again?";
    const feedback = data.feedback || {};

    // Add Maya's reply to chat
    addBubble(reply, "maya");
    conversationHistory.push({ role: "assistant", content: reply });
    totalMessages++;

    // Update feedback panels
    updateFeedbackPanels(feedback);

    // Collect session data
    if (feedback.score && feedback.score > 0) {
      sessionScores.push(feedback.score);
    }
    if (Array.isArray(feedback.better_words)) {
      sessionVocabSuggestions.push(...feedback.better_words);
    }
    if (Array.isArray(feedback.grammar_errors)) {
      sessionGrammarErrors.push(...feedback.grammar_errors);
    }

    // Play TTS — controls re-enabled after audio finishes
    await playTTS(reply);
    setControlsEnabled(true);

  } catch (err) {
    hideTypingIndicator();
    if (err.name === "TypeError" && err.message.includes("fetch")) {
      showToast("Cannot connect to server. Is the backend running?", "red");
    } else {
      showToast("Something went wrong on the server. Try again.", "red");
      console.error("Chat error:", err);
    }
    setControlsEnabled(true);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  SPEECH RECOGNITION SETUP
// ─────────────────────────────────────────────────────────────────────────────
function setupSpeechRecognition() {
  if (!("SpeechRecognition" in window) && !("webkitSpeechRecognition" in window)) {
    // Browser doesn't support STT
    micBtn.style.display = "none";
    browserWarning.classList.remove("hidden");
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous      = false;
  recognition.interimResults  = true;
  recognition.lang            = "en-IN";

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map(r => r[0].transcript)
      .join("");
    messageInput.value = transcript;
  };

  recognition.onend = () => {
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.setAttribute("aria-label", "Start voice recording");
    // Auto-send if we captured something
    if (messageInput.value.trim()) {
      sendMessage();
    }
  };

  recognition.onerror = (event) => {
    isRecording = false;
    micBtn.classList.remove("recording");
    if (event.error === "not-allowed") {
      showToast("Microphone access denied. Please allow mic access in browser settings.", "red");
    } else if (event.error === "no-speech") {
      showToast("No speech detected. Try again.", "yellow");
    } else {
      console.error("Speech recognition error:", event.error);
    }
  };
}

// Mic button click
micBtn.addEventListener("click", () => {
  if (!recognition) return;

  // Don't interrupt Maya speaking
  if (isMayaSpeaking) {
    showToast("Maya is speaking — please wait before recording.", "yellow");
    return;
  }

  if (!isRecording) {
    recognition.start();
    isRecording = true;
    micBtn.classList.add("recording");
    micBtn.setAttribute("aria-label", "Stop voice recording");
  } else {
    recognition.stop();
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.setAttribute("aria-label", "Start voice recording");
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  SEND ON ENTER KEY
// ─────────────────────────────────────────────────────────────────────────────
messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !sendBtn.disabled) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", () => {
  if (!sendBtn.disabled) sendMessage();
});

// ─────────────────────────────────────────────────────────────────────────────
//  MODE SELECTION
// ─────────────────────────────────────────────────────────────────────────────
const MODE_LABELS = {
  casual:    "🗣️ Casual Chat",
  hr:        "💼 HR Interview",
  technical: "💻 Technical Interview",
  gd:        "🏛️ Group Discussion",
};

modeCards.forEach(card => {
  card.addEventListener("click", () => {
    currentMode = card.dataset.mode;

    // Update badge
    modeBadge.textContent = MODE_LABELS[currentMode] || currentMode;

    // Switch screens
    modeScreen.classList.add("hidden");
    chatScreen.classList.remove("hidden");

    // Reset state
    conversationHistory    = [];
    sessionScores          = [];
    sessionVocabSuggestions = [];
    sessionGrammarErrors   = [];
    totalMessages          = 0;
    chatArea.innerHTML     = "";

    // Start session
    startSession(currentMode);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  MOBILE FEEDBACK DRAWER
// ─────────────────────────────────────────────────────────────────────────────
feedbackFab.addEventListener("click", () => {
  feedbackDrawer.classList.add("open");
  feedbackDrawer.setAttribute("aria-hidden", "false");
  drawerOverlay.classList.remove("hidden");
  feedbackFab.setAttribute("aria-expanded", "true");
});

function closeDrawer() {
  feedbackDrawer.classList.remove("open");
  feedbackDrawer.setAttribute("aria-hidden", "true");
  drawerOverlay.classList.add("hidden");
  feedbackFab.setAttribute("aria-expanded", "false");
}

closeDrawerBtn.addEventListener("click", closeDrawer);
drawerOverlay.addEventListener("click", closeDrawer);

// ─────────────────────────────────────────────────────────────────────────────
//  SESSION SUMMARY MODAL
// ─────────────────────────────────────────────────────────────────────────────
function computeMostCommonError(errors) {
  if (errors.length === 0) return "None detected — great job! 🎉";
  // Extract the "wrong phrase" portion before the arrow
  const freq = {};
  errors.forEach(e => {
    const key = e.split("→")[0].trim();
    freq[key] = (freq[key] || 0) + 1;
  });
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  return `"${sorted[0][0]}" (${sorted[0][1]}× repeated)`;
}

function showSessionSummary() {
  // Calculate stats
  const avgScore = sessionScores.length > 0
    ? (sessionScores.reduce((a, b) => a + b, 0) / sessionScores.length).toFixed(1)
    : "—";

  const commonError = computeMostCommonError(sessionGrammarErrors);

  // Top 3 unique vocab suggestions
  const uniqueVocab = [...new Set(sessionVocabSuggestions)].slice(0, 3);

  // Populate modal
  document.getElementById("stat-messages").textContent     = totalMessages;
  document.getElementById("stat-avg-score").textContent    = avgScore;
  document.getElementById("stat-common-error").textContent = commonError;

  const vocabList = document.getElementById("stat-vocab-list");
  if (uniqueVocab.length > 0) {
    vocabList.innerHTML = uniqueVocab
      .map(v => `<li>${escapeHTML(v)}</li>`)
      .join("");
  } else {
    vocabList.innerHTML = `<li class="text-muted">No suggestions collected yet.</li>`;
  }

  // Motivational message
  const motivMsg = document.getElementById("motivational-msg");
  const numScore = parseFloat(avgScore);
  if (isNaN(numScore)) {
    motivMsg.textContent = "Great start! Keep practicing daily to see improvement. 🎯";
  } else if (numScore >= 8) {
    motivMsg.textContent = "Excellent session! You're interview-ready. Keep it up! 🌟";
  } else if (numScore >= 6) {
    motivMsg.textContent = "Good progress! Focus on the grammar tips and you'll be there soon. 💪";
  } else {
    motivMsg.textContent = "Every session counts! Review the vocabulary suggestions and practice daily. 🎯";
  }

  // Show modal
  summaryModal.classList.remove("hidden");
  summaryModal.setAttribute("aria-hidden", "false");
}

endSessionBtn.addEventListener("click", showSessionSummary);

closeModalBtn.addEventListener("click", () => {
  summaryModal.classList.add("hidden");
  summaryModal.setAttribute("aria-hidden", "true");
});

newSessionBtn.addEventListener("click", () => {
  window.location.reload();
});

// Close modal on overlay click
summaryModal.addEventListener("click", (e) => {
  if (e.target === summaryModal) {
    summaryModal.classList.add("hidden");
    summaryModal.setAttribute("aria-hidden", "true");
  }
});

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    if (!summaryModal.classList.contains("hidden")) {
      summaryModal.classList.add("hidden");
      summaryModal.setAttribute("aria-hidden", "true");
    }
    closeDrawer();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
//  INIT
// ─────────────────────────────────────────────────────────────────────────────
(function init() {
  setupSpeechRecognition();
  // Initial state: controls disabled until session starts
  sendBtn.disabled = false;
})();

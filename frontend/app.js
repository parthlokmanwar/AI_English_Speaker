/* ═══════════════════════════════════════════════════════════
   FluentRound — app.js  v2.0
   Author: Antigravity AI
   Description: Full client-side logic for the FluentRound app.
                Includes turn_count tracking, progress dashboard,
                session save, and question injection support.
═══════════════════════════════════════════════════════════ */

// ── Backend URL — CHANGE THIS AFTER DEPLOYING TO RENDER ──────────────────────
const API_BASE_URL = "http://localhost:8000"; // Change to your Render URL after deployment

// ─────────────────────────────────────────────────────────────────────────────
//  STATE
// ─────────────────────────────────────────────────────────────────────────────
let conversationHistory     = []; // [{role, content}, ...]
let sessionScores           = []; // all non-zero integer scores
let sessionVocabSuggestions = []; // all better_words strings
let sessionGrammarErrors    = []; // all grammar_error strings
let currentMode             = "";
let isRecording             = false;
let isMayaSpeaking          = false;
let recognition             = null;
let totalMessages           = 0;  // total user + maya exchanges
let turnCount               = 0;  // user turns sent to /chat (incremented after each send)

// ─────────────────────────────────────────────────────────────────────────────
//  DOM REFERENCES
// ─────────────────────────────────────────────────────────────────────────────
const modeScreen        = document.getElementById("mode-screen");
const progressScreen    = document.getElementById("progress-screen");
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
const sessionSavedNote  = document.getElementById("session-saved-note");

// Mode cards
const modeCards         = document.querySelectorAll(".mode-card");

// Progress screen
const progressBtn       = document.getElementById("progress-btn");
const progressBackBtn   = document.getElementById("progress-back-btn");

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

  let scoreClass = "score-low";
  if (score >= 7) scoreClass = "score-high";
  else if (score >= 5) scoreClass = "score-mid";

  const scoreWidth = `${Math.round((score / 10) * 100)}%`;

  const grammarHTML = grammar_errors.length > 0
    ? `<ul class="feedback-section__list">${grammar_errors.map(e =>
        `<li class="feedback-section__item feedback-section__item--grammar">${escapeHTML(e)}</li>`
      ).join("")}</ul>`
    : `<p class="feedback-all-good">✅ All good!</p>`;

  const vocabHTML = better_words.length > 0
    ? `<ul class="feedback-section__list">${better_words.map(w =>
        `<li class="feedback-section__item feedback-section__item--vocab">${escapeHTML(w)}</li>`
      ).join("")}</ul>`
    : `<p class="feedback-all-good">✅ All good!</p>`;

  const fillerHTML = filler_words.length > 0
    ? `<div class="filler-tags">${filler_words.map(f =>
        `<span class="filler-tag">${escapeHTML(f)}</span>`
      ).join("")}</div>`
    : `<p class="feedback-all-good">✅ None detected!</p>`;

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
        turn_count: turnCount,
      }),
    });

    // Increment turn count after each send
    turnCount++;

    hideTypingIndicator();

    if (res.status === 429) {
      showToast("AI service is busy right now. Please wait a moment and try again.", "yellow");
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

    addBubble(reply, "maya");
    conversationHistory.push({ role: "assistant", content: reply });
    totalMessages++;

    updateFeedbackPanels(feedback);

    if (feedback.score && feedback.score > 0) {
      sessionScores.push(feedback.score);
    }
    if (Array.isArray(feedback.better_words)) {
      sessionVocabSuggestions.push(...feedback.better_words);
    }
    if (Array.isArray(feedback.grammar_errors)) {
      sessionGrammarErrors.push(...feedback.grammar_errors);
    }

    await playTTS(reply);
    setControlsEnabled(true);

  } catch (err) {
    hideTypingIndicator();
    turnCount++; // still increment even on error
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
    micBtn.style.display = "none";
    browserWarning.classList.remove("hidden");
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous      = true;   // Don't stop on short pauses
  recognition.interimResults  = true;   // Show live transcript in input field
  recognition.lang            = "en-IN";
  recognition.maxAlternatives = 1;

  let finalTranscript = "";   // Accumulates confirmed words
  let sendTimer       = null; // Delay before auto-sending

  recognition.onresult = (event) => {
    let interimTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        finalTranscript += result[0].transcript + " ";
      } else {
        interimTranscript += result[0].transcript;
      }
    }

    // Show combined transcript live in the input
    messageInput.value = (finalTranscript + interimTranscript).trim();

    // Reset send timer — wait 600ms of silence after last speech before sending
    clearTimeout(sendTimer);
    if (finalTranscript.trim()) {
      sendTimer = setTimeout(() => {
        recognition.stop(); // Will trigger onend which fires sendMessage
      }, 600);
    }
  };

  recognition.onend = () => {
    isRecording = false;
    micBtn.classList.remove("recording");
    micBtn.setAttribute("aria-label", "Start voice recording");
    clearTimeout(sendTimer);

    const captured = finalTranscript.trim() || messageInput.value.trim();
    finalTranscript = ""; // Reset for next recording

    if (captured) {
      messageInput.value = captured;
      sendMessage();
    }
  };

  recognition.onerror = (event) => {
    isRecording = false;
    micBtn.classList.remove("recording");
    finalTranscript = "";
    clearTimeout(sendTimer);
    if (event.error === "not-allowed") {
      showToast("Microphone access denied. Please allow mic access in browser settings.", "red");
    } else if (event.error === "no-speech") {
      showToast("No speech detected. Tap the mic and try again.", "yellow");
    } else if (event.error === "aborted") {
      // User manually stopped — no toast needed
    } else {
      console.error("Speech recognition error:", event.error);
    }
  };

  // Store reset function for mic button to call
  recognition._resetTranscript = () => { finalTranscript = ""; clearTimeout(sendTimer); };
}

// Mic button click
micBtn.addEventListener("click", () => {
  if (!recognition) return;

  if (isMayaSpeaking) {
    showToast("Maya is speaking — please wait before recording.", "yellow");
    return;
  }

  if (!isRecording) {
    // Start fresh recording
    messageInput.value = "";
    if (recognition._resetTranscript) recognition._resetTranscript();
    recognition.start();
    isRecording = true;
    micBtn.classList.add("recording");
    micBtn.setAttribute("aria-label", "Stop voice recording");
  } else {
    // User manually stopped — onend will fire and handle sending
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

    modeBadge.textContent = MODE_LABELS[currentMode] || currentMode;

    modeScreen.classList.add("hidden");
    chatScreen.classList.remove("hidden");

    // Reset state
    conversationHistory     = [];
    sessionScores           = [];
    sessionVocabSuggestions = [];
    sessionGrammarErrors    = [];
    totalMessages           = 0;
    turnCount               = 0;
    chatArea.innerHTML      = "";

    startSession(currentMode);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
//  PROGRESS SCREEN
// ─────────────────────────────────────────────────────────────────────────────
progressBtn.addEventListener("click", () => {
  modeScreen.classList.add("hidden");
  progressScreen.classList.remove("hidden");
  loadProgressDashboard();
});

progressBackBtn.addEventListener("click", () => {
  progressScreen.classList.add("hidden");
  modeScreen.classList.remove("hidden");
});

async function loadProgressDashboard() {
  const loadingEl  = document.getElementById("progress-loading");
  const emptyEl    = document.getElementById("progress-empty");
  const contentEl  = document.getElementById("progress-content");

  // Reset state
  loadingEl.classList.remove("hidden");
  emptyEl.classList.add("hidden");
  contentEl.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE_URL}/progress`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    loadingEl.classList.add("hidden");

    if (data.total_sessions === 0) {
      emptyEl.classList.remove("hidden");
      return;
    }

    contentEl.classList.remove("hidden");

    // Stats
    document.getElementById("prog-total-sessions").textContent = data.total_sessions;
    const trend = data.avg_score_trend || [];
    const latestScore = trend.length > 0 ? trend[trend.length - 1] : "—";
    const bestScore   = trend.length > 0 ? Math.max(...trend) : "—";
    document.getElementById("prog-latest-score").textContent = latestScore;
    document.getElementById("prog-best-score").textContent   = bestScore;

    // Improvement note
    document.getElementById("prog-improvement-note").textContent = data.improvement_note || "";

    // Common issue
    document.getElementById("prog-common-issue").textContent =
      data.most_common_grammar_issue || "None detected — great job! 🎉";

    // Draw chart
    if (trend.length > 0) {
      drawScoreChart(trend);
    }

    // Recent sessions list (last 5, newest first)
    renderSessionsList(data.sessions || []);

  } catch (err) {
    loadingEl.classList.add("hidden");
    console.error("Failed to load progress:", err);
    showToast("Could not load progress. Is the backend running?", "red");
    progressScreen.classList.add("hidden");
    modeScreen.classList.remove("hidden");
  }
}

// ─── Canvas Score Chart ───────────────────────────────────────────────────────
function drawScoreChart(scores) {
  const canvas = document.getElementById("score-chart");
  const ctx = canvas.getContext("2d");
  const W = canvas.width;
  const H = canvas.height;

  // Clear
  ctx.clearRect(0, 0, W, H);

  const PAD = { top: 20, right: 30, bottom: 30, left: 40 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const minScore = 0;
  const maxScore = 10;

  // Grid lines
  ctx.strokeStyle = "rgba(139, 92, 246, 0.15)";
  ctx.lineWidth = 1;
  [0, 2, 4, 6, 8, 10].forEach(val => {
    const y = PAD.top + chartH - ((val - minScore) / (maxScore - minScore)) * chartH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(PAD.left + chartW, y);
    ctx.stroke();

    // Y labels
    ctx.fillStyle = "rgba(160, 160, 200, 0.8)";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(val, PAD.left - 6, y + 4);
  });

  if (scores.length === 1) {
    // Single point — draw a dot
    const x = PAD.left + chartW / 2;
    const y = PAD.top + chartH - ((scores[0] - minScore) / (maxScore - minScore)) * chartH;

    ctx.beginPath();
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fillStyle = "#8b5cf6";
    ctx.fill();
    return;
  }

  // Compute point positions
  const points = scores.map((s, i) => ({
    x: PAD.left + (i / (scores.length - 1)) * chartW,
    y: PAD.top + chartH - ((s - minScore) / (maxScore - minScore)) * chartH,
  }));

  // Gradient fill
  const gradient = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH);
  gradient.addColorStop(0, "rgba(139, 92, 246, 0.35)");
  gradient.addColorStop(1, "rgba(139, 92, 246, 0.02)");

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(points[points.length - 1].x, PAD.top + chartH);
  ctx.lineTo(points[0].x, PAD.top + chartH);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = "#8b5cf6";
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";
  ctx.stroke();

  // Dots
  points.forEach((p, i) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = "#c4b5fd";
    ctx.fill();
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Score label above dot
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "bold 11px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(scores[i], p.x, p.y - 10);
  });
}

// ─── Sessions List ────────────────────────────────────────────────────────────
function renderSessionsList(sessions) {
  const container = document.getElementById("prog-sessions-list");
  // Show last 5, newest first
  const recent = [...sessions].reverse().slice(0, 5);
  if (recent.length === 0) {
    container.innerHTML = `<p class="text-secondary">No sessions recorded yet.</p>`;
    return;
  }
  container.innerHTML = recent.map(s => {
    const date = s.date ? new Date(s.date).toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
    }) : "—";
    const modeLabel = { casual: "🗣️ Casual", hr: "💼 HR", technical: "💻 Technical", gd: "🏛️ GD" }[s.mode] || s.mode;
    const score = s.avg_score != null ? parseFloat(s.avg_score).toFixed(1) : "—";
    let scoreClass = "score-low";
    if (parseFloat(score) >= 7) scoreClass = "score-high";
    else if (parseFloat(score) >= 5) scoreClass = "score-mid";

    return `
      <div class="session-item">
        <div class="session-item__meta">
          <span class="session-item__mode">${modeLabel}</span>
          <span class="session-item__date">${date}</span>
        </div>
        <div class="session-item__score ${scoreClass}">${score}<span class="session-item__denom">/10</span></div>
      </div>
    `;
  }).join("");
}

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
  const freq = {};
  errors.forEach(e => {
    const key = e.split("→")[0].trim();
    freq[key] = (freq[key] || 0) + 1;
  });
  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]);
  return `"${sorted[0][0]}" (${sorted[0][1]}× repeated)`;
}

async function showSessionSummary() {
  const avgScore = sessionScores.length > 0
    ? (sessionScores.reduce((a, b) => a + b, 0) / sessionScores.length).toFixed(1)
    : "0";

  const commonError = computeMostCommonError(sessionGrammarErrors);
  const uniqueVocab = [...new Set(sessionVocabSuggestions)].slice(0, 3);

  // Populate modal
  document.getElementById("stat-messages").textContent     = totalMessages;
  document.getElementById("stat-avg-score").textContent    = avgScore === "0" ? "—" : avgScore;
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
  if (isNaN(numScore) || numScore === 0) {
    motivMsg.textContent = "Great start! Keep practicing daily to see improvement. 🎯";
  } else if (numScore >= 8) {
    motivMsg.textContent = "Excellent session! You're interview-ready. Keep it up! 🌟";
  } else if (numScore >= 6) {
    motivMsg.textContent = "Good progress! Focus on the grammar tips and you'll be there soon. 💪";
  } else {
    motivMsg.textContent = "Every session counts! Review the vocabulary suggestions and practice daily. 🎯";
  }

  // Hide saved note initially
  sessionSavedNote.classList.add("hidden");

  // Show modal
  summaryModal.classList.remove("hidden");
  summaryModal.setAttribute("aria-hidden", "false");

  // Save session to backend (fire and forget — don't block the modal)
  if (sessionScores.length > 0) {
    try {
      const res = await fetch(`${API_BASE_URL}/session/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: currentMode,
          total_messages: totalMessages,
          avg_score: parseFloat(avgScore),
          common_grammar_issue: commonError,
          vocab_suggestions: uniqueVocab,
          grammar_errors: sessionGrammarErrors,
        }),
      });
      if (res.ok) {
        sessionSavedNote.classList.remove("hidden");
      }
    } catch (err) {
      console.error("Failed to save session:", err);
    }
  }
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

// Close modal or drawer on Escape key
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
  sendBtn.disabled = false;
})();

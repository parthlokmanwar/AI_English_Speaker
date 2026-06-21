# FluentRound 🎙️

> **AI-powered English conversation practice app for Indian engineering students**

FluentRound is an AI-powered English conversation practice app built for Indian engineering students. It uses conversational AI to simulate natural English conversations and provides real-time feedback on grammar, vocabulary, fluency, and filler words — all through a beautiful, voice-enabled interface.

---

## ✨ Features

- 🤖 **AI Conversation Partner** — Maya, powered by Llama 3.3 70B via OpenRouter
- 🎙️ **Voice Input** — Browser Web Speech API (Chrome recommended)
- 🔊 **Voice Output** — Microsoft Neural TTS (`en-IN-NeerjaNeural`) via edge-tts
- 📊 **Real-time Feedback** — Grammar errors, better vocabulary, filler words, fluency score
- 4️⃣ **Practice Modes** — Casual Chat, HR Interview, Technical Interview, Group Discussion
- 📋 **Session Summary** — Stats, average score, top vocabulary suggestions
- 📱 **Mobile Responsive** — Bottom drawer feedback panel on mobile

---

## 🚀 Local Setup

### Prerequisites
- Python 3.9+
- Chrome browser (for voice input)
- Free OpenRouter API key (see below)

### Backend

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Copy the example env file
cp .env.example .env

# Add your OpenRouter API key to .env
# Open .env and replace "your_openrouter_api_key_here" with your actual key

# Start the backend server
uvicorn main:app --reload
```

Backend runs at **http://localhost:8000**

### Frontend

```bash
# No build step needed!
# Just open frontend/index.html in Chrome
```

Or use VS Code Live Server extension for hot reload.

---

## 🔑 Get Free OpenRouter API Key

1. Go to [https://openrouter.ai](https://openrouter.ai)
2. Sign up for free
3. Go to **API Keys** section
4. Click **Create a new key**
5. Copy the key
6. Paste it in `backend/.env` as:
   ```
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
   ```

> Free models (ending in `:free`) have rate limits but cost **nothing**. If you hit the rate limit, wait a few minutes.

---

## ☁️ Deploy Backend to Render

1. **Push your code** to a GitHub repository
2. Go to [https://render.com](https://render.com) and sign up free
3. Click **"New Web Service"** → connect your GitHub repo
4. Set **Root Directory** to `backend`
5. **Build command:** `pip install -r requirements.txt`
6. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Under **Environment Variables**, add:
   - Key: `OPENROUTER_API_KEY`
   - Value: your OpenRouter API key
8. Click **Deploy** — takes 2–3 minutes
9. Copy your Render URL (e.g. `https://fluentround-backend.onrender.com`)

---

## 🔗 Connect Frontend to Deployed Backend

1. Open `frontend/app.js`
2. Change **line 1**:
   ```js
   // Before (local):
   const API_BASE_URL = "http://localhost:8000";

   // After (deployed):
   const API_BASE_URL = "https://your-render-url.onrender.com";
   ```
3. Open `frontend/index.html` in Chrome — it now connects to your live backend!

---

## 📁 Project Structure

```
fluentround/
├── backend/
│   ├── main.py           # FastAPI app — /chat, /tts, /greeting endpoints
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment variable template
│   └── .env              # Your actual API key (DO NOT commit)
├── frontend/
│   ├── index.html        # Single-page app — no build step
│   ├── style.css         # Full design system with CSS variables
│   └── app.js            # Complete client-side logic
├── render.yaml           # Render.com deployment config
└── README.md             # This file
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| AI / LLM | OpenRouter API — `meta-llama/llama-3.3-70b-instruct:free` |
| Voice Output (TTS) | `edge-tts` — Microsoft `en-IN-NeerjaNeural` |
| Voice Input (STT) | Browser Web Speech API |
| Frontend | Plain HTML + CSS + Vanilla JavaScript |
| Deployment | Render.com (free tier) |

---

## ⚠️ Important Notes

- **Use Chrome** for best speech recognition support (Firefox/Safari have limited STT support)
- **Free Render tier sleeps** after 15 min inactivity — first request of the day may take 30–60 seconds to wake up
- **Free OpenRouter models** have daily rate limits — if you hit them, wait a few hours or try a different `:free` model by changing the `MODEL` constant in `backend/main.py`
- **Never commit `.env`** — it contains your API key. The `.gitignore` file is set up to prevent this.

---

## 📱 Practice Modes

| Mode | Description | Best For |
|------|-------------|----------|
| 🗣️ **Casual Chat** | Everyday conversation — day, hobbies, college life | Building comfort with English |
| 💼 **HR Interview** | Tell me about yourself, strengths/weaknesses, situational questions | Campus placement prep |
| 💻 **Technical Interview** | Projects, tech stack, explain concepts simply | Technical round prep |
| 🏛️ **Group Discussion** | GD topics, structured arguments, devil's advocate | GD round prep |

---

## 🎨 Design

- Deep space dark theme with violet accents
- Animated background orbs
- Glassmorphism elements
- Smooth bubble animations
- Responsive — works on mobile and desktop
- Score bar: 🟢 green (≥7), 🟡 yellow (5–6), 🔴 red (≤4)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ for Indian engineering students by Antigravity AI*

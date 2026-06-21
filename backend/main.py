import os
import io
import random
from datetime import datetime

import httpx
import edge_tts
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ─── Load environment ───────────────────────────────────────────────────────
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Model Fallback Chain ─────────────────────────────────────────────────────
# Tries free models first, falls back to paid if all fail.
# Configured via .env variables FREE_MODELS and PAID_FALLBACK_MODEL
FREE_MODELS_ENV = os.getenv("FREE_MODELS", "meta-llama/llama-3.3-70b-instruct:free,qwen/qwen3-235b-a22b:free,deepseek/deepseek-chat-v3-0324:free")
PAID_FALLBACK_MODEL = os.getenv("PAID_FALLBACK_MODEL", "openai/gpt-4o-mini")

MODEL_CHAIN = [m.strip() for m in FREE_MODELS_ENV.split(",") if m.strip()]
if PAID_FALLBACK_MODEL:
    MODEL_CHAIN.append(PAID_FALLBACK_MODEL.strip())

# ─── System Prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Maya, a warm, encouraging English conversation coach for Indian engineering students preparing for campus placements and job interviews. You speak naturally and conversationally — never robotic, never preachy.

Your TWO jobs every turn:
1. CONVERSE: Reply naturally to the student based on the selected mode. Keep it engaging, ask follow-up questions, react like a real person. In HR/technical mode, steer toward placement-relevant topics (projects, goals, strengths, technical concepts). In GD mode, present discussion topics and counter-arguments.
2. ANALYZE: Silently analyze the student's message for language issues.

Mode behavior:
- casual: everyday conversation — how was your day, hobbies, college life, current events
- hr: HR interview practice — tell me about yourself, strengths/weaknesses, why this company, situational questions, body language tips
- technical: technical interview — explain your projects, tech stack questions, problem-solving approach, explain concepts simply
- gd: group discussion — introduce topics relevant to engineering/India/tech, encourage structured arguments, play devil's advocate

CRITICAL: You MUST return ONLY a single valid JSON object. No text before it, no text after it, no markdown code fences, no explanation. Only this exact structure:
{"reply": "your conversational reply here", "feedback": {"grammar_errors": ["list grammar mistakes as: wrong phrase → correct phrase: brief explanation"], "better_words": ["word they used → better alternative: why it sounds more professional"], "filler_words": ["every filler word or phrase detected"], "fluency_tip": "one short specific actionable tip based on THIS message", "score": 8}}

Score rules: 1-10 integer only. 10 = perfect fluency, 8-9 = minor issues, 6-7 = noticeable errors but understandable, 4-5 = frequent errors, 1-3 = hard to understand. Be honest but kind. If grammar_errors/better_words/filler_words have nothing to report, return empty arrays []. Never return null."""

# ─── Greeting Templates ─────────────────────────────────────────────────────
GREETINGS = {
    "morning": {
        "casual": [
            "Good morning! ☀️ I'm Maya, your English practice partner! Ready for a fun chat? How's your morning going so far?",
            "Good morning! 😊 I'm Maya! Mornings are perfect for a quick English chat. What's on your mind today?",
            "Rise and shine! Good morning! I'm Maya, and I'm here to make English practice feel effortless. How did you sleep? 😊",
        ],
        "hr": [
            "Good morning! I'm Maya, your English practice partner 😊 Ready to ace those HR rounds today? Let's start simple — can you tell me a little about yourself?",
            "Good morning! Great time to sharpen those interview skills! I'm Maya. Let's warm up — how would you introduce yourself in an HR interview?",
            "Good morning! 🌅 I'm Maya, and today we're going to nail those HR rounds! Ready? Let's begin — tell me about yourself in 2 minutes.",
        ],
        "technical": [
            "Good morning! 💻 I'm Maya, your tech interview coach! Let's get those technical communication skills polished. Tell me — what's your main tech stack?",
            "Good morning! Ready to explain your projects like a pro? I'm Maya! Let's dive in — what's the most exciting project you've worked on?",
            "Morning! Tech interviews can be tricky, but with clear communication you'll shine! I'm Maya. What programming languages are you most comfortable with?",
        ],
        "gd": [
            "Good morning! 🏛️ I'm Maya, and today we're practicing Group Discussion skills! Today's topic: 'Is AI a boon or bane for engineering students?' — go ahead and share your opening argument!",
            "Good morning! GD rounds require quick, structured thinking. I'm Maya! Let's warm up — what do you think about the growing influence of social media on youth?",
            "Morning! Let's sharpen your GD skills today. I'm Maya. Our topic: 'Remote work vs Office work — which is better for freshers?' Share your stance!",
        ],
    },
    "afternoon": {
        "casual": [
            "Good afternoon! 😊 I'm Maya, your English conversation buddy. Taking a break? Let's make it productive with some fun conversation practice!",
            "Good afternoon! Hope your day's going well. I'm Maya — let's chat in English and make the most of your afternoon break!",
            "Afternoon! 🌤️ I'm Maya. Perfect time for a quick English chat — what's the most interesting thing that happened to you today?",
        ],
        "hr": [
            "Good afternoon! Placement season can be stressful, but practice makes perfect. I'm Maya! Let's work on your HR interview skills. Tell me — what are your key strengths?",
            "Good afternoon! 💼 Ready for some placement prep? I'm Maya! Let's tackle a classic HR question — where do you see yourself 5 years from now?",
            "Afternoon! HR rounds are all about confidence and communication. I'm Maya, and we're going to build both today. Shall we start with 'Tell me about yourself'?",
        ],
        "technical": [
            "Good afternoon! 💻 Technical interviews need both skills AND communication. I'm Maya — let's practice explaining complex ideas simply. What project are you most proud of?",
            "Afternoon! Ready to talk tech? I'm Maya. Let's practice — can you explain what REST APIs are, as if explaining to a non-technical person?",
            "Good afternoon! Tech communication is a superpower. I'm Maya! Tell me — how would you explain machine learning to your grandmother? 😄",
        ],
        "gd": [
            "Good afternoon! 🏛️ GD practice time! I'm Maya. Today's topic: 'Should engineering colleges make coding mandatory from first year?' — what's your take?",
            "Afternoon! Let's sharpen those GD skills. I'm Maya. Our discussion: 'Electric vehicles vs traditional vehicles — the future of Indian roads.' Open floor — go!",
            "Good afternoon! GDs require structure and confidence. I'm Maya! Topic for today: 'Is the Indian education system preparing students for the real world?' Share your thoughts!",
        ],
    },
    "evening": {
        "casual": [
            "Good evening! Long day? I'm Maya — let's just have a relaxed chat in English. How did your day go?",
            "Good evening! 🌆 I'm Maya, your English practice partner. Evenings are perfect for a chill conversation — what did you get up to today?",
            "Evening! 😊 Winding down? I'm Maya! Let's have a fun English chat before you call it a day. How are you feeling right now?",
        ],
        "hr": [
            "Good evening! Even after a long day, a bit of interview practice goes a long way! I'm Maya. Tell me — how would you handle a tough interviewer?",
            "Good evening! 💼 Evening sessions are often the most focused ones. I'm Maya! Let's work on some tricky HR questions — what's your biggest weakness?",
            "Evening! Placement interviews can feel daunting, but you've got this. I'm Maya! Let's practice — tell me about a time you showed leadership.",
        ],
        "technical": [
            "Good evening! 💻 Evening cram session? Let's make it count! I'm Maya. Walk me through your favorite personal project — what problem does it solve?",
            "Good evening! Tech interviews reward clear thinkers. I'm Maya! Let's practice — explain the difference between stack and heap memory in simple terms.",
            "Evening! 🌙 I'm Maya, your technical interview coach. Let's work on explaining concepts clearly. Can you explain what happens when you type a URL in the browser?",
        ],
        "gd": [
            "Good evening! 🏛️ Evening GD practice! I'm Maya. Today's hot topic: 'Should India ban TikTok and other Chinese apps permanently?' — argue your position!",
            "Good evening! GDs can feel intimidating, but you've got this. I'm Maya! Let's discuss: 'Is a startup better than a corporate job for engineering freshers?' Go!",
            "Evening! I'm Maya, and we're doing GD practice today. Topic: 'Cryptocurrency — revolution or risk?' Share your structured argument!",
        ],
    },
    "night": {
        "casual": [
            "Hey, night owl! 🌙 I'm Maya. Can't sleep or just burning the midnight oil? Let's have a calm English chat — what's keeping you up?",
            "Good night! 😊 I'm Maya, your English practice partner. Late-night study sessions call for a little brain break — what's on your mind?",
            "Up late? 🌙 I'm Maya! Perfect time for a quiet English conversation. How has your day been overall?",
        ],
        "hr": [
            "Burning the midnight oil for placements? 🌙 I'm Maya! Late-night practice shows real dedication. Let's work on a key HR question — tell me about yourself!",
            "Night mode: ON! 💼 I'm Maya. Commitment to practice at this hour is impressive. Let's tackle HR interview prep — what motivates you to do your best?",
            "Late night practice session! 🌙 I'm Maya. HR rounds often have unexpected questions — let's prep. Tell me, why should we hire you over other candidates?",
        ],
        "technical": [
            "Midnight coding session? 💻 I'm Maya! Night is when the best developers think clearly. Let's do some tech interview practice — explain recursion with an example.",
            "🌙 Night owl developer! I'm Maya. Late-night clarity is real — let's use it! Walk me through how you would approach debugging a production issue.",
            "Up late studying? 💻 I'm Maya, and we're going to make this session count! Tell me — what data structures do you use most in your projects and why?",
        ],
        "gd": [
            "Night GD session! 🌙 I'm Maya. Dedication at this hour is impressive. Let's discuss: 'Is sleep deprivation a badge of honor in engineering culture? Should it be?' Argue away!",
            "Burning the midnight oil! 🏛️ I'm Maya. GD practice: 'Should engineering students have mandatory internships in their curriculum?' What's your structured argument?",
            "Late night, sharp mind! 🌙 I'm Maya. GD topic: 'Data privacy in the age of AI — personal freedom vs technological advancement.' Go ahead, make your case!",
        ],
    },
}

# ─── Pydantic Models ─────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    mode: str = "casual"

class TTSRequest(BaseModel):
    text: str

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(title="FluentRound API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Helper: Get Time of Day ─────────────────────────────────────────────────
def get_time_of_day() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    else:
        return "night"

# ─── Helper: TTS in Memory ───────────────────────────────────────────────────
async def generate_tts(text: str) -> bytes:
    communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural")
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer.read()

# ─── Helper: Clean LLM Response ──────────────────────────────────────────────
def clean_llm_response(text: str) -> str:
    text = text.strip()
    # Remove markdown code fences
    for fence in ["```json", "```JSON", "```"]:
        text = text.replace(fence, "")
    text = text.strip()
    # Strip any text before the first { and after the last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start:end + 1]
    return text

# ─── Fallback Response ───────────────────────────────────────────────────────
FALLBACK_RESPONSE = {
    "reply": "Sorry, I had a small hiccup! Could you repeat that?",
    "feedback": {
        "grammar_errors": [],
        "better_words": [],
        "filler_words": [],
        "fluency_tip": "Keep going — consistency is key!",
        "score": 0,
    },
}

# ─── Helper: call one model, return raw text or raise ─────────────────────────
async def call_model(model: str, messages: list, headers: dict) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 900,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    # Surface rate limit vs other errors distinctly
    if response.status_code == 429:
        raise ValueError("rate_limit")
    if response.status_code in (502, 503, 504):
        raise ValueError("unavailable")
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]

# ─── POST /chat ───────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: ChatRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set.")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fluentround.app",
        "X-Title": "FluentRound",
    }

    import json
    raw_content = None
    last_error = None

    # ── Try each model in the chain until one works ───────────────────────────
    for i, model in enumerate(MODEL_CHAIN):
        is_paid = not model.endswith(":free")
        tier_label = f"Paid fallback ({model})" if is_paid else f"Free tier {i+1} ({model})"
        try:
            print(f"[FluentRound] Trying {tier_label}...")
            raw_content = await call_model(model, messages, headers)
            print(f"[FluentRound] [SUCCESS] with {model}")
            break  # Got a response — stop trying

        except ValueError as ve:
            # rate_limit or unavailable — try next model
            last_error = str(ve)
            print(f"[FluentRound] [WARNING] {model} -> {ve}, trying next model...")
            continue

        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP {exc.response.status_code}"
            print(f"[FluentRound] [WARNING] {model} -> HTTP error {exc.response.status_code}, trying next...")
            continue

        except Exception as exc:
            last_error = str(exc)
            print(f"[FluentRound] [WARNING] {model} -> {exc}, trying next...")
            continue

    # All models failed
    if raw_content is None:
        # If all were rate-limited return 429, else 500
        if last_error == "rate_limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit reached on all models. Please wait 30 seconds and try again.",
            )
        raise HTTPException(status_code=500, detail=f"All models failed. Last error: {last_error}")

    # ── Clean and parse JSON from LLM response ────────────────────────────────
    try:
        cleaned = clean_llm_response(raw_content)
        parsed = json.loads(cleaned)
        return parsed
    except Exception as e:
        print(f"[FluentRound] Error parsing JSON: {e}")
        print(f"[FluentRound] Raw content: {raw_content}")
        return FALLBACK_RESPONSE

# ─── POST /tts ────────────────────────────────────────────────────────────────
@app.post("/tts")
async def tts(request: TTSRequest):
    try:
        audio_bytes = await generate_tts(request.text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(exc)}")

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline"},
    )

# ─── GET /greeting ────────────────────────────────────────────────────────────
@app.get("/greeting")
async def greeting(mode: str = Query(default="casual")):
    time_of_day = get_time_of_day()
    valid_modes = ["casual", "hr", "technical", "gd"]
    safe_mode = mode if mode in valid_modes else "casual"
    variants = GREETINGS.get(time_of_day, GREETINGS["morning"]).get(safe_mode, GREETINGS["morning"]["casual"])
    return {"greeting": random.choice(variants)}

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "app": "FluentRound API", "version": "1.0.0"}

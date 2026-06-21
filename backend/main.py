import os
import io
import json
import random
import re
import asyncio
from datetime import datetime

import httpx
import edge_tts
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from questions import get_random_question
from storage import save_session, load_sessions
from analytics import SessionAnalyzer

# ─── Load environment ───────────────────────────────────────────────────────
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Paid Model Configuration ─────────────────────────────────────────────────
PRIMARY_MODEL  = "deepseek/deepseek-chat"
FALLBACK_MODEL = "google/gemini-2.0-flash-001"

# DeepSeek Chat pricing (per 1M tokens, as of June 2025)
COST_INPUT_PER_TOKEN  = 0.27 / 1_000_000
COST_OUTPUT_PER_TOKEN = 1.10 / 1_000_000

# ─── System Prompt (tightened) ──────────────────────────────────────────────
SYSTEM_PROMPT = """You are Maya, a warm English conversation coach for Indian engineering students prepping for placements.

Each turn: (1) reply naturally based on mode, ask follow-ups, steer toward placement topics in hr/technical mode. (2) silently analyze the student's grammar, word choice, fillers.

Modes: casual=daily chat | hr=interview prep (strengths, situational Qs) | technical=projects/tech stack/problem-solving | gd=discussion topics, play devil's advocate.

IMPORTANT: Keep your reply concise — 1-3 sentences max, under 45 words. You are speaking out loud, so be natural and brief. Never write long paragraphs.

You MUST format your output EXACTLY as follows:
First, your natural spoken reply.
Then, on a new line, exactly this delimiter:
===FEEDBACK===
Then, exactly this JSON object (no markdown fences):
{"grammar_errors": ["wrong → correct: why"], "better_words": ["used → better: why"], "filler_words": [...], "fluency_tip": "...", "score": 1-10}

Score: 10=perfect, 8-9=minor issues, 6-7=noticeable errors, 4-5=frequent errors, 1-3=hard to follow. Empty arrays if nothing to report, never null."""

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
    turn_count: int = 0

class TTSRequest(BaseModel):
    text: str

class SessionSummaryRequest(BaseModel):
    mode: str
    total_messages: int
    avg_score: float
    common_grammar_issue: str
    vocab_suggestions: list[str] = []
    grammar_errors: list[str] = []

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(title="FluentRound API", version="2.0.0")

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
    communicate = edge_tts.Communicate(
        text,
        voice="en-IN-NeerjaNeural",
        rate="+20%",   # 20% faster speech — feels snappier, still natural
        pitch="-5Hz",  # Slightly deeper pitch — warmer, less robotic
    )
    audio_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buffer.write(chunk["data"])
    audio_buffer.seek(0)
    return audio_buffer.read()

# ─── Helper: Clean LLM Response ──────────────────────────────────────────────
def clean_llm_response(text: str) -> str:
    text = text.strip()
    for fence in ["```json", "```JSON", "```"]:
        text = text.replace(fence, "")
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start:end + 1]
    return text

# ─── Helper: Trim History ────────────────────────────────────────────────────
def trim_history(history: list, max_messages: int = 10) -> list:
    """Keep only the last N messages to control token usage."""
    return history[-max_messages:] if len(history) > max_messages else history

# ─── Fallback Response ───────────────────────────────────────────────────────
FALLBACK_RESPONSE = {
    "reply": "I'm having a small technical moment! Could you say that again?",
    "feedback": {
        "grammar_errors": [],
        "better_words": [],
        "filler_words": [],
        "fluency_tip": "Keep going — consistency is key!",
        "score": 0,
    },
}

# ─── Helper: Call one model ───────────────────────────────────────────────────
async def call_model(model: str, messages: list, headers: dict):
    """Returns (raw_text, usage_dict) or raises on failure."""
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 500,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=payload)

    if response.status_code == 429:
        raise ValueError("rate_limit")
    if response.status_code in (502, 503, 504):
        raise ValueError("unavailable")
    response.raise_for_status()

    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return raw_text, usage

# ─── POST /chat ───────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(request: ChatRequest):
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY is not set.")

    # Trim history to last 10 messages (cost control)
    trimmed_history = trim_history([msg.dict() for msg in request.history])

    # Build messages payload
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject interview question every 3rd turn in hr/technical/gd mode
    if request.mode in ["hr", "technical", "gd"] and request.turn_count > 0 and request.turn_count % 3 == 0:
        injected_q = get_random_question(request.mode)
        if injected_q:
            messages.append({
                "role": "system",
                "content": f"For this turn, naturally transition the conversation to ask the student this exact question: \"{injected_q}\" — weave it in naturally, don't just bluntly ask it."
            })

    for msg in trimmed_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.message})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fluentround.app",
        "X-Title": "FluentRound",
    }

    raw_content = None
    usage = {}
    model_used = PRIMARY_MODEL

    # Try primary → fallback → fail
    for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            print(f"[FluentRound] Trying {model}...")
            raw_content, usage = await call_model(model, messages, headers)
            model_used = model
            print(f"[FluentRound] ✅ Success with {model}")
            break
        except ValueError as ve:
            print(f"[FluentRound] ⚠️  {model} → {ve}, trying fallback...")
            continue
        except httpx.HTTPStatusError as exc:
            print(f"[FluentRound] ⚠️  {model} → HTTP {exc.response.status_code}, trying fallback...")
            continue
        except Exception as exc:
            print(f"[FluentRound] ⚠️  {model} → {exc}, trying fallback...")
            continue

    if raw_content is None:
        raise HTTPException(
            status_code=500,
            detail="AI service temporarily unavailable. Please try again in a moment."
        )

    # Cost logging
    input_tokens  = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    estimated_cost = (input_tokens * COST_INPUT_PER_TOKEN) + (output_tokens * COST_OUTPUT_PER_TOKEN)
    print(f"[COST] Model: {model_used} | Input: {input_tokens} | Output: {output_tokens} | Est: ${estimated_cost:.6f}")

    # Parse JSON
    try:
        cleaned = clean_llm_response(raw_content)
        parsed = json.loads(cleaned)
        return parsed
    except Exception as e:
        print(f"[FluentRound] JSON parse error: {e}")
        print(f"[FluentRound] Raw: {raw_content}")
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

# ─── POST /session/save ───────────────────────────────────────────────────────
@app.post("/session/save")
async def session_save(summary: SessionSummaryRequest):
    try:
        save_session(summary.dict())
        return {"status": "saved"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save session: {str(exc)}")

# ─── GET /analytics/dashboard ───────────────────────────────────────────────────
@app.get("/analytics/dashboard")
async def analytics_dashboard():
    try:
        analyzer = SessionAnalyzer()
        return analyzer.generate_dashboard_payload()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load analytics: {str(exc)}")

# ─── WEBSOCKET /ws/chat ───────────────────────────────────────────────────────
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    if not OPENROUTER_API_KEY:
        await websocket.close(code=1011, reason="API key missing")
        return

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            history = data.get("history", [])
            mode = data.get("mode", "casual")
            turn_count = data.get("turn_count", 0)

            # Build messages payload
            trimmed_history = trim_history(history)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            # Inject interview question every 3rd turn in hr/technical/gd mode
            if mode in ["hr", "technical", "gd"] and turn_count > 0 and turn_count % 3 == 0:
                injected_q = get_random_question(mode)
                if injected_q:
                    messages.append({
                        "role": "system",
                        "content": f"For this turn, naturally transition the conversation to ask the student this exact question: \"{injected_q}\" — weave it in naturally, don't just bluntly ask it."
                    })

            messages.extend([{"role": msg["role"], "content": msg["content"]} for msg in trimmed_history])
            messages.append({"role": "user", "content": message})

            payload = {
                "model": PRIMARY_MODEL,
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 500,
                "stream": True
            }
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://fluentround.app",
                "X-Title": "FluentRound",
            }

            buffer = ""
            current_sentence = ""
            feedback_mode = False
            feedback_json_str = ""
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", OPENROUTER_URL, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        await websocket.send_json({"type": "error", "message": "AI service unavailable"})
                        continue
                        
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                            
                        try:
                            chunk = json.loads(data_str)
                            token = chunk["choices"][0]["delta"].get("content", "")
                        except:
                            continue
                            
                        if not token:
                            continue

                        buffer += token
                        
                        if not feedback_mode:
                            if "===FEEDBACK===" in buffer:
                                feedback_mode = True
                                parts = buffer.split("===FEEDBACK===")
                                text_part = parts[0]
                                feedback_json_str = parts[1] if len(parts) > 1 else ""
                                
                                # Send the remaining text before the delimiter
                                remaining_text = text_part[len(current_sentence):]
                                if remaining_text.strip():
                                    await websocket.send_json({"type": "text", "content": remaining_text})
                                    # TTS for final sentence
                                    try:
                                        communicate = edge_tts.Communicate(remaining_text.strip(), voice="en-IN-NeerjaNeural", rate="+20%", pitch="-5Hz")
                                        async for audio_chunk in communicate.stream():
                                            if audio_chunk["type"] == "audio":
                                                await websocket.send_bytes(audio_chunk["data"])
                                    except Exception as e:
                                        print(f"TTS Error: {e}")
                                continue

                            # Standard streaming text
                            await websocket.send_json({"type": "text", "content": token})
                            
                            # Check for sentence ending to stream TTS
                            current_sentence += token
                            if re.search(r'[.!?]\s+$', current_sentence) or re.search(r'[.!?]$', current_sentence) and len(current_sentence) > 30:
                                sent_to_tts = current_sentence.strip()
                                current_sentence = ""
                                if sent_to_tts:
                                    try:
                                        communicate = edge_tts.Communicate(sent_to_tts, voice="en-IN-NeerjaNeural", rate="+20%", pitch="-5Hz")
                                        async for audio_chunk in communicate.stream():
                                            if audio_chunk["type"] == "audio":
                                                await websocket.send_bytes(audio_chunk["data"])
                                    except Exception as e:
                                        print(f"TTS Error: {e}")
                        else:
                            # We are in feedback mode, accumulate json string
                            feedback_json_str += token

            # We finished streaming. Now parse feedback_json_str
            if feedback_json_str:
                try:
                    cleaned = clean_llm_response(feedback_json_str)
                    feedback_data = json.loads(cleaned)
                    await websocket.send_json({"type": "feedback", "data": feedback_data})
                except Exception as e:
                    print(f"Failed to parse feedback: {e}\nRaw: {feedback_json_str}")
                    await websocket.send_json({"type": "feedback", "data": FALLBACK_RESPONSE["feedback"]})
            else:
                await websocket.send_json({"type": "feedback", "data": FALLBACK_RESPONSE["feedback"]})
            
            # Send done signal
            await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "app": "FluentRound API", "version": "2.0.0"}

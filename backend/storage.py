"""
FluentRound — storage.py
Simple JSON file-based session persistence for progress tracking.
No database required — reads/writes a local session_data.json file.

NOTE: On Render's free tier, this file resets on every redeploy (no persistent disk).
      This is fine for single-user local use.
"""

import json
import os
from datetime import datetime
from collections import Counter

STORAGE_FILE = os.path.join(os.path.dirname(__file__), "session_data.json")


def load_sessions() -> list:
    """Load all saved sessions from the JSON file."""
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_session(session_summary: dict):
    """Append a new session summary to the JSON file."""
    sessions = load_sessions()
    session_summary["date"] = datetime.now().isoformat()
    sessions.append(session_summary)
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)


def compute_progress() -> dict:
    """
    Compute progress trends from saved sessions.

    Returns:
        sessions:               raw list of all sessions
        total_sessions:         total number of completed sessions
        avg_score_trend:        list of avg scores for the last 10 sessions (oldest→newest)
        most_common_grammar_issue: most frequently seen grammar error keyword
        improvement_note:       human-readable improvement summary
    """
    sessions = load_sessions()

    if not sessions:
        return {
            "sessions": [],
            "total_sessions": 0,
            "avg_score_trend": [],
            "most_common_grammar_issue": None,
            "improvement_note": "No sessions yet. Start practicing to track your progress!",
        }

    # Avg score trend — last 10 sessions
    recent = sessions[-10:]
    avg_score_trend = []
    for s in recent:
        score = s.get("avg_score", 0)
        try:
            avg_score_trend.append(round(float(score), 1))
        except (TypeError, ValueError):
            avg_score_trend.append(0.0)

    # Most common grammar issue across all sessions
    all_errors = []
    for s in sessions:
        errors = s.get("grammar_errors", [])
        for e in errors:
            # Extract the "wrong phrase" part before the arrow
            keyword = e.split("→")[0].strip().lower()
            if keyword:
                all_errors.append(keyword)

    most_common = None
    if all_errors:
        counter = Counter(all_errors)
        most_common = counter.most_common(1)[0][0].capitalize()

    # Improvement note — compare last 5 sessions avg vs previous 5
    improvement_note = "Keep practicing! Consistency is the key to fluency. 🎯"
    if len(avg_score_trend) >= 2:
        oldest = avg_score_trend[0]
        newest = avg_score_trend[-1]
        delta = round(newest - oldest, 1)
        if delta > 0:
            improvement_note = f"🌟 Great progress! Your fluency score improved by {delta} points over your last {len(avg_score_trend)} sessions."
        elif delta < 0:
            improvement_note = f"📉 Your score dipped by {abs(delta)} points recently. Try focusing on the grammar feedback tips!"
        else:
            improvement_note = "Your score is holding steady. Push for that next level! 💪"

    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
        "avg_score_trend": avg_score_trend,
        "most_common_grammar_issue": most_common,
        "improvement_note": improvement_note,
    }

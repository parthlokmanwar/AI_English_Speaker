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




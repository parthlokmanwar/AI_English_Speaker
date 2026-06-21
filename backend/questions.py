"""
FluentRound — questions.py
Curated real interview question bank for HR, Technical, and GD practice modes.
"""

import random

QUESTION_BANK = {
    "hr": [
        "Tell me about yourself.",
        "What are your strengths and weaknesses?",
        "Why should we hire you?",
        "Where do you see yourself in 5 years?",
        "Why do you want to join our company?",
        "Tell me about a time you faced a conflict in a team and how you handled it.",
        "What is your biggest achievement so far?",
        "How do you handle pressure or tight deadlines?",
        "Why did you choose engineering as a career?",
        "What do you know about our company?",
        "Describe a situation where you failed and what you learned from it.",
        "How do you prioritize tasks when you have multiple deadlines?",
    ],
    "technical": [
        "Walk me through one of your major projects.",
        "What was the most challenging technical problem you've solved?",
        "Explain a technical concept from your field to a non-technical person.",
        "What programming languages or tools are you most comfortable with, and why?",
        "Describe your role in a group project — what did you specifically contribute?",
        "How do you approach debugging a problem you've never seen before?",
        "What's a technology you're currently learning, and why?",
        "Explain the difference between two concepts relevant to your branch (e.g. process vs thread, SQL vs NoSQL).",
    ],
    "gd": [
        "Is Artificial Intelligence a threat to jobs in India?",
        "Should engineering colleges focus more on practical skills than theory?",
        "Is remote work more productive than office work?",
        "Should coding be a mandatory subject from school level?",
        "Is social media doing more harm than good to students?",
        "Should there be reservations in private sector jobs?",
        "Is work-life balance a myth in the tech industry?",
    ],
}


def get_random_question(mode: str) -> str | None:
    """Return a random question for the given mode, or None if mode not found."""
    if mode in QUESTION_BANK:
        return random.choice(QUESTION_BANK[mode])
    return None

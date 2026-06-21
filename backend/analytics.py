"""
FluentRound — analytics.py
Modular analytics logic for processing session data and generating dashboard metrics.
"""
from collections import Counter
from storage import load_sessions

class SessionAnalyzer:
    def __init__(self):
        self.sessions = load_sessions()

    def get_total_sessions(self) -> int:
        return len(self.sessions)

    def get_score_trend(self) -> list:
        """Returns avg scores for the last 15 sessions."""
        recent = self.sessions[-15:]
        trend = []
        for s in recent:
            score = s.get("avg_score", 0)
            try:
                trend.append(round(float(score), 1))
            except (TypeError, ValueError):
                trend.append(0.0)
        return trend

    def get_filler_word_stats(self) -> list[dict]:
        """Returns counts of filler words used across all sessions."""
        all_fillers = []
        for s in self.sessions:
            fillers = s.get("filler_words", [])
            all_fillers.extend([f.lower() for f in fillers])
        
        if not all_fillers:
            return []
            
        counter = Counter(all_fillers)
        # Return top 5
        return [{"word": word, "count": count} for word, count in counter.most_common(5)]

    def get_top_grammar_errors(self) -> str:
        """Returns the most frequent grammar error category."""
        all_errors = []
        for s in self.sessions:
            errors = s.get("grammar_errors", [])
            for e in errors:
                # Extract the "wrong phrase" part before the arrow
                keyword = e.split("→")[0].strip().lower()
                if keyword:
                    all_errors.append(keyword)

        if not all_errors:
            return "None detected — great job! 🎉"
            
        counter = Counter(all_errors)
        most_common = counter.most_common(1)[0][0].capitalize()
        return f'"{most_common}" ({counter.most_common(1)[0][1]}× repeated)'

    def get_skill_radar(self) -> dict:
        """Calculates mock radar chart data based on overall progress."""
        if not self.sessions:
            return {"grammar": 0, "vocabulary": 0, "fluency": 0, "confidence": 0}
            
        # Basic heuristic for radar chart
        total = self.get_total_sessions()
        recent_scores = self.get_score_trend()[-5:]
        avg_recent = sum(recent_scores) / len(recent_scores) if recent_scores else 0
        
        # Calculate heuristics
        grammar = min(100, 50 + (avg_recent * 5) - len(self.get_top_grammar_errors()) * 2)
        vocab = min(100, 40 + (total * 2) + (avg_recent * 4))
        fluency = min(100, 45 + (avg_recent * 5) - len(self.get_filler_word_stats()) * 3)
        confidence = min(100, 50 + (total * 3))
        
        return {
            "grammar": max(10, int(grammar)),
            "vocabulary": max(10, int(vocab)),
            "fluency": max(10, int(fluency)),
            "confidence": max(10, int(confidence))
        }

    def generate_dashboard_payload(self) -> dict:
        """Assembles all metrics for the frontend dashboard."""
        trend = self.get_score_trend()
        
        # Improvement note
        improvement_note = "Keep practicing! Consistency is the key to fluency. 🎯"
        if len(trend) >= 2:
            oldest = trend[0]
            newest = trend[-1]
            delta = round(newest - oldest, 1)
            if delta > 0:
                improvement_note = f"🌟 Great progress! Your fluency score improved by {delta} points over your last {len(trend)} sessions."
            elif delta < 0:
                improvement_note = f"📉 Your score dipped by {abs(delta)} points recently. Try focusing on the grammar feedback tips!"
            else:
                improvement_note = "Your score is holding steady. Push for that next level! 💪"

        return {
            "total_sessions": self.get_total_sessions(),
            "score_trend": trend,
            "filler_stats": self.get_filler_word_stats(),
            "most_common_error": self.get_top_grammar_errors(),
            "skill_radar": self.get_skill_radar(),
            "improvement_note": improvement_note,
            "sessions": self.sessions # Recent sessions still needed for the list
        }

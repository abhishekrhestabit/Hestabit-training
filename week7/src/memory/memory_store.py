import json
import os
from datetime import datetime

class MemoryStore:
    def __init__(self, filepath="CHAT-LOGS.json", max_history=5):
        self.filepath = filepath
        self.max_history = max_history
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w') as f:
                json.dump([], f)

    def _load_history(self) -> list:
        with open(self.filepath, 'r') as f:
            return json.load(f)

    def get_history(self, chat_pairs: int = None) -> list:
        history = self._load_history()
        if chat_pairs is None:
            chat_pairs = self.max_history
        return history[-(chat_pairs * 2):]

    def add_interaction(self, user_query: str, ai_response: str, metadata: dict = None, endpoint: str = ""):
        history = self._load_history()
        ts = datetime.now().isoformat()
        entry_user = {"role": "user", "content": user_query, "timestamp": ts, "endpoint": endpoint}
        entry_asst = {"role": "assistant", "content": ai_response, "timestamp": ts, "endpoint": endpoint}
        if metadata:
            entry_asst["metadata"] = metadata
        history.extend([entry_user, entry_asst])
        history = history[-(self.max_history * 2):]
        with open(self.filepath, 'w') as f:
            json.dump(history, f, indent=2)

    def format_history_for_prompt(self, chat_pairs: int = None) -> str:
        history = self.get_history(chat_pairs=chat_pairs)
        if not history:
            return "No previous conversation."
        return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)

    def log_feedback(self, rating: int, comment: str = ""):
        history = self._load_history()
        for entry in reversed(history):
            if entry["role"] == "assistant":
                entry["human_feedback"] = {
                    "rating": rating,
                    "comment": comment,
                    "timestamp": datetime.now().isoformat()
                }
                break
        with open(self.filepath, 'w') as f:
            json.dump(history, f, indent=2)

    def clear(self):
        with open(self.filepath, 'w') as f:
            json.dump([], f)
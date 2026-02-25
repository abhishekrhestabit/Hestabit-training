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

    def get_history(self) -> list:
        with open(self.filepath, 'r') as f:
            history = json.load(f)
        return history[-(self.max_history * 2):]

    def add_interaction(self, user_query: str, ai_response: str, metadata: dict = None):
        with open(self.filepath, 'r') as f:
            history = json.load(f)
        ts = datetime.now().isoformat()
        entry_user = {"role": "user", "content": user_query, "timestamp": ts}
        entry_asst = {"role": "assistant", "content": ai_response, "timestamp": ts}
        if metadata:
            entry_asst["metadata"] = metadata
        history.extend([entry_user, entry_asst])
        history = history[-(self.max_history * 2):]
        with open(self.filepath, 'w') as f:
            json.dump(history, f, indent=2)

    def format_history_for_prompt(self) -> str:
        history = self.get_history()
        if not history:
            return "No previous conversation."
        return "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)

    def clear(self):
        with open(self.filepath, 'w') as f:
            json.dump([], f)
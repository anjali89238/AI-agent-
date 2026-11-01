import threading
from collections import defaultdict, deque

MAX_TURNS_PER_SESSION = 20


class HistoryStore:
    """Keeps a short rolling conversation history per session id."""

    def __init__(self, max_turns: int = MAX_TURNS_PER_SESSION) -> None:
        self._sessions: dict[str, deque[tuple[str, str]]] = defaultdict(
            lambda: deque(maxlen=max_turns * 2)
        )
        self._lock = threading.Lock()

    def append(self, session_id: str, role: str, text: str) -> None:
        with self._lock:
            self._sessions[session_id].append((role, text))

    def get(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            turns = list(self._sessions.get(session_id, ()))

        return [
            {"role": "user" if role == "user" else "assistant", "content": text}
            for role, text in turns
        ]

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

from __future__ import annotations

from fastapi import UploadFile

from . import config, groq_client
from .history import HistoryStore
from .realestate import PropertyKnowledgeBase


class RealEstateChatbot:
    """Class-based real-estate assistant that combines Groq with local knowledge."""

    def __init__(
        self,
        history: HistoryStore | None = None,
        knowledge: PropertyKnowledgeBase | None = None,
    ) -> None:
        self.history = history or HistoryStore()
        self.knowledge = knowledge or PropertyKnowledgeBase()

    def system_instruction(self, message: str) -> str:
        reference = self.knowledge.context_for(message)
        return f"{config.SYSTEM_PROMPT}\n\n{reference}"

    async def answer_text(self, message: str, session_id: str) -> str:
        answer = await groq_client.ask_text(
            message,
            self.history.get(session_id),
            self.system_instruction(message),
        )
        self.history.append(session_id, "user", message)
        self.history.append(session_id, "model", answer)
        return answer

    async def answer_image(self, message: str, upload: UploadFile, session_id: str) -> str:
        prompt = message.strip() or "Describe this property image in detail."
        answer = await groq_client.ask_about_image(
            message,
            upload,
            self.history.get(session_id),
            self.system_instruction(prompt),
        )
        self.history.append(session_id, "user", f"[image] {prompt}")
        self.history.append(session_id, "model", answer)
        return answer

    async def answer_audio(
        self, message: str, upload: UploadFile, session_id: str
    ) -> tuple[str, str]:
        transcript, answer = await groq_client.ask_about_audio(
            message,
            upload,
            self.history.get(session_id),
            self.system_instruction(message or "property question"),
        )
        self.history.append(session_id, "user", transcript)
        self.history.append(session_id, "model", answer)
        return transcript, answer

    def reset(self, session_id: str) -> None:
        self.history.reset(session_id)

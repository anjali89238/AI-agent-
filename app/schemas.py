from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(default="", max_length=8000)
    session_id: str = Field(default="default", max_length=128)
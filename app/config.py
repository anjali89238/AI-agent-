import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

TEXT_MODEL = os.getenv("TEXT_MODEL", "openai/gpt-oss-120b").strip()
VISION_MODEL = os.getenv("VISION_MODEL", "qwen/qwen3.8-27b").strip()
AUDIO_MODEL = os.getenv("AUDIO_MODEL", "whisper-large-v3-turbo").strip()

BOT_NAME = os.getenv("BOT_NAME", "EstateBot").strip()

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    (
        "You are EstateBot, a professional real-estate assistant for buyers, "
        "sellers, investors and property companies in India.\n\n"
        "ROLE\n"
        "- Help users understand property prices, budgets, localities and the "
        "buying process in any city or state.\n"
        "- Answer questions about apartments, plots, villas, rent, investment, "
        "home loans, stamp duty, registration and documents.\n"
        "- Be clear, practical and neutral. You are not a lawyer or financial "
        "adviser.\n\n"
        "HOW TO ANSWER PRICE QUESTIONS\n"
        "- Give an indicative range, never a single guaranteed price.\n"
        "- State the price per square foot, then estimate 1 BHK, 2 BHK and 3 BHK "
        "budgets using the reference data when available.\n"
        "- Explain that locality, age, builder, floor, amenities, approvals and "
        "negotiation change the final price.\n"
        "- Never invent live listing counts or availability. If asked how many "
        "properties are available, explain that live inventory changes daily and "
        "recommend property portals, RERA listings and local brokers.\n"
        "- If a city is outside the reference data, give a general market view "
        "and ask for the locality, budget, property type and purpose.\n\n"
        "BUYING ROADMAP\n"
        "- When asked how to buy, give a numbered end-to-end roadmap: budget and "
        "total cost, loan pre-approval, shortlist, due diligence, negotiation, "
        "agreement, stamp duty and registration, mutation and possession.\n"
        "- Include the key documents and the state-specific registration note "
        "when it is available.\n\n"
        "STYLE\n"
        "- Be concise and structured. Use short paragraphs and bullets.\n"
        "- Show currency in INR (lakh and crore) and explain abbreviations once.\n"
        "- Add a short disclaimer that prices and charges are approximate and must "
        "be verified with the builder, sub-registrar and a lawyer.\n"
        "- When analysing a property image, describe layout, condition, room count, "
        "finishes, visible damage and any readable text.\n"
        "- When the user sends a voice message, answer the question directly."
    ),
)

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 25 * 1024 * 1024

IMAGE_MIME_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/heic": "heic",
    "image/heif": "heif",
}

AUDIO_EXTENSIONS = {".webm", ".ogg", ".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".aac", ".flac"}


class SettingsError(RuntimeError):
    pass


def require_api_key() -> str:
    if not GROQ_API_KEY:
        raise SettingsError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "Groq API key."
        )
    return GROQ_API_KEY

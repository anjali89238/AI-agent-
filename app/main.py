import logging
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from . import groq_client
from .chatbot import RealEstateChatbot
from .groq_client import UpstreamError
from .history import HistoryStore
from .schemas import ChatRequest

logger = logging.getLogger("ai_agent")

app = FastAPI(title="Real Estate AI Assistant", version="1.0.0")
history = HistoryStore()
chatbot = RealEstateChatbot(history)


QUOTA_TTL_SECONDS = 300
_quota_cache: dict | None = None
_quota_checked_at: float = 0.0


def _quota_status() -> dict:
    """Result of a live API probe, cached so /api/health stays fast."""
    global _quota_cache, _quota_checked_at

    now = time.monotonic()
    if _quota_cache is not None and (now - _quota_checked_at) < QUOTA_TTL_SECONDS:
        return _quota_cache

    if not config.GROQ_API_KEY:
        _quota_cache = {"ok": True, "reset_hint": "", "message": ""}
    else:
        try:
            groq_client.probe(config.TEXT_MODEL)
            _quota_cache = {"ok": True, "reset_hint": "", "message": ""}
        except UpstreamError as exc:
            _quota_cache = {"ok": False, "reset_hint": "", "message": str(exc)}
        except Exception:  # noqa: BLE001 - never break health
            _quota_cache = {"ok": True, "reset_hint": "", "message": ""}

    _quota_checked_at = now
    return _quota_cache


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_key_configured": bool(config.GROQ_API_KEY),
        "text_model": config.TEXT_MODEL,
        "name": config.BOT_NAME,
        "quota": _quota_status(),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    try:
        answer = await chatbot.answer_text(request.message, request.session_id)
    except config.SettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UpstreamError as exc:
        logger.warning("upstream unavailable: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface upstream errors to the UI
        logger.exception("chat failed")
        raise HTTPException(status_code=502, detail=f"Groq request failed: {exc}") from exc

    return {"answer": answer, "session_id": request.session_id}


@app.post("/api/chat/image")
async def chat_image(
    message: str = Form(default=""),
    session_id: str = Form(default="default"),
    image: UploadFile = File(...),
) -> dict:
    try:
        answer = await chatbot.answer_image(message, image, session_id)
    except config.SettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        raise
    except UpstreamError as exc:
        logger.warning("upstream unavailable: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("image chat failed")
        raise HTTPException(status_code=502, detail=f"Image analysis failed: {exc}") from exc
    finally:
        await image.close()

    return {"answer": answer, "session_id": session_id}


@app.post("/api/chat/audio")
async def chat_audio(
    message: str = Form(default=""),
    session_id: str = Form(default="default"),
    audio: UploadFile = File(...),
) -> dict:
    try:
        transcript, answer = await chatbot.answer_audio(message, audio, session_id)
    except config.SettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except HTTPException:
        raise
    except UpstreamError as exc:
        logger.warning("upstream unavailable: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("audio chat failed")
        raise HTTPException(status_code=502, detail=f"Audio processing failed: {exc}") from exc
    finally:
        await audio.close()

    return {"transcript": transcript, "answer": answer, "session_id": session_id}


@app.post("/api/reset")
async def reset(session_id: str = Form(default="default")) -> dict:
    chatbot.reset(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.BASE_DIR / "static" / "index.html")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, detail="Something went wrong on the server.")


app.mount("/static", StaticFiles(directory=config.BASE_DIR / "static"), name="static")
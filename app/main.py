import logging
import time

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from . import gemini
from .gemini import UpstreamError, ask_about_audio, ask_about_image, ask_text
from .history import HistoryStore
from .schemas import ChatRequest

logger = logging.getLogger("ai_agent")

app = FastAPI(title="AI Agent", version="1.0.0")
history = HistoryStore()


QUOTA_TTL_SECONDS = 300
_quota_cache: dict | None = None
_quota_checked_at: float = 0.0


def _quota_status() -> dict:
    """Result of a live API probe, cached so /api/health stays fast."""
    global _quota_cache, _quota_checked_at

    now = time.monotonic()
    if _quota_cache is not None and (now - _quota_checked_at) < QUOTA_TTL_SECONDS:
        return _quota_cache

    if not config.GOOGLE_API_KEY:
        _quota_cache = {"ok": True, "reset_hint": "", "message": ""}
    else:
        try:
            gemini.probe(config.TEXT_MODEL)
            _quota_cache = {"ok": True, "reset_hint": "", "message": ""}
        except gemini.UpstreamError as exc:
            _quota_cache = {"ok": False, "reset_hint": "", "message": str(exc)}
        except Exception:  # noqa: BLE001 - never break health
            _quota_cache = {"ok": True, "reset_hint": "", "message": ""}

    _quota_checked_at = now
    return _quota_cache


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "api_key_configured": bool(config.GOOGLE_API_KEY),
        "text_model": config.TEXT_MODEL,
        "name": "Shuru",
        "quota": _quota_status(),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    try:
        answer = await ask_text(request.message, history.get(request.session_id))
    except config.SettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except UpstreamError as exc:
        logger.warning("upstream unavailable: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - surface upstream errors to the UI
        logger.exception("chat failed")
        raise HTTPException(status_code=502, detail=f"Google AI request failed: {exc}") from exc

    history.append(request.session_id, "user", request.message)
    history.append(request.session_id, "model", answer)
    return {"answer": answer, "session_id": request.session_id}


@app.post("/api/chat/image")
async def chat_image(
    message: str = Form(default=""),
    session_id: str = Form(default="default"),
    image: UploadFile = File(...),
) -> dict:
    try:
        answer = await ask_about_image(message, image, history.get(session_id))
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

    prompt = message.strip() or "Describe this image in detail."
    history.append(session_id, "user", f"[image] {prompt}")
    history.append(session_id, "model", answer)
    return {"answer": answer, "session_id": session_id}


@app.post("/api/chat/audio")
async def chat_audio(
    message: str = Form(default=""),
    session_id: str = Form(default="default"),
    audio: UploadFile = File(...),
) -> dict:
    try:
        transcript, answer = await ask_about_audio(message, audio, history.get(session_id))
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

    history.append(session_id, "user", transcript)
    history.append(session_id, "model", answer)
    return {"transcript": transcript, "answer": answer, "session_id": session_id}


@app.post("/api/reset")
async def reset(session_id: str = Form(default="default")) -> dict:
    history.reset(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.BASE_DIR / "static" / "index.html")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, detail="Something went wrong on the server.")


app.mount("/static", StaticFiles(directory=config.BASE_DIR / "static"), name="static")
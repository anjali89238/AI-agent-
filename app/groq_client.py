import asyncio
import base64
import mimetypes
import time

from fastapi import HTTPException, UploadFile
from groq import Groq

from . import config

MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 1.5
RATE_LIMIT_BACKOFF = 6.0
MAX_OUTPUT_TOKENS = 2048


class UpstreamError(RuntimeError):
    """Raised when Groq cannot be reached or returns an error."""


def client() -> Groq:
    return Groq(api_key=config.require_api_key(), max_retries=0)


def _status_code(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_transient(exc: Exception) -> bool:
    """Network blips, timeouts, rate limits and server errors are worth retrying."""
    status = _status_code(exc)
    if status in {408, 409, 429, 500, 502, 503, 504}:
        return True
    if status is not None:
        return False

    text = str(exc).lower()
    if any(
        token in text
        for token in (
            "invalid api key",
            "api key not valid",
            "permission denied",
            "not found",
            "unsupported",
            "invalid argument",
            "400",
            "401",
            "403",
            "404",
        )
    ):
        return False

    name = type(exc).__name__.lower()
    if any(
        token in name
        for token in ("connection", "timeout", "temporaryfailure")
    ):
        return True

    return any(
        token in text
        for token in (
            "getaddrinfo failed",
            "failed to resolve",
            "max retries exceeded",
            "timed out",
            "connection aborted",
            "connection reset",
            "429",
            "500",
            "502",
            "503",
            "504",
            "unavailable",
            "overloaded",
            "rate limit",
        )
    )


def _retry_after(exc: Exception) -> float | None:
    """Honour a Retry-After header when the API provides one."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    value = headers.get("Retry-After") or headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return None


def _is_rate_limited(exc: Exception) -> bool:
    return _status_code(exc) == 429 or "rate limit" in str(exc).lower()


def _chat(
    model: str,
    messages: list[dict],
    system_instruction: str | None = None,
    attempts: int = MAX_ATTEMPTS,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    payload: list[dict] = []
    if system_instruction:
        payload.append({"role": "system", "content": system_instruction})
    payload.extend(messages)

    api = client()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = api.chat.completions.create(
                model=model,
                messages=payload,
                temperature=0.6,
                max_completion_tokens=max_tokens,
                reasoning_effort="low",
            )
            content = response.choices[0].message.content or ""
            return content.strip()
        except Exception as exc:  # noqa: BLE001 - normalised below
            last_error = exc
            if attempt == attempts or not _is_transient(exc):
                break

            base = RATE_LIMIT_BACKOFF if _is_rate_limited(exc) else BACKOFF_SECONDS
            delay = _retry_after(exc)
            if delay is None:
                delay = base * attempt
            time.sleep(min(delay, 30.0))

    raise UpstreamError(_friendly(last_error)) from last_error


def _friendly(exc: Exception | None) -> str:
    text = str(exc or "")
    lowered = text.lower()
    status = _status_code(exc) if exc else None

    if status == 429 or "rate limit" in lowered or "too many requests" in lowered:
        return "Groq is rate-limiting requests right now. Please wait a moment and try again."
    if status in {401, 403} or "api key" in lowered or "authentication" in lowered:
        return "Your Groq API key was rejected. Check GROQ_API_KEY in your .env file."
    if status == 404 or "model" in lowered and "not found" in lowered:
        return (
            "The configured Groq model was not found. Update the model names in "
            "your .env file and restart the server."
        )
    if status == 413 or "too large" in lowered:
        return "The uploaded file is too large for Groq. Please use a smaller file."
    if status == 503 or "unavailable" in lowered or "overloaded" in lowered:
        return "Groq is temporarily unavailable. Please try again in a few seconds."
    if "getaddrinfo failed" in lowered or "failed to resolve" in lowered:
        return (
            "Could not reach Groq's servers - your internet or DNS connection "
            "dropped. Please check your network and try again."
        )
    if "timed out" in lowered or "timeout" in lowered or "max retries exceeded" in lowered:
        return "The request to Groq timed out. Please check your connection and try again."
    if exc is not None:
        return f"Groq request failed: {exc}"
    return "Groq request failed for an unknown reason."


async def _read(upload: UploadFile, limit: int, label: str) -> bytes:
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=400, detail=f"The uploaded {label} is empty.")
    if len(data) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"The {label} is too large (max {limit // (1024 * 1024)} MB).",
        )
    return data


def _image_mime(upload: UploadFile) -> str:
    mime = (upload.content_type or "").lower().split(";")[0]
    if mime not in config.IMAGE_MIME_TYPES:
        mime = mimetypes.guess_type(upload.filename or "")[0] or "image/jpeg"
        if mime not in config.IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported image type '{mime}'. Use PNG, JPEG, WEBP or GIF.",
            )
    return mime


def _image_content(prompt: str, upload: UploadFile, data: bytes) -> list[dict]:
    mime = _image_mime(upload)
    encoded = base64.b64encode(data).decode("ascii")
    return [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{encoded}"},
        },
    ]


def _audio_mime(upload: UploadFile) -> str:
    mime = (upload.content_type or "").lower().split(";")[0]
    if not mime.startswith("audio/") and not mime.startswith("video/"):
        guess = mimetypes.guess_type(upload.filename or "")[0]
        mime = (
            guess
            if guess and (guess.startswith("audio/") or guess.startswith("video/"))
            else "audio/webm"
        )
    return mime


def _transcribe(upload: UploadFile, data: bytes) -> str:
    mime = _audio_mime(upload)
    filename = upload.filename or f"voice{mimetypes.guess_extension(mime) or '.webm'}"

    api = client()
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            result = api.audio.transcriptions.create(
                model=config.AUDIO_MODEL,
                file=(filename, data, mime),
                response_format="text",
            )
            if isinstance(result, str):
                return result.strip()
            return (getattr(result, "text", "") or "").strip()
        except Exception as exc:  # noqa: BLE001 - normalised below
            last_error = exc
            if attempt == MAX_ATTEMPTS or not _is_transient(exc):
                break

            base = RATE_LIMIT_BACKOFF if _is_rate_limited(exc) else BACKOFF_SECONDS
            delay = _retry_after(exc)
            if delay is None:
                delay = base * attempt
            time.sleep(min(delay, 30.0))

    raise UpstreamError(_friendly(last_error)) from last_error


def probe(model: str) -> str:
    """Cheap, single-attempt call so /api/health stays fast."""
    return _chat(
        model,
        [{"role": "user", "content": "Reply with OK."}],
        attempts=1,
        max_tokens=64,
    )


async def ask_text(
    message: str,
    history: list[dict],
    system_instruction: str | None = None,
) -> str:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    messages = list(history) + [{"role": "user", "content": message}]
    answer = await asyncio.to_thread(
        _chat,
        config.TEXT_MODEL,
        messages,
        system_instruction or config.SYSTEM_PROMPT,
    )
    return answer or "I could not generate a response. Please try again."


async def ask_about_image(
    message: str,
    upload: UploadFile,
    history: list[dict],
    system_instruction: str | None = None,
) -> str:
    data = await _read(upload, config.MAX_IMAGE_BYTES, "image")
    prompt = message.strip() or "Describe this property image in detail."

    messages = list(history) + [
        {"role": "user", "content": _image_content(prompt, upload, data)}
    ]
    answer = await asyncio.to_thread(
        _chat,
        config.VISION_MODEL,
        messages,
        system_instruction or config.SYSTEM_PROMPT,
    )
    return answer or "I could not analyse that image. Please try again."


async def ask_about_audio(
    message: str,
    upload: UploadFile,
    history: list[dict],
    system_instruction: str | None = None,
) -> tuple[str, str]:
    data = await _read(upload, config.MAX_AUDIO_BYTES, "audio file")
    transcript = await asyncio.to_thread(_transcribe, upload, data)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="No speech was detected in that recording. Please try again.",
        )

    follow_up = message.strip() or "Answer the property question in this voice message."
    messages = list(history) + [
        {
            "role": "user",
            "content": f"Voice message transcript:\n{transcript}\n\nUser instruction: {follow_up}",
        }
    ]
    answer = await asyncio.to_thread(
        _chat,
        config.TEXT_MODEL,
        messages,
        system_instruction or config.SYSTEM_PROMPT,
    )
    return transcript, answer or "I could not generate a response. Please try again."


def encode_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

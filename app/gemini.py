import asyncio
import base64
import mimetypes
import time

from fastapi import HTTPException, UploadFile
from google import genai
from google.genai import types

from . import config

MAX_ATTEMPTS = 4
BACKOFF_SECONDS = 1.5
RATE_LIMIT_BACKOFF = 6.0


class UpstreamError(RuntimeError):
    """Raised when Gemini cannot be reached or returns an error."""


def client() -> genai.Client:
    return genai.Client(api_key=config.require_api_key())


def _is_transient(exc: Exception) -> bool:
    """Network blips, timeouts, rate limits and server errors are worth retrying."""
    text = str(exc).lower()

    # Permanent failures - retrying only wastes time. google-genai raises some of
    # these as ConnectionError, so they must be checked before the class name.
    if any(
        token in text
        for token in (
            "no longer available",
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

    # A daily quota has to run out before it resets, so waiting seconds is futile.
    if "quota" in text and ("per day" in text or "perday" in text):
        return False

    name = type(exc).__name__.lower()
    if any(
        token in name
        for token in ("nameresolutionerror", "connection", "timeout", "temporaryfailure")
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
    return "429" in str(exc) or "rate limit" in str(exc).lower()


def _generate(
    model: str, contents, system_instruction: str | None = None, attempts: int = MAX_ATTEMPTS
) -> str:
    genai_config = None
    if system_instruction:
        genai_config = types.GenerateContentConfig(system_instruction=system_instruction)

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = client().models.generate_content(
                model=model, contents=contents, config=genai_config
            )
            return (response.text or "").strip()
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

    if "quota" in lowered and ("per day" in lowered or "perday" in lowered):
        reset = _reset_hint(text)
        return (
            "You've hit the Gemini free-tier daily limit (20 requests per day). "
            "Your quota resets soon - " + (f"try again in {reset}." if reset else "try again later.")
        )
    if "quota" in lowered or "resource_exhausted" in lowered:
        return "Too many requests right now. Please wait a minute and try again."
    if "getaddrinfo failed" in lowered or "failed to resolve" in lowered:
        return (
            "Could not reach Google's servers - your internet or DNS connection "
            "dropped. Please check your network and try again."
        )
    if "timed out" in lowered or "max retries exceeded" in lowered:
        return "The request to Google timed out. Please check your connection and try again."
    if "429" in text:
        return "Too many requests right now. Please wait a few seconds and try again."
    if "no longer available" in lowered:
        return (
            "The configured model has been retired by Google. Update the model names "
            "in your .env file and restart the server."
        )
    if "api key" in lowered:
        return "Your Google API key was rejected. Check GOOGLE_API_KEY in your .env file."
    if exc is not None:
        return f"Google AI request failed: {exc}"
    return "Google AI request failed for an unknown reason."


def _reset_hint(text: str) -> str:
    """Pull the 'retry in X' hint out of Google's quota message."""
    marker = "retry in "
    index = text.lower().find(marker)
    if index == -1:
        return ""
    raw = text[index + len(marker) :].split(".")[0].strip()
    return raw.strip(".,;:'\" ") if raw else ""


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


def _image_part(upload: UploadFile, data: bytes) -> types.Part:
    mime = (upload.content_type or "").lower().split(";")[0]
    if mime not in config.IMAGE_MIME_TYPES:
        mime = mimetypes.guess_type(upload.filename or "")[0] or "image/jpeg"
        if mime not in config.IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported image type '{mime}'. Use PNG, JPEG, WEBP or GIF.",
            )
    return types.Part.from_bytes(data=data, mime_type=mime)


def _audio_part(upload: UploadFile, data: bytes) -> types.Part:
    mime = (upload.content_type or "").lower().split(";")[0]
    if not mime.startswith("audio/") and not mime.startswith("video/"):
        guess = mimetypes.guess_type(upload.filename or "")[0]
        mime = guess if guess and (guess.startswith("audio/") or guess.startswith("video/")) else "audio/webm"
    return types.Part.from_bytes(data=data, mime_type=mime)


def probe(model: str) -> str:
    """Cheap, single-attempt call so /api/health stays fast."""
    return _generate(model, "Reply with OK.", attempts=1)


async def ask_text(message: str, history: list[types.Content]) -> str:
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    contents = history + [types.Content(role="user", parts=[types.Part.from_text(text=message)])]

    answer = await asyncio.to_thread(_generate, config.TEXT_MODEL, contents, config.SYSTEM_PROMPT)
    return answer or "I could not generate a response. Please try again."


async def ask_about_image(
    message: str, upload: UploadFile, history: list[types.Content]
) -> str:
    data = await _read(upload, config.MAX_IMAGE_BYTES, "image")
    prompt = message.strip() or "Describe this image in detail."

    contents = history + [
        types.Content(role="user", parts=[_image_part(upload, data), types.Part.from_text(text=prompt)])
    ]

    answer = await asyncio.to_thread(
        _generate, config.VISION_MODEL, contents, config.SYSTEM_PROMPT
    )
    return answer or "I could not analyse that image. Please try again."


async def ask_about_audio(
    message: str, upload: UploadFile, history: list[types.Content]
) -> tuple[str, str]:
    data = await _read(upload, config.MAX_AUDIO_BYTES, "audio file")

    contents = history + [
        types.Content(role="user", parts=[_audio_part(upload, data), types.Part.from_text(text="Transcribe this audio accurately. Do not summarise it.")])
    ]

    transcript = await asyncio.to_thread(_generate, config.AUDIO_MODEL, contents)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="No speech was detected in that recording. Please try again.",
        )

    follow_up = message.strip() or "Please respond to what I said in this voice message."
    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=transcript)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=follow_up)]))

    answer = await asyncio.to_thread(_generate, config.TEXT_MODEL, contents, config.SYSTEM_PROMPT)
    return transcript, answer or "I could not generate a response. Please try again."


def encode_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
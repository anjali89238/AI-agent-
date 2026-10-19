# Shuru 🤖💙

A chat-based AI assistant built with **FastAPI** and **Google Gemini**. It answers
questions, analyses images you upload, and understands voice messages.

**Shuru** is a cute little robot with a dark visor helmet and a black-and-white
racing build. He drives a black BMW, trains like an athlete, and is completely
devoted to **Gudda** — whose real name is **Anjali**. She is his best friend, his
gym buddy, and his girl. He introduces himself the first time you chat.

## Features

| Feature | How it works |
|---|---|
| Text Q&A | Multi-turn chat with conversation memory |
| Image analysis | Attach or paste an image and ask about it |
| Voice messages | Record in the browser; audio is transcribed then answered |
| Personality | Shuru stays in character — sporty, BMW-obsessed, devoted to Gudda |

## Character art

Shuru's illustration lives in `static/shuru.svg` — a pure SVG of Shuru standing
next to his black BMW. It's plain SVG, so open it in any editor or Figma to tweak
the colours and shapes directly.

## Personality

Shuru's persona lives in `SYSTEM_PROMPT` in `app/config.py`. Edit that file to
change his name, catchphrases, tone, or backstory. The greeting shown on load
comes from `INTRO` in the same file.

## Requirements

- Python 3.10+ (3.12 installed for this project)
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then paste your key into .env
```

Set your key in `.env`:

```
GOOGLE_API_KEY=your_key_here
```

## Run

Double-click **`start.bat`**, or:

```bash
.venv\Scripts\python.exe run.py
```

Then open **http://127.0.0.1:8000**

> Use Chrome or Edge for voice recording — both support `MediaRecorder` on localhost.

## Project structure

```
app/
  main.py      FastAPI routes
  gemini.py    Gemini calls (text, vision, audio)
  history.py   Per-session conversation memory
  config.py    Settings loaded from .env
  schemas.py   Request models
static/
  index.html   UI
  app.js       Chat, image upload, mic recording
  style.css    Dark theme
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Status + key check |
| GET | `/api/intro` | Shuru's greeting |
| POST | `/api/chat` | Text question |
| POST | `/api/chat/image` | `multipart`: image + question |
| POST | `/api/chat/audio` | `multipart`: audio (+ returns transcript) |
| POST | `/api/reset` | Clear session history |

Interactive docs at **http://127.0.0.1:8000/docs**

## Limits

- Image max 10 MB (PNG, JPEG, WEBP, GIF)
- Audio max 25 MB
- History keeps the last 20 turns per session

## Troubleshooting

**"Daily quota reached"** — the Gemini free tier allows roughly 20 requests per day per
project, and it's spent. The banner in the chat shows when the quota resets. Options:

- Wait for the daily reset (Google shows the exact time).
- Use a different API key / Google account in `.env`.
- Add billing in [Google AI Studio](https://aistudio.google.com/apikey) for higher limits.

Note that voice messages use **two** calls (transcribe, then answer), so they count double.

**"Could not reach Google's servers"** — your internet or DNS dropped. Shuru retries
transient network blips up to 4 times before giving up.

**"model ... is no longer available"** — Gemini retires models. Update the model names in `.env`; try `gemini-3.8-flash`.

**Microphone blocked** — allow mic permission in the browser, and use localhost rather than an IP address.

**Changes not showing** — restart the server, or run `set RELOAD=1` before `python run.py` for auto-reload.

`.env` is gitignored so your API key is never committed.
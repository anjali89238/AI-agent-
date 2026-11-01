# EstateBot

A simple class-based Python chatbot for real-estate companies, built with
**FastAPI** and **Groq**. It answers property questions for cities and states in
India, gives indicative price ranges, and explains the full property buying
roadmap.

## What it does

| Feature | How it works |
|---|---|
| Property prices | Gives approximate price per sq ft and 1/2/3 BHK budgets by city |
| Buying roadmap | Numbered steps from budget and loan approval to registration and possession |
| State rules | Stamp duty, registration and portal notes for major states |
| Text Q&A | Multi-turn chat with conversation memory |
| Image analysis | Upload a property photo and ask about layout, condition or visible details |
| Voice messages | Record in the browser; the audio is transcribed and answered |
| Unknown cities | Falls back to general market guidance and asks for locality and budget |

Prices are broad, time-sensitive market ranges, not live listings or guaranteed
quotes. The bot is instructed to say this and to recommend checking RERA records,
property portals, the sub-registrar and a lawyer.

## Code structure

The chatbot is built with a class and constructor:

```python
class RealEstateChatbot:
    def __init__(self, history=None, knowledge=None):
        self.history = history or HistoryStore()
        self.knowledge = knowledge or PropertyKnowledgeBase()

    def system_instruction(self, message): ...
    async def answer_text(self, message, session_id): ...
    async def answer_image(self, message, upload, session_id): ...
    async def answer_audio(self, message, upload, session_id): ...
    def reset(self, session_id): ...
```

`PropertyKnowledgeBase` in `app/realestate.py` holds the city price ranges,
state notes, buying roadmap and helper functions such as `format_inr`,
`market_summary`, `roadmap_text` and `context_for`. Extend it with your own
company data using `add_city(CityMarket(...))` and `add_state_note(state, note)`.

## Requirements

- Python 3.10+ (3.12 installed for this project)
- A free Groq API key from [Groq Console](https://console.groq.com/keys)

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # then paste your key into .env
```

Set your key in `.env`:

```
GROQ_API_KEY=your_key_here
```

Default models:

- Text: `openai/gpt-oss-120b`
- Vision: `qwen/qwen3.8-27b`
- Audio: `whisper-large-v3-turbo`

## Run

Double-click **`start.bat`**, or:

```bash
venv\Scripts\python.exe run.py
```

Then open **http://127.0.0.1:8000**

> Use Chrome or Edge for voice recording, because both support `MediaRecorder` on localhost.

## Using this project on another system

Yes. Clone the repo on the other machine and create a local `.env`:

```bash
git clone <your-repo-url>
cd AI-agent
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Then open `.env` and set `GROQ_API_KEY=your_key_here`. The same key works on
another system, but it is safer to create a separate key per machine or project
so one key can be revoked without affecting the others.

Never send `.env` through chat, email, screenshots or Git. It stays local to each
machine.

## API key security

- `.env` is gitignored and must never be committed.
- `.env.example` is safe to commit and contains an empty `GROQ_API_KEY=`.
- The key is used only by the FastAPI backend; the browser never receives it.
- If a key is ever exposed, revoke it in Groq Console and create a new one.
- On a hosting provider, set `GROQ_API_KEY` as a server-side environment
  variable instead of uploading `.env`.

## Sharing with teachers

The API key must never be published on GitHub.

**Option 1 - teachers run it locally (free):**

1. Open your GitHub repository or download the ZIP.
2. Follow the Setup section above.
3. creates their own free Groq key and puts it in their local
   `.env`.
4. Open **http://127.0.0.1:8000**.


```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```


## Project structure

```
app/
  main.py        FastAPI routes
  chatbot.py     RealEstateChatbot class and constructor
  realestate.py  City prices, state notes, buying roadmap
  groq_client.py Groq calls (text, vision, audio)
  history.py     Per-session conversation memory
  config.py      Settings and real-estate system prompt
  schemas.py     Request models
static/
  index.html     UI
  app.js         Chat, image upload, mic recording
  style.css      Dark theme
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Status + key check |
| POST | `/api/chat` | Text question |
| POST | `/api/chat/image` | `multipart`: image + question |
| POST | `/api/chat/audio` | `multipart`: audio (returns transcript) |
| POST | `/api/reset` | Clear session history |

Interactive docs at **http://127.0.0.1:8000/docs**

## Limits

- Image max 10 MB (PNG, JPEG, WEBP, GIF)
- Audio max 25 MB
- History keeps the last 20 turns per session

## Troubleshooting

**"Groq is rate-limiting requests"** - wait a moment and try again, or use another
Groq API key. Voice messages use two calls (transcribe, then answer).

**"Could not reach Groq's servers"** - your internet or DNS dropped. The app
retries transient network blips up to 4 times.

**"model ... not found"** - Groq may retire or rename models. Update the model
names in `.env` and restart the server.

**Microphone blocked** - allow mic permission in the browser and use localhost
rather than an IP address.

**Changes not showing** - restart the server, or run `set RELOAD=1` before
`python run.py` for auto-reload.

`.env` is gitignored so your API key is never committed.

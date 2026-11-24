"""FastAPI app for EstateBot.

The bot answers from a local SQLite database, so this file only has a few
routes: a health check, a chat endpoint and the static web page.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import bot, config, database
from .schemas import ChatRequest

logger = logging.getLogger("estatebot")

# Create the database and sample data on startup.
database.init_db()

app = FastAPI(title="EstateBot - Database Real Estate Bot", version="2.0.0")


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "name": config.BOT_NAME,
        "database": database.DB_PATH.name,
        "cities": database.count_cities(),
    }


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    return {"answer": bot.answer(request.message), "session_id": request.session_id}


@app.get("/api/cities")
def cities() -> list[str]:
    """Small helper endpoint to show the city names stored in the database."""
    return [city["city"] for city in database.all_cities()]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(config.BASE_DIR / "static" / "index.html")


app.mount("/static", StaticFiles(directory=config.BASE_DIR / "static"), name="static")

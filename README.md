# EstateBot — Simple Database Real Estate Bot

A beginner-level Python project for college. It is a small real-estate chatbot
built with **Python**, **SQLite** (the built-in database) and **FastAPI** for the
web page.

The bot does **not** use any external AI API. All answers come from data stored
in a local SQLite database file called `estatebot.db`.

## What it does

1. Stores real-estate data in a database: city prices, rent, stamp duty, the
   buying roadmap, documents and common FAQs.
2. When the user asks a question, it finds the matching city / state / topic in
   the database and prints the stored answer.

Example questions:

- "What is the price of a 2 BHK in Mumbai?"
- "What is the rent in Bengaluru?"
- "What is the stamp duty in Maharashtra?"
- "How do I buy a flat in Delhi?"
- "What documents do I need?"

## How the database is used

`app/database.py` creates these tables on first run and fills them with sample
data:

| Table | Stores |
|---|---|
| `cities` | city, state, aliases, price per sq ft, rent |
| `state_notes` | stamp duty and registration details per state |
| `roadmap_steps` | the step-by-step property buying process |
| `documents` | documents a buyer should keep ready |
| `faqs` | extra keyword-based question / answer pairs |

`app/bot.py` reads the user message, looks for a known city or state, and builds
the reply from the database rows. There is no machine learning — just simple
keyword matching.

## Project structure

```
app/
  database.py   SQLite setup, sample data and queries
  bot.py        Rule-based bot that answers from the database
  main.py       FastAPI routes and web page
  config.py     Small config (project folder, bot name)
  schemas.py    Request model
static/
  index.html    Chat page
  app.js        Sends messages to /api/chat
  style.css     Styling
run.py          Starts the web server
start.bat       Windows one-click start
```

## Requirements

- Python 3.10 or newer

Nothing else to sign up for — there is no API key.

## Setup and run

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Then start the app:

```bash
venv\Scripts\python.exe run.py
```

Or just double-click **`start.bat`**.

Open **http://127.0.0.1:8000** in your browser.

The database file `estatebot.db` is created automatically the first time the app
starts, so you do not need to create it by hand.

## Reset the database

Delete `estatebot.db` and restart the app. It will be re-created with the sample
data from `app/database.py`.

## Add your own data

Open `app/database.py` and edit the sample lists near the top:

- `CITIES` — add `("City", "State", "alias1,alias2", price_low, price_high, rent_low, rent_high)`
- `STATE_NOTES` — add `("State", "stamp duty text", "registration text", "portal", "note")`
- `ROADMAP_STEPS`, `DOCUMENTS`, `FAQS` — add more rows

Delete `estatebot.db` (so the new rows get inserted) and restart.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Status, database name and city count |
| GET | `/api/cities` | List of city names in the database |
| POST | `/api/chat` | Send `{ "message": "..." }`, get `{ "answer": "..." }` |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/chat -H "Content-Type: application/json" -d "{\"message\": \"price in Pune\"}"
```

Interactive docs: **http://127.0.0.1:8000/docs**

## Notes

Prices and charges are approximate sample values for a college demo. They are
not live listings and should be verified with local listings, RERA records and a
lawyer.

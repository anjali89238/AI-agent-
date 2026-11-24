"""EstateBot: a beginner-friendly, database-only real-estate chatbot.

``answer()`` looks at the user's message, finds a city, state or intent
keyword, and then builds the reply from rows stored in SQLite. There is no
external API and no machine learning involved - just simple matching plus
data from :mod:`app.database`.
"""

from __future__ import annotations

import re

from . import database

# Approximate apartment sizes in square feet, used to turn a per-sq-ft price
# into a budget for 1 / 2 / 3 BHK homes.
SIZES = {1: 550, 2: 950, 3: 1350, 4: 1800}

GREETINGS = ("hi", "hello", "hey", "namaste", "good morning", "good evening")
ROADMAP_WORDS = ("buy", "buying", "purchase", "purchasing", "roadmap", "process", "steps", "how to")
STAMP_WORDS = ("stamp", "stamp duty", "registration", "register", "registrar", "duty")
DOC_WORDS = ("document", "documents", "paper", "papers", "paperwork")
RENT_WORDS = ("rent", "rental", "renting")


def _has_word(word: str, text: str) -> bool:
    """True if ``word`` appears in ``text`` as a whole word / phrase."""
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _has_any(words: tuple[str, ...], text: str) -> bool:
    return any(_has_word(word, text) for word in words)


def format_inr(amount: int) -> str:
    if amount >= 10_000_000:
        value = f"{amount / 10_000_000:.2f}".rstrip("0").rstrip(".")
        return f"INR {value} crore"
    if amount >= 100_000:
        value = f"{amount / 100_000:.2f}".rstrip("0").rstrip(".")
        return f"INR {value} lakh"
    return f"INR {amount:,.0f}"


def format_inr_range(low: int, high: int) -> str:
    low_text = format_inr(low).removeprefix("INR ")
    high_text = format_inr(high).removeprefix("INR ")
    return f"INR {low_text} to {high_text}"


# ---------------------------------------------------------------------------
# Answer builders
# ---------------------------------------------------------------------------

def _city_price_answer(city: dict, rent_only: bool = False) -> str:
    state_note = database.get_state_note(city["state"])

    if rent_only:
        lines = [
            f"{city['city']}, {city['state']}",
            f"Typical 2 BHK monthly rent: INR {city['rent_low']:,} - {city['rent_high']:,}.",
            f"For reference, buying costs about INR {city['price_low']:,} - "
            f"{city['price_high']:,} per sq ft.",
            "",
            "These are approximate 2026 ranges. Locality, age and amenities can change the rent a lot.",
        ]
        return "\n".join(lines)

    lines = [
        f"{city['city']}, {city['state']}",
        f"Indicative apartment price: INR {city['price_low']:,} - {city['price_high']:,} per sq ft.",
        "",
        "Estimated price in a mid-market locality:",
    ]
    for bhk in (1, 2, 3):
        size = SIZES[bhk]
        low = city["price_low"] * size
        high = city["price_high"] * size
        lines.append(f"  - {bhk} BHK (~{size:,} sq ft): {format_inr_range(low, high)}")

    lines += [
        "",
        f"Typical 2 BHK monthly rent: INR {city['rent_low']:,} - {city['rent_high']:,}.",
    ]
    if state_note:
        lines.append(
            f"State note: stamp duty {state_note['stamp_duty']} and registration "
            f"{state_note['registration']} ({state_note['portal']})."
        )
    lines += [
        "",
        "These are broad ranges, not live listings. Locality, builder, floor, amenities "
        "and approvals can change the price a lot.",
    ]
    return "\n".join(lines)


def _state_note_answer(state_note: dict) -> str:
    return "\n".join(
        [
            f"{state_note['state']} property registration:",
            f"  - Stamp duty: {state_note['stamp_duty']}",
            f"  - Registration: {state_note['registration']}",
            f"  - Portal: {state_note['portal']}",
            f"  - Note: {state_note['note']}",
            "",
            "Charges change, so confirm the current rates on the state portal or at the sub-registrar.",
        ]
    )


def _roadmap_answer(state_note: dict | None = None) -> str:
    lines = ["Buying property in India, step by step:"]
    for step in database.get_roadmap():
        lines.append(f"{step['step_no']}. {step['title']} - {step['description']}")

    documents = database.get_documents()
    lines += ["", "Keep these documents ready: " + ", ".join(documents) + "."]

    if state_note:
        lines.append(
            f"State note ({state_note['state']}): stamp duty {state_note['stamp_duty']}, "
            f"registration {state_note['registration']}."
        )
    return "\n".join(lines)


def _documents_answer() -> str:
    lines = ["Documents to keep ready when buying property:"]
    lines += [f"  - {name}" for name in database.get_documents()]
    lines += ["", "Always verify original documents with a lawyer before paying any advance."]
    return "\n".join(lines)


def _faq_answer(text: str) -> str | None:
    best = None
    best_score = 0
    for faq in database.get_faqs():
        keywords = [word.strip() for word in faq["keywords"].split(",") if word.strip()]
        score = sum(1 for word in keywords if _has_word(word, text))
        if score > best_score:
            best = faq
            best_score = score
    if best:
        return f"{best['question']}\n\n{best['answer']}"
    return None


def _help_answer() -> str:
    cities = ", ".join(city["city"] for city in database.all_cities())
    return "\n".join(
        [
            "Hi, I'm EstateBot, a simple real-estate bot that answers from a database.",
            "I can help with:",
            "  - Property prices in a city (e.g. \"2 BHK price in Pune\")",
            "  - Rent in a city (e.g. \"rent in Bengaluru\")",
            "  - Stamp duty and registration for a state",
            "  - The property buying process / roadmap",
            "  - Documents needed when buying",
            "",
            f"I know these cities: {cities}.",
            "",
            "Try asking: \"What is the price of a 2 BHK in Mumbai?\"",
        ]
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def answer(message: str) -> str:
    """Return the bot reply for a user ``message`` using the SQLite data."""
    text = message.strip().lower()

    if not text:
        return _help_answer()

    if _has_any(GREETINGS, text) or _has_word("help", text):
        return _help_answer()

    city = database.find_city(text)
    state = database.find_state(text)

    # 1. Questions about documents.
    if _has_any(DOC_WORDS, text):
        return _documents_answer()

    # 2. Questions about stamp duty / registration.
    if _has_any(STAMP_WORDS, text):
        state_note = database.get_state_note(state["state"]) if state else None
        if state_note:
            return _state_note_answer(state_note)
        return (
            "Please mention a state, for example \"stamp duty in Maharashtra\". "
            "I know these states: "
            + ", ".join(row["state"] for row in database.all_state_notes())
            + "."
        )

    # 3. Questions about the buying process.
    if _has_any(ROADMAP_WORDS, text):
        state_note = database.get_state_note(state["state"]) if state else None
        return _roadmap_answer(state_note)

    # 4. A known city: give prices, or rent if asked.
    if city:
        return _city_price_answer(city, rent_only=_has_any(RENT_WORDS, text))

    # 5. A state on its own (no city): explain registration charges.
    if state:
        return _state_note_answer(database.get_state_note(state["state"]))

    # 6. Extra keyword-based questions (loans, RERA, GST, etc.).
    faq = _faq_answer(text)
    if faq:
        return faq

    # 7. Nothing matched: explain what the bot can do.
    return _help_answer()

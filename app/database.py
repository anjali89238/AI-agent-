"""SQLite database for EstateBot.

The whole project stores its real-estate data in a local SQLite file
(``estatebot.db``). On first run ``init_db()`` creates the tables and fills
them with the sample data below. After that the bot only reads from the
database when a user asks a question.

Tables
------
cities        : city, state, aliases and price / rent ranges
state_notes   : stamp duty and registration details per state
roadmap_steps : the step-by-step property buying process
documents     : documents a buyer should keep ready
faqs          : extra keyword-based question / answer pairs
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "estatebot.db"

# ---------------------------------------------------------------------------
# Sample data (used only when the database is empty)
# ---------------------------------------------------------------------------

# city, state, aliases, price_per_sqft_low, price_per_sqft_high,
# rent_2bhk_low, rent_2bhk_high
CITIES = [
    ("Mumbai", "Maharashtra", "bombay", 25000, 60000, 45000, 90000),
    ("Delhi", "Delhi", "new delhi,ncr", 12000, 30000, 25000, 55000),
    ("Bengaluru", "Karnataka", "bangalore", 8000, 16000, 22000, 45000),
    ("Hyderabad", "Telangana", "", 6500, 12000, 18000, 35000),
    ("Pune", "Maharashtra", "", 7500, 14000, 18000, 35000),
    ("Chennai", "Tamil Nadu", "madras", 7000, 14000, 18000, 35000),
    ("Kolkata", "West Bengal", "calcutta", 5500, 11000, 14000, 28000),
    ("Ahmedabad", "Gujarat", "", 4500, 8500, 12000, 22000),
    ("Surat", "Gujarat", "", 4000, 7500, 10000, 18000),
    ("Vadodara", "Gujarat", "baroda", 3500, 6500, 9000, 16000),
    ("Jaipur", "Rajasthan", "", 4000, 8000, 10000, 18000),
    ("Lucknow", "Uttar Pradesh", "", 3500, 7000, 9000, 16000),
    ("Noida", "Uttar Pradesh", "", 7000, 14000, 18000, 35000),
    ("Gurugram", "Haryana", "gurgaon", 9000, 20000, 25000, 50000),
    ("Chandigarh", "Chandigarh", "", 6000, 12000, 15000, 28000),
    ("Indore", "Madhya Pradesh", "", 3500, 6500, 9000, 16000),
    ("Bhopal", "Madhya Pradesh", "", 3000, 5500, 8000, 14000),
    ("Patna", "Bihar", "", 4000, 8000, 10000, 18000),
    ("Kochi", "Kerala", "cochin", 5000, 9000, 12000, 22000),
    ("Thiruvananthapuram", "Kerala", "trivandrum", 4500, 8000, 11000, 20000),
    ("Nagpur", "Maharashtra", "", 3500, 6500, 9000, 16000),
    ("Nashik", "Maharashtra", "", 3500, 6500, 8000, 15000),
    ("Coimbatore", "Tamil Nadu", "", 4000, 7500, 10000, 18000),
    ("Visakhapatnam", "Andhra Pradesh", "vizag", 4000, 7500, 10000, 18000),
    ("Bhubaneswar", "Odisha", "", 3500, 6500, 9000, 16000),
    ("Dehradun", "Uttarakhand", "", 4000, 7500, 10000, 18000),
    ("Guwahati", "Assam", "", 3500, 6500, 9000, 16000),
    ("Mysuru", "Karnataka", "mysore", 4000, 7000, 10000, 18000),
    ("Ludhiana", "Punjab", "", 4000, 7000, 10000, 18000),
    ("Amritsar", "Punjab", "", 3500, 6500, 9000, 16000),
    ("Agra", "Uttar Pradesh", "", 3000, 5500, 8000, 14000),
    ("Varanasi", "Uttar Pradesh", "", 3000, 5500, 8000, 14000),
    ("Ranchi", "Jharkhand", "", 3000, 5500, 8000, 14000),
    ("Raipur", "Chhattisgarh", "", 3000, 5500, 8000, 14000),
    ("Panaji", "Goa", "panjim", 6000, 12000, 18000, 35000),
]

# state, stamp_duty, registration, portal, note
STATE_NOTES = [
    ("Maharashtra", "around 5% for men and 3% for women", "about 1%", "IGR Maharashtra",
     "Check the ready-reckoner rate and register at the local sub-registrar."),
    ("Delhi", "around 6% for men and 4% for women", "about 1%", "DORIS portal",
     "Verify DDA or municipal approvals."),
    ("Karnataka", "around 5% plus cess and surcharge", "about 1%", "Kaveri portal",
     "Complete khata transfer after registration."),
    ("Telangana", "around 6%", "about 0.5%", "IGRS Telangana",
     "Verify layout approval and Dharani records for agricultural land."),
    ("Tamil Nadu", "around 7%", "about 4%", "TNREGINET",
     "Complete patta transfer after registration."),
    ("Gujarat", "around 4.9%", "about 1%", "Garvi portal",
     "Verify the 7/12 land record for plots."),
    ("Uttar Pradesh", "around 7%", "about 1%", "IGRSUP",
     "Verify authority approval in Noida, Greater Noida or Ghaziabad."),
    ("West Bengal", "around 5%", "about 1%", "e-Nathikaran",
     "Apply for mutation after registration."),
    ("Rajasthan", "around 5%", "about 1%", "e-Gras",
     "Verify Jamabandi land records for plots."),
    ("Kerala", "around 8%", "about 2%", "Kerala registration department",
     "Verify title, survey number and village records before paying any advance."),
    ("Haryana", "around 7%", "about 1%", "e-Stamp portal",
     "Verify tehsil records and licences for plotted development."),
    ("Punjab", "around 7%", "about 1%", "Punjab e-stamp",
     "Verify title and approved layout before registration."),
    ("Madhya Pradesh", "around 7.5%", "about 3%", "SAMPADA portal",
     "Verify the land record."),
    ("Bihar", "around 6.5%", "about 2%", "IGRS Bihar",
     "Check the mutation record."),
    ("Odisha", "around 5%", "about 1%", "Odisha IGR",
     "Verify RERA registration and the approved plan."),
    ("Andhra Pradesh", "around 5%", "about 1%", "AP registration department",
     "Verify layout approval and land records."),
    ("Assam", "around 5%", "about 1%", "Assam e-stamp",
     "Verify title and municipal approvals."),
    ("Chhattisgarh", "around 5%", "about 1%", "Chhattisgarh IGR",
     "Verify the land record and approved layout."),
    ("Jharkhand", "around 4%", "about 2%", "Jharkhand IGR",
     "Verify title and municipal approvals."),
    ("Uttarakhand", "around 5%", "about 1%", "Uttarakhand IGR",
     "Verify title and hill-area building rules."),
    ("Goa", "around 3.5%", "about 1%", "Goa registration department",
     "Verify title, zone and CRZ clearance for coastal property."),
    ("Chandigarh", "around 5%", "about 1%", "Chandigarh estate office",
     "Verify allotment or title documents."),
]

# step_no, title, description
ROADMAP_STEPS = [
    (1, "Set a budget", "Add stamp duty, registration, GST for under-construction homes, brokerage and moving costs to the property price."),
    (2, "Check loan eligibility", "Get a home-loan pre-approval so you know your safe EMI range."),
    (3, "Shortlist localities", "Compare price per sq ft, commute, schools, hospitals, water supply and future infrastructure."),
    (4, "Verify the property", "Check RERA registration, approved layout, building plan and occupancy certificate."),
    (5, "Visit the site", "Inspect construction quality, parking, amenities, power backup and actual carpet area."),
    (6, "Do legal due diligence", "Ask a lawyer to check the title chain, encumbrance certificate, NOCs and pending dues."),
    (7, "Negotiate", "Negotiate the price, payment schedule and inclusions, and get every promise in writing."),
    (8, "Pay a token amount", "Pay a small booking amount and collect a dated receipt with the agreed terms."),
    (9, "Sign the agreement", "Sign the sale agreement and, if using a loan, complete the bank's checks."),
    (10, "Register the sale deed", "Pay stamp duty and registration charges and register at the sub-registrar office."),
    (11, "Transfer records", "Apply for mutation / khata transfer and update utility connections in your name."),
    (12, "Take possession", "Collect keys, occupancy certificate, warranties and maintenance documents."),
]

DOCUMENTS = [
    "identity proof",
    "PAN card",
    "address proof",
    "passport-size photographs",
    "income proof and bank statements",
    "sale deed",
    "encumbrance certificate",
    "property tax receipts",
    "approved building plan",
    "RERA registration",
    "NOCs",
    "possession certificate",
]

# keywords, question, answer
FAQS = [
    ("home loan,loan,emi,mortgage",
     "How do I get a home loan?",
     "Compare at least 3 banks or NBFCs. Keep your identity proof, PAN, salary slips, "
     "bank statements and the property documents ready. Get a pre-approval first so you "
     "know your budget, then the bank does technical and legal checks before final approval."),
    ("rera",
     "What is RERA?",
     "RERA (Real Estate Regulation and Development Act) protects home buyers. Always check "
     "that the project is RERA-registered, and verify the project details on your state's RERA website."),
    ("carpet area,built up area,super built up",
     "What is carpet area vs built-up area?",
     "Carpet area is the usable floor area inside your walls. Built-up area adds the wall "
     "thickness. Super built-up area also adds a share of common areas like lifts and lobbies. "
     "Price is usually quoted on built-up or super built-up area, so always ask for the carpet area."),
    ("booking amount,token amount,advance",
     "How much booking amount should I pay?",
     "A token or booking amount is usually 1-5% of the property price. Pay only after you have "
     "seen the documents, and always take a dated receipt that mentions the agreed price and terms."),
    ("investment,invest,appreciation,rental yield",
     "Is real estate a good investment?",
     "Real estate can be a good long-term investment, but returns depend on location, "
     "infrastructure growth and rental demand. Compare the rental yield and appreciation with "
     "other options before deciding."),
    ("brokerage,broker,commission",
     "Is brokerage negotiable?",
     "Yes. Brokerage is usually 1-2% of the property value and is negotiable. Agree on the "
     "commission in writing before the broker starts showing you properties."),
    ("gst",
     "Is GST applicable on property?",
     "GST applies mainly to under-construction properties. Ready-to-move-in properties with an "
     "occupancy certificate generally do not attract GST. Rates change, so confirm with the builder."),
    ("possession,handover",
     "What happens at possession?",
     "At possession you get the keys, occupancy certificate, warranties and maintenance documents. "
     "Do a final inspection and note any defects in writing before signing the possession letter."),
]


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """Open a connection and let rows be accessed by column name."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create the tables and fill them with sample data if they are empty."""
    connection = get_connection()
    try:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL,
                aliases TEXT NOT NULL DEFAULT '',
                price_low INTEGER NOT NULL,
                price_high INTEGER NOT NULL,
                rent_low INTEGER NOT NULL,
                rent_high INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS state_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL UNIQUE,
                stamp_duty TEXT NOT NULL,
                registration TEXT NOT NULL,
                portal TEXT NOT NULL,
                note TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roadmap_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                step_no INTEGER NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keywords TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL
            );
            """
        )
        _seed(connection)
        connection.commit()
    finally:
        connection.close()


def _seed(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM cities").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO cities "
            "(city, state, aliases, price_low, price_high, rent_low, rent_high) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            CITIES,
        )
    if connection.execute("SELECT COUNT(*) FROM state_notes").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO state_notes (state, stamp_duty, registration, portal, note) "
            "VALUES (?, ?, ?, ?, ?)",
            STATE_NOTES,
        )
    if connection.execute("SELECT COUNT(*) FROM roadmap_steps").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO roadmap_steps (step_no, title, description) VALUES (?, ?, ?)",
            ROADMAP_STEPS,
        )
    if connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO documents (name) VALUES (?)",
            [(name,) for name in DOCUMENTS],
        )
    if connection.execute("SELECT COUNT(*) FROM faqs").fetchone()[0] == 0:
        connection.executemany(
            "INSERT INTO faqs (keywords, question, answer) VALUES (?, ?, ?)",
            FAQS,
        )


# ---------------------------------------------------------------------------
# Read queries used by the bot
# ---------------------------------------------------------------------------

def all_cities() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("SELECT * FROM cities ORDER BY city").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def find_city(text: str) -> dict | None:
    """Return the first city mentioned in ``text`` (matches aliases too)."""
    lowered = text.lower()
    for row in all_cities():
        names = [row["city"]]
        names += [alias.strip() for alias in row["aliases"].split(",") if alias.strip()]
        for name in names:
            if re.search(rf"\b{re.escape(name.lower())}\b", lowered):
                return row
    return None


def all_state_notes() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("SELECT * FROM state_notes ORDER BY state").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def find_state(text: str) -> dict | None:
    lowered = text.lower()
    for row in all_state_notes():
        if re.search(rf"\b{re.escape(row['state'].lower())}\b", lowered):
            return row
    return None


def get_state_note(state: str) -> dict | None:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM state_notes WHERE state = ?", (state,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def get_roadmap() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM roadmap_steps ORDER BY step_no"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_documents() -> list[str]:
    connection = get_connection()
    try:
        rows = connection.execute("SELECT name FROM documents ORDER BY id").fetchall()
        return [row["name"] for row in rows]
    finally:
        connection.close()


def get_faqs() -> list[dict]:
    connection = get_connection()
    try:
        rows = connection.execute("SELECT * FROM faqs ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def count_cities() -> int:
    connection = get_connection()
    try:
        return connection.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
    finally:
        connection.close()

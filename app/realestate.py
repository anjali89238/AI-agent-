from __future__ import annotations

import re
from dataclasses import dataclass


def format_inr(amount: int) -> str:
    if amount >= 10_000_000:
        value = f"{amount / 10_000_000:.2f}".rstrip("0").rstrip(".")
        return f"INR {value} crore"
    if amount >= 100_000:
        value = f"{amount / 100_000:.1f}".rstrip("0").rstrip(".")
        return f"INR {value} lakh"
    return f"INR {amount:,.0f}"


def format_inr_range(low: int, high: int) -> str:
    low_text = format_inr(low).removeprefix("INR ")
    high_text = format_inr(high).removeprefix("INR ")
    return f"INR {low_text} to {high_text}"


@dataclass(frozen=True)
class CityMarket:
    city: str
    state: str
    price_per_sqft: tuple[int, int]
    rent_2bhk: tuple[int, int]

    def estimate(self, bhk: int) -> tuple[int, int]:
        sizes = {1: 550, 2: 950, 3: 1350, 4: 1800}
        size = sizes.get(bhk, 950)
        low, high = self.price_per_sqft
        return low * size, high * size


class PropertyKnowledgeBase:
    """Approximate property knowledge and buying guidance for Indian cities."""

    def __init__(self) -> None:
        self.cities = self._build_cities()
        self.aliases = self._build_aliases()
        self.state_notes = self._build_state_notes()
        self.roadmap_steps = [
            "Set a realistic budget. Add stamp duty, registration, GST (for under-construction homes), brokerage, maintenance deposit and moving costs to the property price.",
            "Check loan eligibility and get a home-loan pre-approval so you know your safe EMI range.",
            "Shortlist 2-3 localities. Compare price per sq ft, commute, schools, hospitals, water supply, drainage and future infrastructure.",
            "Verify the project or property. Check RERA registration, approved layout, building plan, occupancy certificate and builder track record.",
            "Visit the site and model flat. Inspect construction quality, parking, amenities, lifts, power backup and actual carpet area.",
            "Do legal due diligence. Ask a lawyer to check the title chain, encumbrance certificate, land conversion, NOCs and pending dues.",
            "Negotiate the price, payment schedule and inclusions. Get every promise in writing.",
            "Pay a small booking or token amount and collect a dated receipt with the agreed terms.",
            "Sign the sale agreement. If using a loan, sign the loan agreement and complete the bank's technical and legal checks.",
            "Pay stamp duty and registration charges, then register the sale deed at the sub-registrar office.",
            "Apply for mutation, khata or property-tax transfer, and update utility connections in your name.",
            "Collect possession, keys, occupancy certificate, warranties and maintenance documents.",
        ]
        self.documents = [
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

    def _build_cities(self) -> dict[str, CityMarket]:
        rows = [
            ("Mumbai", "Maharashtra", (25000, 60000), (45000, 90000)),
            ("Delhi", "Delhi", (12000, 30000), (25000, 55000)),
            ("Bengaluru", "Karnataka", (8000, 16000), (22000, 45000)),
            ("Hyderabad", "Telangana", (6500, 12000), (18000, 35000)),
            ("Pune", "Maharashtra", (7500, 14000), (18000, 35000)),
            ("Chennai", "Tamil Nadu", (7000, 14000), (18000, 35000)),
            ("Kolkata", "West Bengal", (5500, 11000), (14000, 28000)),
            ("Ahmedabad", "Gujarat", (4500, 8500), (12000, 22000)),
            ("Surat", "Gujarat", (4000, 7500), (10000, 18000)),
            ("Vadodara", "Gujarat", (3500, 6500), (9000, 16000)),
            ("Jaipur", "Rajasthan", (4000, 8000), (10000, 18000)),
            ("Lucknow", "Uttar Pradesh", (3500, 7000), (9000, 16000)),
            ("Noida", "Uttar Pradesh", (7000, 14000), (18000, 35000)),
            ("Gurugram", "Haryana", (9000, 20000), (25000, 50000)),
            ("Chandigarh", "Chandigarh", (6000, 12000), (15000, 28000)),
            ("Indore", "Madhya Pradesh", (3500, 6500), (9000, 16000)),
            ("Bhopal", "Madhya Pradesh", (3000, 5500), (8000, 14000)),
            ("Patna", "Bihar", (4000, 8000), (10000, 18000)),
            ("Kochi", "Kerala", (5000, 9000), (12000, 22000)),
            ("Thiruvananthapuram", "Kerala", (4500, 8000), (11000, 20000)),
            ("Nagpur", "Maharashtra", (3500, 6500), (9000, 16000)),
            ("Nashik", "Maharashtra", (3500, 6500), (8000, 15000)),
            ("Coimbatore", "Tamil Nadu", (4000, 7500), (10000, 18000)),
            ("Visakhapatnam", "Andhra Pradesh", (4000, 7500), (10000, 18000)),
            ("Bhubaneswar", "Odisha", (3500, 6500), (9000, 16000)),
            ("Dehradun", "Uttarakhand", (4000, 7500), (10000, 18000)),
            ("Guwahati", "Assam", (3500, 6500), (9000, 16000)),
            ("Mysuru", "Karnataka", (4000, 7000), (10000, 18000)),
            ("Ludhiana", "Punjab", (4000, 7000), (10000, 18000)),
            ("Amritsar", "Punjab", (3500, 6500), (9000, 16000)),
            ("Agra", "Uttar Pradesh", (3000, 5500), (8000, 14000)),
            ("Varanasi", "Uttar Pradesh", (3000, 5500), (8000, 14000)),
            ("Ranchi", "Jharkhand", (3000, 5500), (8000, 14000)),
            ("Raipur", "Chhattisgarh", (3000, 5500), (8000, 14000)),
            ("Panaji", "Goa", (6000, 12000), (18000, 35000)),
        ]
        return {city.city: city for city in (CityMarket(*row) for row in rows)}

    def _build_aliases(self) -> dict[str, str]:
        aliases = {name.lower(): name for name in self.cities}
        aliases.update(
            {
                "bombay": "Mumbai",
                "bangalore": "Bengaluru",
                "gurgaon": "Gurugram",
                "calcutta": "Kolkata",
                "cochin": "Kochi",
                "trivandrum": "Thiruvananthapuram",
                "mysore": "Mysuru",
                "vizag": "Visakhapatnam",
                "panjim": "Panaji",
                "new delhi": "Delhi",
                "ncr": "Delhi",
            }
        )
        return aliases

    def _build_state_notes(self) -> dict[str, str]:
        return {
            "Maharashtra": "Stamp duty is around 5% for men and 3% for women, plus about 1% registration. Check the IGR Maharashtra ready-reckoner rate and register at the local sub-registrar.",
            "Delhi": "Stamp duty is around 6% for men and 4% for women, plus about 1% registration. Use the DORIS portal and verify DDA or municipal approvals.",
            "Karnataka": "Stamp duty is around 5% plus registration, cess and surcharge. Use the Kaveri portal and complete khata transfer after registration.",
            "Telangana": "Stamp duty is around 6% plus about 0.5% registration. Use the IGRS Telangana portal and verify the layout approval and Dharani records for agricultural land.",
            "Tamil Nadu": "Stamp duty is around 7% plus about 4% registration. Use TNREGINET and complete patta transfer after registration.",
            "Gujarat": "Stamp duty is around 4.9% plus about 1% registration. Use the Garvi portal and verify the 7/12 land record for plots.",
            "Uttar Pradesh": "Stamp duty is around 7% plus about 1% registration, with concessions in some cases. Use IGRSUP and verify the authority approval in Noida, Greater Noida or Ghaziabad.",
            "West Bengal": "Stamp duty is around 5% plus about 1% registration. Use e-Nathikaran and apply for mutation after registration.",
            "Rajasthan": "Stamp duty is around 5% plus about 1% registration, with a possible concession for women buyers. Use e-Gras and verify Jamabandi land records for plots.",
            "Kerala": "Stamp duty is around 8% plus about 2% registration. Verify the title, survey number and village records before paying any advance.",
            "Haryana": "Stamp duty is around 7% plus about 1% registration. Use the e-Stamp portal and verify the tehsil records and licences for plotted development.",
            "Punjab": "Stamp duty is around 7% plus about 1% registration. Verify the title and approved layout before registration.",
            "Madhya Pradesh": "Stamp duty is around 7.5% plus about 3% registration. Use the SAMPADA portal and verify the land record.",
            "Bihar": "Stamp duty is around 6.5% plus about 2% registration. Use the IGRS Bihar portal and check the mutation record.",
            "Odisha": "Stamp duty is around 5% plus about 1% registration. Verify the RERA registration and approved plan.",
            "Andhra Pradesh": "Stamp duty is around 5% plus about 1% registration. Verify the layout approval and land records.",
            "Assam": "Stamp duty is around 5% plus about 1% registration. Verify the title and municipal approvals.",
            "Chhattisgarh": "Stamp duty is around 5% plus about 1% registration. Verify the land record and approved layout.",
            "Jharkhand": "Stamp duty is around 4% plus about 2% registration. Verify the title and municipal approvals.",
            "Uttarakhand": "Stamp duty is around 5% plus about 1% registration. Verify the title and hill-area building rules.",
            "Goa": "Stamp duty is around 3.5% plus about 1% registration. Verify the title, zone and CRZ clearance for coastal property.",
            "Chandigarh": "Stamp duty is around 5% plus about 1% registration. Verify the allotment or title documents with the estate office.",
        }

    def add_city(self, market: CityMarket) -> None:
        self.cities[market.city] = market
        self.aliases[market.city.lower()] = market.city

    def add_state_note(self, state: str, note: str) -> None:
        self.state_notes[state] = note

    def find_cities(self, text: str) -> list[CityMarket]:
        lowered = text.lower()
        found: list[CityMarket] = []
        for alias, city_name in self.aliases.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                market = self.cities.get(city_name)
                if market and market not in found:
                    found.append(market)
        return found

    def find_states(self, text: str) -> list[str]:
        lowered = text.lower()
        states: list[str] = []
        for state in self.state_notes:
            if re.search(rf"\b{re.escape(state.lower())}\b", lowered) and state not in states:
                states.append(state)
        return states

    def market_summary(self, market: CityMarket) -> str:
        low, high = market.price_per_sqft
        one = market.estimate(1)
        two = market.estimate(2)
        three = market.estimate(3)
        rent_low, rent_high = market.rent_2bhk
        return (
            f"{market.city}, {market.state}\n"
            f"- Indicative apartment price: INR {low:,}-{high:,} per sq ft.\n"
            f"- Estimated purchase price in a mid-market locality: 1 BHK {format_inr_range(*one)}; "
            f"2 BHK {format_inr_range(*two)}; 3 BHK {format_inr_range(*three)}.\n"
            f"- Typical 2 BHK monthly rent: INR {rent_low:,}-{rent_high:,}.\n"
            f"- These are broad 2026 ranges. Locality, age, builder, floor, amenities and approvals can move the price a lot."
        )

    def state_note(self, state: str | None) -> str:
        if state and state in self.state_notes:
            return self.state_notes[state]
        return "Check the state sub-registrar or IGR portal for current stamp duty, registration charges and local rules."

    def roadmap_text(self, state: str | None = None) -> str:
        lines = ["Buying roadmap in India:"]
        lines.extend(f"{index}. {step}" for index, step in enumerate(self.roadmap_steps, 1))
        lines.append("Keep these documents ready: " + ", ".join(self.documents) + ".")
        lines.append(f"State note: {self.state_note(state)}")
        return "\n".join(lines)

    def wants_roadmap(self, text: str) -> bool:
        lowered = text.lower()
        keywords = (
            "buy",
            "buying",
            "purchase",
            "roadmap",
            "process",
            "steps",
            "how to",
            "registration",
            "stamp duty",
            "loan",
            "documents",
            "legal",
            "due diligence",
        )
        return any(keyword in lowered for keyword in keywords)

    def context_for(self, text: str) -> str:
        cities = self.find_cities(text)
        states = self.find_states(text)
        mentioned_states = {city.state for city in cities}
        mentioned_states.update(states)

        sections: list[str] = []
        for market in cities:
            sections.append("REFERENCE MARKET DATA\n" + self.market_summary(market))

        if self.wants_roadmap(text):
            state = next(iter(mentioned_states), None)
            sections.append("REFERENCE BUYING ROADMAP\n" + self.roadmap_text(state))
        elif not cities and states:
            sections.append(
                "REFERENCE STATE NOTES\n"
                + "\n".join(f"{state}: {self.state_note(state)}" for state in states)
            )
        elif not cities:
            sections.append(
                "REFERENCE NOTE\nNo exact city matched the built-in dataset. Give general real-estate guidance, "
                "state that prices vary by locality, and ask for city, locality, property type and budget."
            )

        sections.append(
            "DATA CAVEAT\nReference ranges are approximate and may be outdated. Never present them as live prices "
            "or guaranteed availability. Ask the user to verify with local listings, RERA records and a lawyer."
        )
        return "\n\n".join(sections)

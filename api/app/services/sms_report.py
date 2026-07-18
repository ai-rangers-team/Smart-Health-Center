"""Parse a plain-text SMS/WhatsApp stock report into structured stock levels.

The low-connectivity path the rubric rewards: an operator with only a basic phone
(no smartphone, no data) texts the remaining stock as a short message
("PARA 120 ORS 40 IFA 300"). In production an SMS/WhatsApp gateway webhook feeds
that text here. Pure function over a read-only catalog, so it can safely back a
public demo simulator; the authenticated write path is unchanged.

Format: whitespace/comma separated <name-or-code> <number> pairs, case-insensitive.
A token matches a catalog medicine by short alias, by exact id, or by name prefix.
"""
import re

# Short codes an operator would realistically text, mapped to catalog ids.
ALIASES = {
    "para": "paracetamol", "pcm": "paracetamol", "pc": "paracetamol",
    "ors": "ors",
    "ifa": "ifa", "iron": "ifa",
    "amox": "amoxicillin", "amx": "amoxicillin",
    "met": "metformin", "metf": "metformin",
}

_PAIR = re.compile(r"([A-Za-z][A-Za-z+]*)\s*[:=]?\s*(\d+)")


def _resolve(token: str, catalog: list[dict]) -> str | None:
    key = token.lower()
    if key in ALIASES:
        return ALIASES[key]
    if any(c["id"] == key for c in catalog):
        return key
    # name prefix, e.g. "parac" -> "Paracetamol 500mg"
    return next((c["id"] for c in catalog if c["name"].lower().startswith(key)), None)


def parse_sms_report(text: str, catalog: list[dict]) -> dict:
    """catalog: [{id, name}, ...] (the centre's own medicines).
    Returns {updates: [{medicine_id, medicine_name, current_stock}], unmatched: [token]}."""
    by_id = {c["id"]: c for c in catalog}
    updates, unmatched, seen = [], [], set()
    for word, num in _PAIR.findall(text or ""):
        mid = _resolve(word, catalog)
        if not mid or mid not in by_id:
            unmatched.append(word)
            continue
        if mid in seen:  # last value wins if the same medicine is texted twice
            for u in updates:
                if u["medicine_id"] == mid:
                    u["current_stock"] = int(num)
            continue
        seen.add(mid)
        updates.append({"medicine_id": mid, "medicine_name": by_id[mid]["name"],
                        "current_stock": int(num)})
    return {"updates": updates, "unmatched": unmatched}

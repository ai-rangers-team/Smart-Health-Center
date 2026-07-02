"""Greedy surplus->deficit redistribution matching (spec §6.2).

For each medicine: match the largest surplus centre to the most critical deficit
centre, transferring enough to bring the needy centre to ~14 days of supply, capped
at the donor's available surplus above its reorder buffer. Gemini phrases each match
as a field instruction elsewhere.
"""

_SURPLUS_BUFFER = 1.5  # donor keeps reorder_level * 1.5 before it's considered surplus
_TARGET_DAYS = 14


def compute_redistribution(centres: list[dict]) -> list[dict]:
    recs: list[dict] = []
    medicines = {m for c in centres for m in c["stock"]}

    for med in medicines:
        surplus = sorted(
            [c for c in centres
             if c["stock"].get(med, {}).get("current_stock", 0)
             > c["stock"].get(med, {}).get("reorder_level", 0) * _SURPLUS_BUFFER],
            key=lambda c: -c["stock"][med]["current_stock"],
        )
        deficit = sorted(
            [c for c in centres if c["stock"].get(med, {}).get("days_remaining", 999) <= 7],
            key=lambda c: c["stock"][med]["days_remaining"],
        )

        for needy in deficit:
            if not surplus:
                break
            donor = surplus[0]
            nd = needy["stock"][med]
            dd = donor["stock"][med]
            need = (_TARGET_DAYS - nd["days_remaining"]) * nd["daily_avg"]
            available = dd["current_stock"] - dd["reorder_level"]
            qty = round(min(need, available))
            if qty <= 0:
                continue
            recs.append({
                "from_centre": donor["name"],
                "to_centre": needy["name"],
                "medicine": med,
                "quantity": qty,
                "urgency": "critical" if nd["days_remaining"] <= 3 else "high",
            })
            dd["current_stock"] -= qty
            if dd["current_stock"] <= dd["reorder_level"] * _SURPLUS_BUFFER:
                surplus.pop(0)

    return recs

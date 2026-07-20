"""District impact ledger — the headline numbers for the demo/pitch (Slide 3).

Pure function. Turns the already-computed stock forecasts + redistribution matches
into the handful of figures a District Health Officer (or an MP) can quote: how many
stock-outs the system caught before shelves ran empty, how much lead time that bought,
and the value of the medicine kept in circulation instead of emergency-procured.

Every rupee/patient figure here is an ESTIMATE from transparent, tunable constants
(unit costs, emergency premium, per-patient usage) — the UI labels them as estimates.
The decision layer stays elsewhere; this only *summarises* what the system already did.
"""
from app.services.thresholds import PER_PATIENT_USAGE, _DEFAULT_USAGE

# Approx routine (rate-contract) public-procurement cost in INR per dispensing unit.
# Order-of-magnitude figures — tune against a state's actual drug rate contract.
UNIT_COST = {
    "paracetamol": 0.5,   # per tablet
    "ors": 5.0,           # per sachet
    "ifa": 0.4,           # per tablet
    "amoxicillin": 1.2,   # per tablet
    "metformin": 0.6,     # per tablet
}
_DEFAULT_UNIT_COST = 1.0

# When a centre runs dry it spot-buys locally at a steep premium over rate-contract
# supply; moving existing surplus instead avoids that premium on the value moved.
EMERGENCY_PREMIUM = 0.40  # 40%


def compute_impact(forecasts: list[dict], recs: list[dict], confirmed: list[dict] | None = None) -> dict:
    """forecasts: flat list across the district (each has `severity` + `days_remaining`).
    recs: redistribution matches (each has `quantity` + `medicine_id`) — the identified
    opportunity. confirmed: transfers a recipient has actually confirmed (each has
    `received_qty` + `medicine_id`). When any transfers are confirmed, the redistribution
    impact reflects DELIVERED reality (anti-fraud layer 4: no credit for unverified
    transfers); otherwise it reflects the opportunity the plan identified."""
    # Shortages caught with a forecast still on the clock (days_remaining is a real
    # number, not a cold-start None and not already at zero) — i.e. flagged early.
    early = [
        f for f in forecasts
        if f.get("severity") in ("critical", "high")
        and f.get("days_remaining") is not None
        and (f.get("days_remaining") or 0) > 0
    ]
    lead_times = [f["days_remaining"] for f in early]
    avg_lead = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0.0

    # Prefer confirmed (delivered) transfers; fall back to the planned opportunity.
    if confirmed:
        transfers = [{"medicine_id": c.get("medicine_id"),
                      "quantity": c.get("received_qty", 0)} for c in confirmed]
        delivered = True
    else:
        transfers = [{"medicine_id": r.get("medicine_id"),
                      "quantity": r.get("quantity", 0)} for r in recs]
        delivered = False

    units = sum(tr["quantity"] for tr in transfers)
    patients = 0.0
    rupees = 0.0
    for tr in transfers:
        med = tr["medicine_id"] or ""
        qty = tr["quantity"]
        usage = PER_PATIENT_USAGE.get(med, _DEFAULT_USAGE)
        # units moved / (units per patient per day) = patient-days of treatment secured
        patients += qty / usage if usage else 0
        rupees += qty * UNIT_COST.get(med, _DEFAULT_UNIT_COST) * EMERGENCY_PREMIUM

    return {
        "stockouts_flagged_early": len(early),
        "avg_lead_time_days": avg_lead,
        "units_redistributed": round(units),
        "patients_protected": round(patients),
        "rupees_saved": round(rupees),
        "transfers_confirmed": delivered,
    }

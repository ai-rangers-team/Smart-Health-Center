"""Derive per-medicine stock levels from one admin-friendly question:
"roughly how many patients per day does this centre see?"

Until a new centre builds its own consumption history (which takes ~2 daily
reports), these levels power the cold-start stock alerts. Ratios are
units-per-patient-per-day, calibrated from the demo district's observed usage
(e.g. PHC Mulshi: ~82 patients/day consuming ~40 paracetamol/day ≈ 0.5).
"""
import math

# medicine_id -> units consumed per patient per day (approximation)
PER_PATIENT_USAGE = {
    "paracetamol": 0.5,
    "ors": 0.3,
    "ifa": 0.7,
    "amoxicillin": 0.3,
    "metformin": 0.35,
}
_DEFAULT_USAGE = 0.4  # unknown medicines: a middle-of-the-road ratio

# Static fallbacks when the admin gives no estimate (the original MEDS defaults)
_STATIC_DEFAULTS = {
    "paracetamol": (100, 200),
    "ors": (50, 100),
    "ifa": (150, 300),
    "amoxicillin": (25, 50),
    "metformin": (50, 100),
}

MIN_BUFFER_DAYS = 3   # min_threshold = ~3 days of estimated usage
REORDER_BUFFER_DAYS = 7  # reorder_level = ~a week


def derive_stock_levels(medicine_id: str, expected_daily_patients: int | None) -> dict:
    """Returns {min_threshold, reorder_level, estimated_daily_usage}."""
    if not expected_daily_patients:
        minimum, reorder = _STATIC_DEFAULTS.get(medicine_id, (50, 100))
        return {"min_threshold": minimum, "reorder_level": reorder,
                "estimated_daily_usage": 0}

    daily = expected_daily_patients * PER_PATIENT_USAGE.get(medicine_id, _DEFAULT_USAGE)
    return {
        "min_threshold": math.ceil(daily * MIN_BUFFER_DAYS),
        "reorder_level": math.ceil(daily * REORDER_BUFFER_DAYS),
        "estimated_daily_usage": round(daily, 1),
    }

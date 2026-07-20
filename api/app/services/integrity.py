"""Deterministic data-integrity checks over a centre's reported signals (anti-fraud
layer 2).

Flags reports that are internally inconsistent or statistically suspicious:
- medicine leaving far faster than patient volume can explain (a diversion signature),
- figures that never vary day to day (a fabrication signature),
- full staff attendance with essentially no patients (ghost staffing).

Pure function — no Gemini, no I/O. Flags are ADVISORY: they surface to the district
officer for a *targeted spot-inspection*, never automatic punishment (an honest
operator in a low-footfall or poor-connectivity area must not be penalized).
"""

MIN_CONSUMPTION_RATE = 10.0   # ignore trivial-volume medicines
# units/patient/day far above any real regimen. Typical dispensing here is ~0.3-0.7;
# >2 means stock is leaving much faster than patient volume explains (review trigger).
PER_PATIENT_CEILING = 2.0
FLATLINE_REPEATS = 6          # this many identical recent footfall values = implausibly flat
FOOTFALL_FLOOR = 5            # avg footfall at/below this = "essentially no patients"
GHOST_ATTENDANCE = 0.95       # ~full staff


def check_integrity(*, medicines, avg_footfall, foot_counts, avg_attendance) -> list[dict]:
    """medicines: [{medicine_name, daily_rate}] (daily_rate = EWMA consumption/day).
    foot_counts: recent footfall counts, newest first. avg_attendance in [0,1] or None.
    Returns flag dicts: {check_type, medicine_name?, message, observed, expected}."""
    flags: list[dict] = []
    ff = avg_footfall or 0

    # 1. Consumption far exceeds what patient volume can explain -> possible diversion.
    for m in medicines:
        rate = m.get("daily_rate") or 0
        if rate < MIN_CONSUMPTION_RATE:
            continue
        per_patient = rate / max(ff, 1)
        if per_patient > PER_PATIENT_CEILING:
            name = m.get("medicine_name")
            flags.append({
                "check_type": "CONSUMPTION_WITHOUT_PATIENTS",
                "medicine_name": name,
                "message": (f"{name} leaving at {per_patient:.1f} units per patient — "
                            f"far above normal; verify dispensing vs diversion"),
                "observed": round(per_patient, 1),
                "expected": PER_PATIENT_CEILING,
            })

    # 2. Reported footfall never varies -> possible fabricated figures.
    recent = list(foot_counts or [])[:FLATLINE_REPEATS]
    if len(recent) >= FLATLINE_REPEATS and len(set(recent)) == 1 and recent[0] > 0:
        flags.append({
            "check_type": "FLATLINE_FOOTFALL",
            "message": (f"Footfall reported as exactly {recent[0]} for "
                        f"{FLATLINE_REPEATS} days running — figures never vary"),
            "observed": recent[0],
            "expected": None,
        })

    # 3. Full staff attendance but essentially no patients -> possible ghost staffing.
    if avg_attendance is not None and avg_attendance >= GHOST_ATTENDANCE and ff <= FOOTFALL_FLOOR:
        flags.append({
            "check_type": "GHOST_STAFFING",
            "message": (f"Attendance {avg_attendance * 100:.0f}% with only {ff:.0f} "
                        f"patients/day — staff present but centre near-idle"),
            "observed": round(ff, 1),
            "expected": None,
        })

    return flags

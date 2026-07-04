"""Pune Rural District demo seed (plan tasks 1.4 + 2.1).

Fixed values (no randomness) so the demo is reproducible. After loading raw
data, each centre runs through the REAL recompute pipeline — so days_remaining,
performance_score, status, denormalized card fields, and alerts are produced by
the same code the live app uses.
"""
from datetime import datetime, timedelta, timezone

from firebase_admin import auth

from app.services.language import default_language_for_state
from app.services.recompute import recompute_centre

DISTRICT = {"id": "pune_rural", "name": "Pune Rural District", "state": "Maharashtra"}
DISTRICT_AVG_FOOTFALL = 78

# email -> (role, centre_id). Accounts must have signed in once before claims
# can attach; provision_accounts() skips (and reports) the ones that haven't.
DEMO_ACCOUNTS = {
    "rishimishra1508@gmail.com": ("district_admin", None),
    "rupeshsharma137@gmail.com": ("phc_operator", "phc_ambegaon"),
    "ishadesai53@gmail.com": ("phc_operator", "phc_mulshi"),
    "devikbansal14@gmail.com": ("phc_operator", "phc_haveli"),
}

MEDS = [
    # id, name, unit, reorder_level, min_threshold
    ("paracetamol", "Paracetamol 500mg", "tablets", 200, 100),
    ("ors", "ORS Sachets", "sachets", 100, 50),
    ("ifa", "Iron + Folic Acid", "tablets", 300, 150),
    ("amoxicillin", "Amoxicillin 250mg", "tablets", 50, 25),
    ("metformin", "Metformin 500mg", "tablets", 100, 50),
]

# The spec §4 demo scenario. stock: med_id -> (current_stock, ~7d consumption history)
CENTRES = [
    {
        "id": "phc_mulshi", "name": "PHC Mulshi", "type": "PHC",
        "block": "Mulshi Taluka", "beds": (12, 8), "attendance": 0.60,
        "footfall_base": 82, "tests_off": [],
        "stock": {
            "paracetamol": (120, [38, 41, 40, 42, 39, 40, 41]),   # ~3 days -> CRITICAL
            "ors": (340, [24, 25, 23, 25, 24, 25, 24]),
            "ifa": (450, [55, 57, 56, 55, 57, 56, 56]),
            "amoxicillin": (300, [24, 26, 25, 25, 24, 26, 25]),
            "metformin": (500, [27, 29, 28, 28, 27, 29, 28]),
        },
    },
    {
        "id": "phc_haveli", "name": "PHC Haveli", "type": "PHC",
        "block": "Haveli Taluka", "beds": (10, 4), "attendance": 0.75,
        "footfall_base": 74, "tests_off": [],
        "stock": {
            "paracetamol": (400, [32, 34, 33, 33, 32, 34, 33]),
            "ors": (90, [44, 46, 45, 44, 45, 46, 45]),             # ~2 days -> CRITICAL
            "ifa": (500, [40, 42, 41, 41, 40, 42, 41]),
            "amoxicillin": (250, [20, 21, 20, 21, 20, 21, 20]),
            "metformin": (450, [24, 25, 24, 25, 24, 25, 24]),
        },
    },
    {
        "id": "phc_ambegaon", "name": "PHC Ambegaon", "type": "PHC",
        "block": "Ambegaon Taluka", "beds": (10, 6), "attendance": 0.80,
        "footfall_base": 70, "tests_off": [],
        "stock": {
            "paracetamol": (500, [30, 31, 30, 31, 30, 31, 30]),
            "ors": (300, [22, 23, 22, 23, 22, 23, 22]),
            "ifa": (450, [88, 92, 90, 89, 91, 90, 90]),            # ~5 days -> HIGH
            "amoxicillin": (280, [18, 19, 18, 19, 18, 19, 18]),
            "metformin": (400, [21, 22, 21, 22, 21, 22, 21]),
        },
    },
    {
        "id": "chc_pune_rural", "name": "Pune Rural CHC", "type": "CHC",
        "block": "Community Health Centre", "beds": (60, 45), "attendance": 0.92,
        "footfall_base": 140, "tests_off": [],
        "stock": {
            "paracetamol": (900, [48, 50, 49, 50, 48, 50, 49]),   # surplus donor
            "ors": (600, [30, 31, 30, 31, 30, 31, 30]),
            "ifa": (800, [45, 47, 46, 46, 45, 47, 46]),
            "amoxicillin": (400, [25, 26, 25, 26, 25, 26, 25]),
            "metformin": (700, [32, 33, 32, 33, 32, 33, 32]),
        },
    },
    {
        "id": "phc_velhe", "name": "PHC Velhe", "type": "PHC",
        "block": "Velhe Taluka", "beds": (10, 2), "attendance": 0.52,
        "footfall_base": 40, "tests_off": ["malaria"],             # -> UNDERPERFORMING
        "stock": {
            "paracetamol": (300, [28, 30, 29, 29, 28, 30, 29]),
            "ors": (220, [23, 24, 23, 24, 23, 24, 23]),
            "ifa": (340, [29, 31, 30, 30, 29, 31, 30]),
            "amoxicillin": (200, [15, 16, 15, 16, 15, 16, 15]),
            "metformin": (350, [18, 19, 18, 19, 18, 19, 18]),
        },
    },
    {
        "id": "phc_bhor", "name": "PHC Bhor", "type": "PHC",
        "block": "Bhor Taluka", "beds": (8, 5), "attendance": 0.88,
        "footfall_base": 61, "tests_off": [],
        "stock": {
            "paracetamol": (450, [26, 27, 26, 27, 26, 27, 26]),
            "ors": (280, [20, 21, 20, 21, 20, 21, 20]),
            "ifa": (420, [27, 28, 27, 28, 27, 28, 27]),
            "amoxicillin": (240, [14, 15, 14, 15, 14, 15, 14]),
            "metformin": (380, [17, 18, 17, 18, 17, 18, 17]),
        },
    },
]

TESTS_ALL = ("malaria", "tb", "pregnancy", "diabetes", "hiv")


def _db():
    from app.firestore_client import db
    return db


def _dates(n: int):
    base = datetime.now(timezone.utc).date()
    return [(base - timedelta(days=i)).strftime("%Y%m%d") for i in range(n - 1, -1, -1)]


def wipe_district():
    """Delete district data (centres + subcollections, alerts, recommendations)."""
    db = _db()
    for cref in db.collection("centres").where("district_id", "==", DISTRICT["id"]).stream():
        for sub in ("stock", "beds", "tests", "attendance", "footfall"):
            for d in cref.reference.collection(sub).stream():
                d.reference.delete()
        cref.reference.delete()
    for coll in ("alerts", "recommendations"):
        for d in db.collection(coll).where("district_id", "==", DISTRICT["id"]).stream():
            d.reference.delete()


def seed_district():
    db = _db()
    db.collection("districts").document(DISTRICT["id"]).set({
        "name": DISTRICT["name"], "state": DISTRICT["state"],
        "total_centres": len(CENTRES),
        "default_language": default_language_for_state(DISTRICT["state"]),
    })

    days30 = _dates(30)
    for c in CENTRES:
        total, occupied = c["beds"]
        cref = db.collection("centres").document(c["id"])
        cref.set({
            "name": c["name"], "type": c["type"], "district_id": DISTRICT["id"],
            "location": {"block": c["block"]},
            "district_avg_footfall": DISTRICT_AVG_FOOTFALL,
            "status": "operational",
        })

        for med_id, name, unit, reorder, minimum in MEDS:
            stock, history = c["stock"][med_id]
            cref.collection("stock").document(med_id).set({
                "medicine_name": name, "unit": unit,
                "current_stock": stock, "reorder_level": reorder,
                "min_threshold": minimum,
                "daily_consumption_avg": round(sum(history) / len(history), 1),
                "consumption_history": history,
            })

        cref.collection("beds").document("current").set({
            "total": total, "occupied": occupied,
            "available": max(0, total - occupied),
        })
        cref.collection("tests").document("current").set(
            {t: (t not in c["tests_off"]) for t in TESTS_ALL})

        # 30 days of history; small fixed wobble, mild decline for Velhe
        for i, day in enumerate(days30):
            wobble = (i % 5) - 2
            drift = (29 - i) // 6 if c["id"] == "phc_velhe" else 0
            count = max(5, c["footfall_base"] + wobble + drift)
            cref.collection("footfall").document(day).set(
                {"date": day, "count": count, "opd": count, "ipd": 0})

            rate = c["attendance"] + (0.05 if i % 3 == 0 else -0.03 if i % 3 == 1 else 0.0)
            rate = max(0.2, min(1.0, round(rate, 2)))
            doctors_total = 6 if c["type"] == "CHC" else 2
            cref.collection("attendance").document(day).set({
                "date": day,
                "doctors_present": round(rate * doctors_total),
                "doctors_total": doctors_total,
                "nurses_present": round(rate * 3),
                "nurses_total": 3,
                "attendance_rate": rate,
            })

    # Run the REAL pipeline per centre: forecasts, score, status, alerts,
    # denormalized dashboard fields.
    results = {}
    for c in CENTRES:
        results[c["id"]] = recompute_centre(c["id"])
    return results


def provision_account(email: str, role: str, district_id: str, centre_id: str | None) -> bool:
    """Attach role custom-claims to one account. Returns True if provisioned,
    False if the account has never signed in yet (caller should treat this as
    a soft skip, not an error)."""
    try:
        u = auth.get_user_by_email(email)
        auth.set_custom_user_claims(u.uid, {
            "role": role, "district_id": district_id, "centre_id": centre_id})
        return True
    except auth.UserNotFoundError:
        return False


def provision_accounts():
    """Attach role custom-claims to demo accounts that exist in Firebase Auth."""
    done, skipped = [], []
    for email, (role, centre_id) in DEMO_ACCOUNTS.items():
        if provision_account(email, role, DISTRICT["id"], centre_id):
            done.append(email)
        else:
            skipped.append(email)  # must sign in once first, then re-run
    return {"provisioned": done, "skipped_never_signed_in": skipped}

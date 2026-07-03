"""Pune Rural District demo data (plan Tasks 1.4 + 2.1).

Fixed, non-random values so the demo is reproducible: 1 CHC + 5 PHCs encoding the
spec scenario exactly (a critical stock-out at Mulshi and Haveli, a warning at
Ambegaon, a surplus donor at the CHC, and an underperforming centre at Velhe).
Gated behind SEED_ENABLED + district_admin at the router layer (app/routers/seed.py).
"""
from datetime import datetime, timedelta, timezone

DISTRICT = {"id": "pune_rural", "name": "Pune Rural District", "state": "Maharashtra"}

DISTRICT_AVG_FOOTFALL = 78

ESSENTIAL_TESTS = ("malaria", "tb", "pregnancy")

# email -> (role, centre_id). Create these Google accounts (or substitute your own
# emails for the demo) and sign in once each so provision_accounts() can attach claims.
DEMO_ACCOUNTS = {
    "admin@pune.gov.in": ("district_admin", None),
    "mulshi@pune.gov.in": ("phc_operator", "phc_mulshi"),
    "haveli@pune.gov.in": ("phc_operator", "phc_haveli"),
    "ambegaon@pune.gov.in": ("phc_operator", "phc_ambegaon"),
    "velhe@pune.gov.in": ("phc_operator", "phc_velhe"),
    "bhor@pune.gov.in": ("phc_operator", "phc_bhor"),
    "chc@pune.gov.in": ("phc_operator", "chc_pune_rural"),
}

# Each centre: display info, 1-3 medicines (id -> current_stock/reorder_level/
# min_threshold/daily_consumption_avg), bed capacity, a constant daily footfall,
# a constant weekly doctor-attendance ratio (present/total "doctor-days" this
# week), and any essential-test overrides (default: all available).
CENTRES = [
    {
        "id": "phc_mulshi", "name": "PHC Mulshi", "type": "PHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 120, "reorder_level": 200,
                             "min_threshold": 100, "daily_consumption_avg": 40},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 300, "reorder_level": 150,
                    "min_threshold": 75, "daily_consumption_avg": 20},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 250, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 15},
        },
        "beds": {"total": 10, "occupied": 6},
        "footfall": 85,
        "doctors": {"present": 15, "total": 25},
        "tests": {},
    },
    {
        "id": "phc_haveli", "name": "PHC Haveli", "type": "PHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 300, "reorder_level": 150,
                             "min_threshold": 75, "daily_consumption_avg": 20},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 90, "reorder_level": 150,
                    "min_threshold": 75, "daily_consumption_avg": 45},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 300, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 15},
        },
        "beds": {"total": 8, "occupied": 5},
        "footfall": 88,
        "doctors": {"present": 22, "total": 25},
        "tests": {},
    },
    {
        "id": "phc_ambegaon", "name": "PHC Ambegaon", "type": "PHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 300, "reorder_level": 150,
                             "min_threshold": 75, "daily_consumption_avg": 20},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 250, "reorder_level": 150,
                    "min_threshold": 75, "daily_consumption_avg": 15},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 450, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 90},
        },
        "beds": {"total": 10, "occupied": 6},
        "footfall": 90,
        "doctors": {"present": 23, "total": 25},
        "tests": {},
    },
    {
        "id": "chc_pune_rural", "name": "Pune Rural CHC", "type": "CHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 900, "reorder_level": 200,
                             "min_threshold": 100, "daily_consumption_avg": 30},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 250, "reorder_level": 100,
                    "min_threshold": 50, "daily_consumption_avg": 20},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 300, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 15},
        },
        "beds": {"total": 30, "occupied": 20},
        "footfall": 130,
        "doctors": {"present": 24, "total": 25},
        "tests": {},
    },
    {
        "id": "phc_velhe", "name": "PHC Velhe", "type": "PHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 300, "reorder_level": 150,
                             "min_threshold": 75, "daily_consumption_avg": 20},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 200, "reorder_level": 150,
                    "min_threshold": 75, "daily_consumption_avg": 15},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 250, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 15},
        },
        "beds": {"total": 10, "occupied": 2},
        "footfall": 40,
        "doctors": {"present": 13, "total": 25},
        "tests": {"malaria": False},
    },
    {
        "id": "phc_bhor", "name": "PHC Bhor", "type": "PHC",
        "stock": {
            "paracetamol": {"medicine_name": "Paracetamol 500mg", "unit": "tablets",
                             "current_stock": 400, "reorder_level": 150,
                             "min_threshold": 75, "daily_consumption_avg": 20},
            "ors": {"medicine_name": "ORS Sachets", "unit": "sachets",
                    "current_stock": 300, "reorder_level": 150,
                    "min_threshold": 75, "daily_consumption_avg": 15},
            "iron_folic": {"medicine_name": "Iron+Folic Tablets", "unit": "tablets",
                           "current_stock": 350, "reorder_level": 100,
                           "min_threshold": 50, "daily_consumption_avg": 15},
        },
        "beds": {"total": 8, "occupied": 5},
        "footfall": 78,
        "doctors": {"present": 25, "total": 25},
        "tests": {},
    },
]

HISTORY_DAYS = 7
TIMESERIES_DAYS = 30


def _dates(n: int) -> list[str]:
    base = datetime.now(timezone.utc).date()
    return [(base - timedelta(days=i)).strftime("%Y%m%d") for i in range(n)]


def _db():
    # Lazy import: keeps this module importable without live credentials
    # (firestore_client initialises Firebase at import time).
    from app.firestore_client import db
    return db


def provision_accounts():
    """Set custom claims on existing Firebase users; skip if the user hasn't signed
    in yet (they claim their role after first sign-in — re-run seed then)."""
    from firebase_admin import auth
    for email, (role, centre_id) in DEMO_ACCOUNTS.items():
        try:
            u = auth.get_user_by_email(email)
            auth.set_custom_user_claims(u.uid, {
                "role": role, "district_id": DISTRICT["id"], "centre_id": centre_id,
            })
        except auth.UserNotFoundError:
            pass


def seed_district():
    db = _db()
    db.collection("districts").document(DISTRICT["id"]).set({
        "name": DISTRICT["name"], "state": DISTRICT["state"],
        "total_centres": len(CENTRES),
    })

    dates = _dates(TIMESERIES_DAYS)
    for c in CENTRES:
        cref = db.collection("centres").document(c["id"])
        cref.set({
            "name": c["name"], "type": c["type"], "district_id": DISTRICT["id"],
            "status": "operational", "district_avg_footfall": DISTRICT_AVG_FOOTFALL,
            "avg_footfall": c["footfall"],
        })

        for med_id, m in c["stock"].items():
            cref.collection("stock").document(med_id).set({
                **m,
                "consumption_history": [m["daily_consumption_avg"]] * HISTORY_DAYS,
            })

        total, occupied = c["beds"]["total"], c["beds"]["occupied"]
        cref.collection("beds").document("current").set({
            "total": total, "occupied": occupied, "available": max(0, total - occupied),
        })

        tests = {t: c["tests"].get(t, True) for t in ESSENTIAL_TESTS}
        cref.collection("tests").document("current").set(tests)

        present, total_slots = c["doctors"]["present"], c["doctors"]["total"]
        rate = present / total_slots
        for day in dates:
            cref.collection("attendance").document(day).set({
                "date": day, "doctors_present": present, "doctors_total": total_slots,
                "nurses_present": 0, "nurses_total": 0, "attendance_rate": rate,
            })
            count = c["footfall"]
            cref.collection("footfall").document(day).set({
                "date": day, "count": count,
                "opd": round(count * 0.8), "ipd": round(count * 0.2),
            })

    provision_accounts()

    # Populate derived fields (performance_score/status) + active alerts so the
    # dashboard has real data immediately after seeding.
    from app.services.recompute import recompute_centre
    for c in CENTRES:
        recompute_centre(c["id"])


def _delete_collection(coll_ref, batch_size: int = 200):
    docs = list(coll_ref.limit(batch_size).stream())
    for doc in docs:
        for sub in doc.reference.collections():
            _delete_collection(sub, batch_size)
        doc.reference.delete()
    if len(docs) >= batch_size:
        _delete_collection(coll_ref, batch_size)


def reset_district():
    db = _db()
    for name in ("centres", "districts", "alerts", "recommendations"):
        _delete_collection(db.collection(name))
    seed_district()

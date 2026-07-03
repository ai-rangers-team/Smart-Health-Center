"""Recompute-on-write (plan Task 2.5): ties forecasting + scoring + alerting

Runs after every operator write (and after seeding) so days_remaining, the
performance score/status, and the active-alerts set are always in sync with
the latest data. Gemini is never called from this path — see app/services/gemini.py.
"""
from app.services import alerting
from app.services.forecasting import forecast_stockout
from app.services.scoring import compute_performance_score


def _db():
    # Lazy import: keeps this module importable without live credentials
    # (firestore_client initialises Firebase at import time).
    from app.firestore_client import db
    return db


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def recompute_centre(centre_id: str) -> dict:
    from firebase_admin import firestore

    db = _db()
    cref = db.collection("centres").document(centre_id)
    centre = cref.get().to_dict() or {}

    forecasts = []
    for doc in cref.collection("stock").stream():
        m = doc.to_dict()
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        doc.reference.update({
            "days_remaining": fc["days_remaining"],
            "predicted_stockout_date": fc["predicted_stockout_date"],
        })
        forecasts.append({"medicine_name": m.get("medicine_name"), **fc})

    beds = (cref.collection("beds").document("current").get().to_dict()) or {}
    tests = (cref.collection("tests").document("current").get().to_dict()) or {}

    att_docs = list(cref.collection("attendance")
                     .order_by("date", direction=firestore.Query.DESCENDING)
                     .limit(7).stream())
    att_rate = _avg([d.to_dict().get("attendance_rate", 0.0) for d in att_docs]) if att_docs else 1.0

    ff_docs = list(cref.collection("footfall")
                    .order_by("date", direction=firestore.Query.DESCENDING)
                    .limit(30).stream())
    avg_footfall = _avg([d.to_dict().get("count", 0) for d in ff_docs])

    score = compute_performance_score({
        "avg_attendance_rate": att_rate,
        "avg_footfall": avg_footfall,
        "district_avg_footfall": centre.get("district_avg_footfall") or 1,
        "critical_stockouts": sum(1 for f in forecasts if f["severity"] == "critical"),
        "bed_occupancy_rate": (beds.get("occupied", 0) / beds["total"]) if beds.get("total") else 0.5,
        "essential_tests_unavailable": sum(1 for t in alerting.ESSENTIAL if tests.get(t) is False),
    })
    cref.update({
        "performance_score": score["score"], "status": score["status"],
        "avg_footfall": round(avg_footfall),
    })

    for a in db.collection("alerts").where("centre_id", "==", centre_id).where("resolved", "==", False).stream():
        a.reference.delete()
    for a in alerting.build_alerts(centre_id, centre.get("name"), centre.get("district_id"),
                                    forecasts, beds, att_rate, tests):
        db.collection("alerts").add({**a, "created_at": firestore.SERVER_TIMESTAMP})

    return score

"""Recompute-on-write (spec §3, plan task 2.5).

Runs synchronously inside operator write endpoints: re-forecasts stock,
re-scores the centre, regenerates its alerts (templates, Gemini-free), and
writes back the denormalized summary fields the dashboard cards read
(footfall_today, beds_*, performance_score, status).
"""
from firebase_admin import firestore

from app.services import alerting
from app.services.forecasting import forecast_stockout
from app.services.scoring import compute_performance_score
from google.cloud.firestore_v1.base_query import FieldFilter


def _db():
    from app.firestore_client import db
    return db


def recompute_centre(centre_id: str) -> dict:
    db = _db()
    cref = db.collection("centres").document(centre_id)
    centre = cref.get().to_dict() or {}

    # 1. Stock forecasts (write back per-medicine)
    forecasts = []
    for doc in cref.collection("stock").stream():
        m = doc.to_dict()
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        doc.reference.update({
            "days_remaining": fc["days_remaining"],
            "predicted_stockout_date": fc["predicted_stockout_date"],
        })
        forecasts.append({
            "medicine_name": m.get("medicine_name"),
            # For the cold-start threshold fallback in alerting:
            "current_stock": m.get("current_stock", 0),
            "min_threshold": m.get("min_threshold", 0),
            **fc,
        })

    # 2. Current beds / tests
    beds = (cref.collection("beds").document("current").get().to_dict()) or {}
    tests = (cref.collection("tests").document("current").get().to_dict()) or {}

    # 3. Latest attendance + footfall
    att_docs = list(cref.collection("attendance")
                    .order_by("date", direction=firestore.Query.DESCENDING)
                    .limit(7).stream())
    att_rates = [d.to_dict().get("attendance_rate") for d in att_docs
                 if d.to_dict().get("attendance_rate") is not None]
    avg_attendance = sum(att_rates) / len(att_rates) if att_rates else None

    foot_docs = list(cref.collection("footfall")
                     .order_by("date", direction=firestore.Query.DESCENDING)
                     .limit(30).stream())
    foot_counts = [d.to_dict().get("count", 0) for d in foot_docs]
    footfall_today = foot_counts[0] if foot_counts else 0
    avg_footfall = sum(foot_counts) / len(foot_counts) if foot_counts else 0

    # 4. Score
    score = compute_performance_score({
        "avg_attendance_rate": avg_attendance if avg_attendance is not None else 1.0,
        "avg_footfall": avg_footfall,
        "district_avg_footfall": centre.get("district_avg_footfall") or 1,
        "critical_stockouts": sum(1 for f in forecasts if f["severity"] == "critical"),
        "bed_occupancy_rate": (beds.get("occupied", 0) / beds["total"]) if beds.get("total") else 0.5,
        "essential_tests_unavailable": sum(1 for t in alerting.ESSENTIAL if tests.get(t) is False),
    })

    # 5. Denormalized summary for the dashboard cards (FE data contract).
    # Status escalation: an imminent stock-out makes a centre operationally
    # critical regardless of its composite score; a high (<=7d) stock-out
    # escalates an otherwise-operational centre to warning.
    status = score["status"]
    severities = {f["severity"] for f in forecasts}
    if "critical" in severities:
        status = "critical"
    elif "high" in severities and status == "operational":
        status = "warning"
    cref.update({
        "performance_score": score["score"],
        "status": status,
        "footfall_today": footfall_today,
        "beds_total": beds.get("total", 0),
        "beds_occupied": beds.get("occupied", 0),
        "beds_available": max(0, beds.get("total", 0) - beds.get("occupied", 0)),
        "last_updated": firestore.SERVER_TIMESTAMP,
    })

    # 6. Replace this centre's active alerts (templates — no Gemini here)
    for a in (db.collection("alerts")
              .where(filter=FieldFilter("centre_id", "==", centre_id))
              .where(filter=FieldFilter("resolved", "==", False)).stream()):
        a.reference.delete()
    for a in alerting.build_alerts(centre_id, centre.get("name"), centre.get("district_id"),
                                   forecasts, beds, avg_attendance, tests):
        db.collection("alerts").add({**a, "created_at": firestore.SERVER_TIMESTAMP})

    # 6b. Data-integrity checks (anti-fraud): flag suspicious/inconsistent reports as
    # advisory DATA_INTEGRITY alerts for the district officer to spot-inspect.
    from app.services.integrity import check_integrity
    base = {"centre_id": centre_id, "centre_name": centre.get("name"),
            "district_id": centre.get("district_id"), "resolved": False}
    for fl in check_integrity(
        medicines=[{"medicine_name": f["medicine_name"],
                    "daily_rate": f.get("daily_consumption_forecast", 0)} for f in forecasts],
        avg_footfall=avg_footfall, foot_counts=foot_counts, avg_attendance=avg_attendance,
    ):
        db.collection("alerts").add({**base, "type": "DATA_INTEGRITY", "severity": "medium",
                                     **fl, "created_at": firestore.SERVER_TIMESTAMP})

    # 6c. Re-evaluate citizen disputes (they were deleted with the alerts above, so
    # regenerate them here to survive operator writes).
    from app.services.citizen import refresh_disputes
    refresh_disputes(centre_id)

    return {**score, "status": status}

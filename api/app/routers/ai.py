"""AI endpoints (plan Tasks 1.6 + 2.7).

Thin glue: read Firestore -> run the decision-layer services (forecasting, scoring,
redistribution) -> enrich with Gemini -> return the standard envelope. Gemini never
gates a write here; these are read/advisory endpoints.

STATUS: built per the plan but UNVERIFIED end-to-end — requires the firestore_client
eager-init fix + service-account creds for smart-health-a35ef + seeded data. The
pure services it calls (forecasting/scoring/redistribution/gemini) are unit-tested.
"""
import time

from fastapi import APIRouter, Depends, Query
from firebase_admin import firestore

from app.deps import get_current_user
from app.models.schemas import ok
from app.services import gemini
from app.services.forecasting import forecast_stockout
from app.services.redistribution import compute_redistribution
from app.services.scoring import compute_performance_score

router = APIRouter(prefix="/api/ai", tags=["ai"])

ESSENTIAL_TESTS = ("malaria", "tb", "pregnancy")

# district_id -> (briefing_text, expires_at_epoch, critical_count_at_generation)
_briefing_cache: dict[str, tuple[str, float, int]] = {}


def _db():
    # Lazy import: keeps this module importable without live credentials
    # (firestore_client initialises Firebase at import time).
    from app.firestore_client import db
    return db


def _stock_forecasts(centre_id: str) -> list[dict]:
    db = _db()
    out = []
    for doc in db.collection("centres").document(centre_id).collection("stock").stream():
        m = doc.to_dict()
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        out.append({"medicine_name": m.get("medicine_name"), "id": doc.id, **m, **fc})
    return out


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _recent_attendance_rate(centre_id: str, days: int = 7) -> float:
    docs = (_db().collection("centres").document(centre_id).collection("attendance")
            .order_by("date", direction=firestore.Query.DESCENDING).limit(days).stream())
    return _mean([d.to_dict().get("attendance_rate", 0.0) for d in docs])


def _recent_footfall(centre_id: str, days: int = 30) -> float:
    docs = (_db().collection("centres").document(centre_id).collection("footfall")
            .order_by("date", direction=firestore.Query.DESCENDING).limit(days).stream())
    return _mean([d.to_dict().get("count", 0) for d in docs])


@router.get("/forecast/{centre_id}")
def forecast(centre_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    meds = _stock_forecasts(centre_id)
    at_risk = [{"name": m["medicine_name"], "days_remaining": m["days_remaining"]}
               for m in meds if m["severity"] in ("critical", "high")]
    narrative = gemini.stockout_narrative(at_risk, lang)
    return ok({"medicines": meds, "narrative": narrative})


@router.get("/district-briefing/{district_id}")
def district_briefing(district_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    alerts = [a.to_dict() for a in _db().collection("alerts")
              .where("district_id", "==", district_id).where("resolved", "==", False).stream()]
    critical = sum(1 for a in alerts if a.get("severity") == "critical")

    hit = _briefing_cache.get(district_id)
    if hit and hit[1] > time.time() and hit[2] == critical:
        return ok({"briefing": hit[0], "cached": True})

    text = gemini.district_briefing(
        len(alerts), critical, [a.get("message", "") for a in alerts], lang)
    _briefing_cache[district_id] = (text, time.time() + 900, critical)  # 15-min TTL
    return ok({"briefing": text, "cached": False})


@router.post("/redistribution/{district_id}")
def redistribution(district_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    db = _db()
    centres = []
    for c in db.collection("centres").where("district_id", "==", district_id).stream():
        stock = {}
        for m in _stock_forecasts(c.id):
            stock[m["id"]] = {
                "current_stock": m.get("current_stock", 0),
                "reorder_level": m.get("reorder_level", 0),
                "daily_avg": m.get("daily_consumption_avg", 1),
                "days_remaining": m["days_remaining"],
            }
        centres.append({"id": c.id, "name": c.to_dict().get("name"), "stock": stock})

    recs = compute_redistribution(centres)
    for r in recs:
        r["gemini_message"] = gemini.redistribution_instruction(r, lang)
        db.collection("recommendations").add({
            **r, "district_id": district_id, "type": "REDISTRIBUTION",
            "status": "pending", "created_at": firestore.SERVER_TIMESTAMP,
        })
    return ok({"recommendations": recs})


# Separate prefix: recommendations are created by the redistribution endpoint
# above, and acknowledged by the district admin from the dashboard.
recs_router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@recs_router.post("/{recommendation_id}/acknowledge")
def acknowledge_recommendation(recommendation_id: str, user=Depends(get_current_user)):
    """District admin acknowledges a redistribution recommendation."""
    if user.get("role") != "district_admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")
    _db().collection("recommendations").document(recommendation_id).update(
        {"status": "acknowledged"})
    return ok({"acknowledged": True})


@router.post("/explain-underperformance/{centre_id}")
def explain_underperformance(centre_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    db = _db()
    centre = (db.collection("centres").document(centre_id).get().to_dict()) or {}
    beds = (db.collection("centres").document(centre_id).collection("beds")
            .document("current").get().to_dict()) or {}
    tests = (db.collection("centres").document(centre_id).collection("tests")
             .document("current").get().to_dict()) or {}
    forecasts = _stock_forecasts(centre_id)

    metrics = {
        "avg_attendance_rate": _recent_attendance_rate(centre_id),
        "avg_footfall": _recent_footfall(centre_id),
        "district_avg_footfall": centre.get("district_avg_footfall") or 1,
        "critical_stockouts": sum(1 for f in forecasts if f["severity"] == "critical"),
        "bed_occupancy_rate": (beds.get("occupied", 0) / beds["total"]) if beds.get("total") else 0.5,
        "essential_tests_unavailable": sum(1 for t in ESSENTIAL_TESTS if tests.get(t) is False),
    }
    score = compute_performance_score(metrics)
    explanation = gemini.underperformance_explanation(score["score"], score["flags"], lang)
    return ok({"score": score, "explanation": explanation})

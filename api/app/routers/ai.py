"""AI endpoints (plan Tasks 1.6 + 2.7).

Thin glue: read Firestore -> run the decision-layer services (forecasting, scoring,
redistribution) -> enrich with Gemini -> return the standard envelope. Gemini never
gates a write here; these are read/advisory endpoints.
"""
import time

from fastapi import APIRouter, Depends, Query
from firebase_admin import firestore

from app.deps import get_current_user
from app.models.schemas import ok
from app.services import gemini
from app.services.forecasting import forecast_stockout
from app.services.recompute import recompute_centre
from app.services.redistribution import compute_redistribution

router = APIRouter(prefix="/api/ai", tags=["ai"])

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


@router.post("/explain-underperformance/{centre_id}")
def explain_underperformance(centre_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    score = recompute_centre(centre_id)
    explanation = gemini.underperformance_explanation(score["score"], score["flags"], lang)
    return ok({"score": score, "explanation": explanation})

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
from app.services.forecasting import forecast_footfall, forecast_stockout
from app.services.recompute import recompute_centre
from app.services.redistribution import compute_redistribution
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/api/ai", tags=["ai"])

# (district_id, lang) -> (briefing_text, expires_at_epoch, critical_count_at_generation)
_briefing_cache: dict[tuple[str, str], tuple[str, float, int]] = {}


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

    # Patient-demand forecast from the footfall series (spec §6.4) — the
    # forward-looking number the challenge calls an "AI-driven demand forecast".
    ff_docs = (_db().collection("centres").document(centre_id).collection("footfall")
               .order_by("date", direction=firestore.Query.DESCENDING).limit(30).stream())
    counts = [d.to_dict().get("count", 0) for d in ff_docs][::-1]  # oldest -> newest
    footfall = forecast_footfall(counts) if counts else {"projection": None, "trend": "stable"}

    return ok({"medicines": meds, "narrative": narrative, "footfall": footfall})


@router.get("/district-briefing/{district_id}")
def district_briefing(district_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    alerts = [a.to_dict() for a in _db().collection("alerts")
              .where(filter=FieldFilter("district_id", "==", district_id)).where(filter=FieldFilter("resolved", "==", False)).stream()]
    critical = sum(1 for a in alerts if a.get("severity") == "critical")

    # Cache per (district, language) — a cached English briefing must not be
    # served to a Marathi request. Still invalidates when the critical count
    # changes (e.g. right after a live operator write).
    cache_key = (district_id, lang)
    hit = _briefing_cache.get(cache_key)
    if hit and hit[1] > time.time() and hit[2] == critical:
        return ok({"briefing": hit[0], "cached": True})

    text = gemini.district_briefing(
        len(alerts), critical, [a.get("message", "") for a in alerts], lang)
    if text:  # never cache a failed (empty) Gemini response — retry next request
        _briefing_cache[cache_key] = (text, time.time() + 900, critical)  # 15-min TTL
    return ok({"briefing": text, "cached": False})


@router.post("/redistribution/{district_id}")
def redistribution(district_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    db = _db()
    centres = []
    for c in db.collection("centres").where(filter=FieldFilter("district_id", "==", district_id)).stream():
        stock = {}
        for m in _stock_forecasts(c.id):
            stock[m["id"]] = {
                "medicine_name": m.get("medicine_name") or m["id"],
                "current_stock": m.get("current_stock", 0),
                "reorder_level": m.get("reorder_level", 0),
                "daily_avg": m.get("daily_consumption_avg", 1),
                "days_remaining": m["days_remaining"],
            }
        centres.append({"id": c.id, "name": c.to_dict().get("name"), "stock": stock})

    recs = compute_redistribution(centres)

    # Each generated plan supersedes the previous pending one — without this,
    # every click of "Generate plan" would stack duplicate recommendations.
    for old in (db.collection("recommendations")
                .where(filter=FieldFilter("district_id", "==", district_id))
                .where(filter=FieldFilter("status", "==", "pending")).stream()):
        old.reference.delete()

    for r in recs:
        r["gemini_message"] = gemini.redistribution_instruction(r, lang)
        db.collection("recommendations").add({
            **r, "district_id": district_id, "type": "REDISTRIBUTION",
            "status": "pending", "lang": lang,  # language the message was written in
            "created_at": firestore.SERVER_TIMESTAMP,
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
    score = recompute_centre(centre_id)
    explanation = gemini.underperformance_explanation(score["score"], score["flags"], lang)
    return ok({"score": score, "explanation": explanation})

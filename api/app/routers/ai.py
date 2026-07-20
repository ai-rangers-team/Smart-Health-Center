"""AI endpoints (plan Tasks 1.6 + 2.7).

Thin glue: read Firestore -> run the decision-layer services (forecasting, scoring,
redistribution) -> enrich with Gemini -> return the standard envelope. Gemini never
gates a write here; these are read/advisory endpoints.
"""
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from firebase_admin import firestore
from pydantic import BaseModel, Field

from app.deps import get_current_user, require_own_centre
from app.models.schemas import ok
from app.services import audit, gemini
from app.services.forecasting import forecast_footfall, forecast_stockout
from app.services.impact import compute_impact
from app.services.outbreak import MARKERS, detect_outbreaks
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
    dref = _db().collection("districts").document(district_id)
    if text:  # never cache a failed (empty) Gemini response — retry next request
        _briefing_cache[cache_key] = (text, time.time() + 900, critical)  # 15-min TTL
        # Persist as the last-good briefing so a rate-limited Gemini never
        # leaves the dashboard without one (served with stale=true below).
        dref.set({"last_briefing": {lang: text}}, merge=True)
        return ok({"briefing": text, "cached": False})

    stored = ((dref.get().to_dict() or {}).get("last_briefing") or {}).get(lang, "")
    return ok({"briefing": stored, "cached": False, "stale": bool(stored)})


def _district_stock(district_id: str) -> tuple[list[dict], list[dict]]:
    """Assemble every centre's stock (in the shape the redistribution engine wants)
    plus the flat list of per-medicine forecasts across the district. Shared by the
    redistribution and impact endpoints so both read the same numbers."""
    db = _db()
    centres, all_forecasts = [], []
    for c in db.collection("centres").where(filter=FieldFilter("district_id", "==", district_id)).stream():
        stock = {}
        for m in _stock_forecasts(c.id):
            all_forecasts.append(m)
            stock[m["id"]] = {
                "medicine_name": m.get("medicine_name") or m["id"],
                "current_stock": m.get("current_stock", 0),
                "reorder_level": m.get("reorder_level", 0),
                "daily_avg": m.get("daily_consumption_avg", 1),
                "days_remaining": m["days_remaining"],
            }
        centres.append({"id": c.id, "name": c.to_dict().get("name"), "stock": stock})
    return centres, all_forecasts


@router.get("/outbreak/{district_id}")
def outbreak(district_id: str, user=Depends(get_current_user)):
    """Possible disease-cluster early warning — consumption/footfall surges across
    multiple centres (deterministic, no Gemini). Empty list means no cluster signal."""
    db = _db()
    centres = []
    for c in db.collection("centres").where(filter=FieldFilter("district_id", "==", district_id)).stream():
        foot_docs = list(c.reference.collection("footfall")
                         .order_by("date", direction=firestore.Query.DESCENDING).limit(10).stream())
        footfall = [d.to_dict().get("count", 0) for d in foot_docs][::-1]  # oldest -> newest
        consumption = {}
        for s in c.reference.collection("stock").stream():
            m = s.to_dict()
            if s.id in MARKERS:
                consumption[s.id] = list(m.get("consumption_history") or [])
        centres.append({"name": c.to_dict().get("name"), "footfall": footfall,
                        "consumption": consumption})
    return ok({"outbreaks": detect_outbreaks(centres)})


@router.get("/impact/{district_id}")
def impact(district_id: str, user=Depends(get_current_user)):
    """District impact ledger — deterministic headline metrics (no Gemini): shortages
    caught early, lead time bought, and the redistribution opportunity in patients/₹."""
    centres, forecasts = _district_stock(district_id)
    recs = compute_redistribution(centres)
    # Transfers a recipient has actually confirmed count as delivered impact.
    confirmed = [r.to_dict() for r in _db().collection("recommendations")
                 .where(filter=FieldFilter("district_id", "==", district_id))
                 .where(filter=FieldFilter("status", "in", ["received", "disputed"])).stream()]
    return ok(compute_impact(forecasts, recs, confirmed=confirmed))


@router.post("/redistribution/{district_id}")
def redistribution(district_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    db = _db()
    centres, _ = _district_stock(district_id)
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


class ReceiptBody(BaseModel):
    received_qty: float = Field(ge=0)


@recs_router.post("/{recommendation_id}/confirm-receipt")
def confirm_receipt(recommendation_id: str, body: ReceiptBody,
                    user=Depends(get_current_user)):
    """Recipient operator confirms how much of a transfer actually arrived (anti-fraud
    layer 4). Applies the received quantity to the recipient's stock and reconciles it
    against what the plan said to send — a shortfall marks the transfer DISPUTED, which
    surfaces to the district officer. Only the recipient centre's own operator may confirm."""
    from fastapi import HTTPException
    db = _db()
    ref = db.collection("recommendations").document(recommendation_id)
    rec = ref.get().to_dict()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    to_id = rec.get("to_centre_id")
    if not to_id:
        raise HTTPException(status_code=400, detail="Recommendation predates receipt tracking")
    require_own_centre(to_id, user)  # only the receiving centre's operator
    if rec.get("status") in ("received", "disputed"):
        return ok({"status": rec["status"], "already": True})

    medicine_id = rec.get("medicine_id")
    recommended = rec.get("quantity", 0) or 0
    received = body.received_qty

    sref = db.collection("centres").document(to_id).collection("stock").document(medicine_id)
    prev = sref.get().to_dict() or {}
    new_stock = (prev.get("current_stock", 0) or 0) + received
    sref.update({"current_stock": new_stock,
                 "last_updated": datetime.now(timezone.utc).isoformat()})

    shortfall = max(0, recommended - received)
    status = "disputed" if shortfall > 0 else "received"
    ref.update({
        "status": status, "received_qty": received, "shortfall": shortfall,
        "received_by": user.get("email") or user.get("uid"),
        "received_at": firestore.SERVER_TIMESTAMP,
    })
    audit.record("transfer_receipt", to_id, user.get("district_id"),
                 audit.actor_from_user(user), before=prev.get("current_stock"),
                 after=new_stock, medicine_id=medicine_id,
                 recommended=recommended, received=received, shortfall=shortfall)
    recompute_centre(to_id)
    return ok({"status": status, "shortfall": shortfall})


@router.post("/explain-underperformance/{centre_id}")
def explain_underperformance(centre_id: str, lang: str = Query("mr"), user=Depends(get_current_user)):
    score = recompute_centre(centre_id)
    explanation = gemini.underperformance_explanation(score["score"], score["flags"], lang)
    return ok({"score": score, "explanation": explanation})

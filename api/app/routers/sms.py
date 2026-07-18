"""SMS/WhatsApp stock-report parsing (low-connectivity path).

Parse-only and read-only: it reads a centre's medicine catalog and maps a texted
message to structured stock levels, returning what it understood. It does NOT
write — the demo simulator can call it without auth, while the real write path in
production sits behind an authenticated gateway webhook. Reveals nothing the public
citizen page doesn't already (medicine names + a proposed count the sender typed).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import ok
from app.services.recompute import recompute_centre
from app.services.sms_report import parse_sms_report

router = APIRouter(prefix="/api/sms", tags=["sms"])


class SmsParseBody(BaseModel):
    centre_id: str = Field(min_length=1)
    text: str = Field(max_length=500)


class SmsReportBody(SmsParseBody):
    secret: str | None = None


def _db():
    from app.firestore_client import db
    return db


def _catalog(cref):
    return [{"id": s.id, "name": (s.to_dict() or {}).get("medicine_name", s.id)}
            for s in cref.collection("stock").stream()]


@router.post("/parse")
def sms_parse(body: SmsParseBody):
    """Parse-only preview (no write, no auth) — used to show what a text would do."""
    cref = _db().collection("centres").document(body.centre_id)
    doc = cref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Centre not found")
    parsed = parse_sms_report(body.text, _catalog(cref))
    return ok({"centre_name": doc.to_dict().get("name"), **parsed})


@router.post("/report")
def sms_report(body: SmsReportBody):
    """Webhook: parse a texted report AND apply it — writes stock and recomputes, so
    the district dashboard updates live. Authenticated by the shared gateway secret."""
    if (body.secret or "") != settings.sms_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid SMS secret")
    cref = _db().collection("centres").document(body.centre_id)
    doc = cref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Centre not found")

    parsed = parse_sms_report(body.text, _catalog(cref))
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    for u in parsed["updates"]:
        ref = cref.collection("stock").document(u["medicine_id"])
        prev = ref.get().to_dict() or {}
        new_stock = u["current_stock"]
        updates = {"current_stock": new_stock,
                   "last_updated": datetime.now(timezone.utc).isoformat()}
        # Same consumption-history bookkeeping as operator.update_stock: a texted
        # count is the REMAINING stock; the drawdown since the last report feeds the
        # forecaster (merged per-day so two texts in a day don't read as two days).
        drawdown = max(0, (prev.get("current_stock") or 0) - new_stock)
        if drawdown > 0:
            history = list(prev.get("consumption_history") or [])
            if prev.get("consumption_last_date") == today and history:
                history[-1] += drawdown
            else:
                history = history[-13:] + [drawdown]
            updates["consumption_history"] = history
            updates["consumption_last_date"] = today
        ref.update(updates)

    if parsed["updates"]:
        recompute_centre(body.centre_id)
    return ok({"centre_name": doc.to_dict().get("name"),
               "applied": parsed["updates"], "unmatched": parsed["unmatched"]})

"""Public, unauthenticated citizen view of a single centre (transparency / QR poster).

A citizen scans a QR poster at their PHC and sees, in their own language, whether the
centre is functioning right now: is a doctor present, are beds free, are essential
medicines and tests available. Read-only and deliberately COARSE — it exposes
availability status (available / low / out), never exact stock counts, performance
scores, or any operator/staff identity. Served via the Admin SDK so Firestore's
signed-in-only rules stay closed; this endpoint is the only public surface.
"""
from fastapi import APIRouter, HTTPException
from firebase_admin import firestore
from pydantic import BaseModel, Field

from app.models.schemas import ok
from google.cloud.firestore_v1.base_query import FieldFilter
from app.services.citizen import refresh_disputes

router = APIRouter(prefix="/api/public", tags=["public"])

# Medicines/tests a citizen would reasonably ask a rural PHC about.
_ESSENTIAL_TESTS = ("malaria", "tb", "pregnancy")


def _db():
    from app.firestore_client import db
    return db


def _medicine_status(m: dict) -> str:
    stock = m.get("current_stock", 0) or 0
    if stock <= 0:
        return "out"
    days = m.get("days_remaining")
    minimum = m.get("min_threshold") or 0
    if (days is not None and days <= 7) or (minimum and stock <= minimum):
        return "low"
    return "available"


@router.get("/centre/{centre_id}")
def public_centre(centre_id: str):
    cref = _db().collection("centres").document(centre_id)
    doc = cref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Centre not found")
    c = doc.to_dict()

    beds = (cref.collection("beds").document("current").get().to_dict()) or {}
    tests = (cref.collection("tests").document("current").get().to_dict()) or {}

    medicines = []
    for s in cref.collection("stock").stream():
        m = s.to_dict()
        medicines.append({"id": s.id, "name": m.get("medicine_name", s.id),
                          "status": _medicine_status(m)})

    # Latest attendance -> "is a doctor here today?" (boolean, never a count/name)
    from firebase_admin import firestore
    att = list(cref.collection("attendance")
               .order_by("date", direction=firestore.Query.DESCENDING).limit(1).stream())
    doctor_present = None
    if att:
        a = att[0].to_dict()
        doctor_present = (a.get("doctors_present", 0) or 0) > 0

    return ok({
        "name": c.get("name"),
        "type": c.get("type"),
        "block": (c.get("location") or {}).get("block"),
        "doctor_present": doctor_present,
        "beds": {"available": c.get("beds_available", beds.get("available", 0)),
                 "total": c.get("beds_total", beds.get("total", 0))},
        "medicines": medicines,
        "tests": {t: bool(tests.get(t, True)) for t in _ESSENTIAL_TESTS},
    })


class CitizenFeedback(BaseModel):
    doctor_present: bool
    medicine_available: bool
    # Anonymous per-browser token (random, no PII) — lets the dispute logic count
    # each device once and lets this endpoint drop same-day repeats.
    device: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


@router.post("/centre/{centre_id}/feedback")
def submit_feedback(centre_id: str, body: CitizenFeedback):
    """A citizen reports ground truth from their visit (coarse, no PII). Rate-limited
    by the global SlowAPI limiter. Structured yes/no only — there is no free-text field,
    so the surface can't carry defamation. One report per device per centre per day:
    same-day repeats are accepted politely but not stored, so a burst from one phone
    can never manufacture a dispute. Re-evaluates citizen disputes on every stored
    report so a real contradiction still raises an alert for the district officer."""
    db = _db()
    cref = db.collection("centres").document(centre_id)
    doc = cref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Centre not found")

    from datetime import date
    today = date.today().isoformat()
    dup = list(db.collection("citizen_feedback")
               .where(filter=FieldFilter("centre_id", "==", centre_id))
               .where(filter=FieldFilter("device", "==", body.device))
               .where(filter=FieldFilter("date", "==", today))
               .limit(1).stream())
    if dup:
        return ok({"received": True})  # indistinguishable from a stored report, by design

    db.collection("citizen_feedback").add({
        "centre_id": centre_id,
        "district_id": doc.to_dict().get("district_id"),
        "doctor_present": body.doctor_present,
        "medicine_available": body.medicine_available,
        "device": body.device,
        "date": today,
        "at": firestore.SERVER_TIMESTAMP,
    })
    refresh_disputes(centre_id)
    return ok({"received": True})

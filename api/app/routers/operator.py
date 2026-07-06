"""PHC operator write endpoints (spec §5, plan task 2.5).

Every write is scoped to the operator's own centre (custom-claim check) and
synchronously recomputes forecasts, score, and alerts — so the district
dashboard updates within ~1s via Firestore listeners.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.deps import get_current_user, require_own_centre
from app.models.schemas import (AttendanceLog, BedsUpdate, FootfallLog, StockUpdate,
                                TestsUpdate, ok)
from app.services.invoice_extract import extract_restock_items
from app.services.recompute import recompute_centre

router = APIRouter(prefix="/api/centres", tags=["operator"])

_ALLOWED_INVOICE_TYPES = {"application/pdf", "image/jpeg", "image/png"}
_MAX_INVOICE_BYTES = 8 * 1024 * 1024


def _db():
    from app.firestore_client import db
    return db


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


@router.patch("/{centre_id}/stock")
def update_stock(centre_id: str, body: StockUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    ref = (_db().collection("centres").document(centre_id)
           .collection("stock").document(body.medicine_id))
    prev = ref.get().to_dict() or {}
    updates = {"current_stock": body.current_stock,
               "last_updated": datetime.now(timezone.utc).isoformat()}
    # Record today's consumption for the forecaster (consumption = stock
    # drawdown since the last report, floored at 0). Multiple saves on the
    # same day MERGE into one daily entry — otherwise two reports in a day
    # would read as two days of consumption and skew the EWMA.
    drawdown = max(0, (prev.get("current_stock") or 0) - body.current_stock)
    if drawdown > 0:
        today = _today()
        history = list(prev.get("consumption_history") or [])
        if prev.get("consumption_last_date") == today and history:
            history[-1] += drawdown
        else:
            history = history[-13:] + [drawdown]
        updates["consumption_history"] = history
        updates["consumption_last_date"] = today
    ref.update(updates)
    return ok({"recomputed": recompute_centre(centre_id)})


@router.post("/{centre_id}/stock/extract")
async def extract_stock_from_document(centre_id: str, file: UploadFile = File(...),
                                       user=Depends(get_current_user)):
    """Reads a restock invoice photo/PDF and proposes stock updates for review —
    never writes. The operator confirms via the normal PATCH /stock flow above."""
    require_own_centre(centre_id, user)
    if file.content_type not in _ALLOWED_INVOICE_TYPES:
        raise HTTPException(status_code=400,
                             detail="Unsupported file type — upload a PDF or a photo (JPG/PNG).")
    data = await file.read()
    if len(data) > _MAX_INVOICE_BYTES:
        raise HTTPException(status_code=400, detail="File too large — max 8MB.")

    stock_docs = list(_db().collection("centres").document(centre_id).collection("stock").stream())
    catalog = [{"id": d.id, "name": (d.to_dict() or {}).get("medicine_name", d.id),
                "unit": (d.to_dict() or {}).get("unit", ""),
                "current_stock": (d.to_dict() or {}).get("current_stock", 0) or 0}
               for d in stock_docs]
    by_id = {c["id"]: c for c in catalog}

    try:
        extracted = extract_restock_items(data, file.content_type, catalog)
    except Exception:
        raise HTTPException(status_code=502,
                             detail="Could not read the document. Try again or enter stock manually.")

    items, unmatched = [], []
    for e in extracted:
        cat = by_id.get(e.medicine_id) if e.medicine_id else None
        if not cat:
            unmatched.append(e.raw_name)
            continue
        items.append({
            "medicine_id": cat["id"], "medicine_name": cat["name"], "unit": cat["unit"],
            "current_stock": cat["current_stock"], "quantity_received": e.quantity,
            "proposed_stock": cat["current_stock"] + e.quantity,
            "confidence": e.confidence,
        })
    return ok({"items": items, "unmatched": unmatched})


@router.patch("/{centre_id}/beds")
def update_beds(centre_id: str, body: BedsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    ref = (_db().collection("centres").document(centre_id)
           .collection("beds").document("current"))
    stored_total = (ref.get().to_dict() or {}).get("total", 0)
    total = body.total if body.total is not None else stored_total
    ref.set({"total": total, "occupied": body.occupied,
             "available": max(0, total - body.occupied)}, merge=True)
    return ok({"recomputed": recompute_centre(centre_id)})


@router.post("/{centre_id}/footfall")
def log_footfall(centre_id: str, body: FootfallLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = _today()
    (_db().collection("centres").document(centre_id)
     .collection("footfall").document(day)
     .set({"date": day, **body.model_dump()}))
    return ok({"recomputed": recompute_centre(centre_id)})


@router.post("/{centre_id}/attendance")
def log_attendance(centre_id: str, body: AttendanceLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = _today()
    rate = body.doctors_present / body.doctors_total
    (_db().collection("centres").document(centre_id)
     .collection("attendance").document(day)
     .set({"date": day, **body.model_dump(), "attendance_rate": rate}))
    return ok({"recomputed": recompute_centre(centre_id)})


@router.patch("/{centre_id}/tests")
def update_tests(centre_id: str, body: TestsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    cref = _db().collection("centres").document(centre_id)
    cref.collection("tests").document("current").set(body.tests, merge=True)
    # Dated snapshot -> a real "test availability audit" trail (spec §4).
    day = _today()
    cref.collection("tests_history").document(day).set({
        "date": day,
        "available": body.tests,
        "unavailable_count": sum(1 for v in body.tests.values() if v is False),
    })
    return ok({"recomputed": recompute_centre(centre_id)})

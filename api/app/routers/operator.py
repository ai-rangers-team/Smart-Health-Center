"""PHC operator write endpoints (spec §5, plan task 2.5).

Every write is scoped to the operator's own centre (custom-claim check) and
synchronously recomputes forecasts, score, and alerts — so the district
dashboard updates within ~1s via Firestore listeners.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.deps import get_current_user, require_own_centre
from app.models.schemas import (AttendanceLog, BedsUpdate, FootfallLog, StockUpdate,
                                TestsUpdate, ok)
from app.services.recompute import recompute_centre

router = APIRouter(prefix="/api/centres", tags=["operator"])


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
    # Append today's consumption to the history the forecaster reads
    # (consumption = stock drawdown since the last report, floored at 0).
    drawdown = max(0, (prev.get("current_stock") or 0) - body.current_stock)
    if drawdown > 0:
        history = (prev.get("consumption_history") or [])[-13:]
        updates["consumption_history"] = history + [drawdown]
    ref.update(updates)
    return ok({"recomputed": recompute_centre(centre_id)})


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
    (_db().collection("centres").document(centre_id)
     .collection("tests").document("current").set(body.tests, merge=True))
    return ok({"recomputed": recompute_centre(centre_id)})

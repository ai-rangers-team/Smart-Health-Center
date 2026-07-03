"""Operator write endpoints (plan Task 2.5).

Every write recomputes forecasts/score/alerts synchronously (app.services.recompute)
so the dashboard reflects it on the next onSnapshot tick — Gemini is never on this
path. Each endpoint is scoped to the caller's own centre via require_own_centre.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.deps import get_current_user, require_own_centre
from app.models.schemas import AttendanceLog, BedsUpdate, FootfallLog, StockUpdate, TestsUpdate, ok
from app.services.recompute import recompute_centre

router = APIRouter(prefix="/api/centres", tags=["operator"])


def _db():
    from app.firestore_client import db
    return db


@router.patch("/{centre_id}/stock")
def update_stock(centre_id: str, body: StockUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    (_db().collection("centres").document(centre_id).collection("stock")
     .document(body.medicine_id).update({"current_stock": body.current_stock}))
    return ok({"recomputed": recompute_centre(centre_id)})


@router.patch("/{centre_id}/beds")
def update_beds(centre_id: str, body: BedsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    ref = _db().collection("centres").document(centre_id).collection("beds").document("current")
    total = (ref.get().to_dict() or {}).get("total", 0)
    ref.set({"occupied": body.occupied, "available": max(0, total - body.occupied)}, merge=True)
    return ok({"recomputed": recompute_centre(centre_id)})


@router.post("/{centre_id}/footfall")
def log_footfall(centre_id: str, body: FootfallLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    (_db().collection("centres").document(centre_id).collection("footfall").document(day)
     .set({"date": day, **body.model_dump()}))
    return ok({"recomputed": recompute_centre(centre_id)})


@router.post("/{centre_id}/attendance")
def log_attendance(centre_id: str, body: AttendanceLog, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    rate = body.doctors_present / body.doctors_total
    (_db().collection("centres").document(centre_id).collection("attendance").document(day)
     .set({"date": day, **body.model_dump(), "attendance_rate": rate}))
    return ok({"recomputed": recompute_centre(centre_id)})


@router.patch("/{centre_id}/tests")
def update_tests(centre_id: str, body: TestsUpdate, user=Depends(get_current_user)):
    require_own_centre(centre_id, user)
    (_db().collection("centres").document(centre_id).collection("tests")
     .document("current").set(body.tests, merge=True))
    return ok({"recomputed": recompute_centre(centre_id)})

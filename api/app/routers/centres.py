"""Centre read endpoints (plan Tasks 1.5 + 3.1 step 1).

Stock is enriched with the live forecast on every read; the other subcollections
are returned as stored (recompute already wrote the derived stock fields back on
the last write — see app.services.recompute).
"""
from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.models.schemas import ok
from app.services.forecasting import forecast_footfall, forecast_stockout

router = APIRouter(prefix="/api/centres", tags=["centres"])


def _db():
    # Lazy import: keeps this module importable without live credentials
    # (firestore_client initialises Firebase at import time).
    from app.firestore_client import db
    return db


@router.get("/{centre_id}/stock")
def get_stock(centre_id: str, user=Depends(get_current_user)):
    out = []
    for doc in _db().collection("centres").document(centre_id).collection("stock").stream():
        m = doc.to_dict() | {"id": doc.id}
        fc = forecast_stockout(m.get("consumption_history", []), m.get("current_stock", 0))
        out.append(m | fc)
    return ok({"medicines": out})


@router.get("/{centre_id}/beds")
def get_beds(centre_id: str, user=Depends(get_current_user)):
    doc = _db().collection("centres").document(centre_id).collection("beds").document("current").get()
    return ok({"beds": doc.to_dict() or {}})


@router.get("/{centre_id}/attendance")
def get_attendance(centre_id: str, days: int = Query(7, ge=1, le=90), user=Depends(get_current_user)):
    from firebase_admin import firestore
    docs = (_db().collection("centres").document(centre_id).collection("attendance")
            .order_by("date", direction=firestore.Query.DESCENDING).limit(days).stream())
    records = [d.to_dict() for d in docs]
    records.sort(key=lambda r: r.get("date", ""))
    return ok({"attendance": records})


@router.get("/{centre_id}/footfall")
def get_footfall(centre_id: str, days: int = Query(30, ge=1, le=90), user=Depends(get_current_user)):
    from firebase_admin import firestore
    docs = (_db().collection("centres").document(centre_id).collection("footfall")
            .order_by("date", direction=firestore.Query.DESCENDING).limit(days).stream())
    records = [d.to_dict() for d in docs]
    records.sort(key=lambda r: r.get("date", ""))
    forecast = forecast_footfall([r.get("count", 0) for r in records])
    return ok({"footfall": records, "forecast": forecast})


@router.get("/{centre_id}/tests")
def get_tests(centre_id: str, user=Depends(get_current_user)):
    doc = _db().collection("centres").document(centre_id).collection("tests").document("current").get()
    return ok({"tests": doc.to_dict() or {}})

"""Centre read endpoints (plan Tasks 1.5 + 3.1 step 1).

Stock is enriched with the live forecast on every read; the other subcollections
are returned as stored (recompute already wrote the derived stock fields back on
the last write — see app.services.recompute).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user, require_role
from app.models.schemas import CentreCreate, ok
from app.services.forecasting import forecast_footfall, forecast_stockout
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/api/centres", tags=["centres"])

_DEFAULT_DISTRICT_AVG_FOOTFALL = 75


def _db():
    # Lazy import: keeps this module importable without live credentials
    # (firestore_client initialises Firebase at import time).
    from app.firestore_client import db
    return db


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


@router.post("")
def create_centre(body: CentreCreate, user=Depends(require_role("district_admin"))):
    from app.seed.demo_data import MEDS, TESTS_ALL, provision_account
    from app.services.language import default_language_for_state
    from app.services.thresholds import derive_stock_levels
    from app.services.recompute import recompute_centre

    district_id = user.get("district_id")
    if not district_id:
        raise HTTPException(status_code=400, detail="Admin account has no district assigned")

    centre_id = _slugify(body.name)
    if not centre_id:
        raise HTTPException(status_code=400, detail="Invalid centre name")

    db = _db()
    cref = db.collection("centres").document(centre_id)
    if cref.get().exists:
        raise HTTPException(status_code=409, detail=f"A centre with id '{centre_id}' already exists")

    siblings = list(db.collection("centres").where(filter=FieldFilter("district_id", "==", district_id)).stream())
    footfalls = [s.to_dict().get("district_avg_footfall", 0) for s in siblings]
    district_avg_footfall = (
        round(sum(footfalls) / len(footfalls)) if footfalls else _DEFAULT_DISTRICT_AVG_FOOTFALL
    )

    dref = db.collection("districts").document(district_id)
    dsnap = dref.get()
    state = (dsnap.to_dict() or {}).get("state", "") if dsnap.exists else ""
    default_language = default_language_for_state(state)
    if dsnap.exists:
        dref.set({"default_language": default_language}, merge=True)

    cref.set({
        "name": body.name, "type": body.type, "district_id": district_id,
        "location": {"block": body.block},
        "district_avg_footfall": district_avg_footfall,
        "expected_daily_patients": body.expected_daily_patients,
        "status": "operational",
        "default_language": default_language,
    })

    for med_id, name, unit, _reorder, _minimum in MEDS:
        levels = derive_stock_levels(med_id, body.expected_daily_patients)
        cref.collection("stock").document(med_id).set({
            "medicine_name": name, "unit": unit,
            "current_stock": 0,
            "reorder_level": levels["reorder_level"],
            "min_threshold": levels["min_threshold"],
            "daily_consumption_avg": levels["estimated_daily_usage"],
            "consumption_history": [],
        })

    cref.collection("beds").document("current").set({"total": 0, "occupied": 0, "available": 0})
    cref.collection("tests").document("current").set({t: True for t in TESTS_ALL})

    result = recompute_centre(centre_id)

    operator = None
    if body.operator_email:
        provisioned = provision_account(body.operator_email, "phc_operator", district_id, centre_id)
        operator = {"email": body.operator_email, "provisioned": provisioned}

    return ok({"centre_id": centre_id, "recomputed": result, "operator": operator})


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

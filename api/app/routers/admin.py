"""Super-admin console API — the configuration surface above district admins.

Everything here is gated on the `super_admin` role and audit-logged, so the
platform's own configuration changes carry the same accountability as an
operator's stock report. Kept deliberately small: users & roles, districts,
per-centre medicine catalogs, and a read-only view of the audit trail.
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as fb_auth
from pydantic import BaseModel, Field
from typing import Literal

from app.deps import require_super_admin
from app.models.schemas import ok
from app.services import audit
from app.services.language import default_language_for_state
from app.services.thresholds import derive_stock_levels
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/api/admin", tags=["admin"])

ROLES = ("district_admin", "phc_operator", "super_admin")


def _db():
    from app.firestore_client import db
    return db


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ---------- overview ----------

@router.get("/overview")
def overview(user=Depends(require_super_admin)):
    db = _db()
    centres = [c.to_dict() | {"id": c.id} for c in db.collection("centres").stream()]
    districts = []
    for d in db.collection("districts").stream():
        dd = d.to_dict() or {}
        districts.append({
            "id": d.id, "name": dd.get("name", d.id), "state": dd.get("state"),
            "default_language": dd.get("default_language", "en"),
            "centres": sum(1 for c in centres if c.get("district_id") == d.id),
        })
    roles = list(_db().collection("roles").stream())
    return ok({"districts": districts, "total_centres": len(centres), "total_users": len(roles)})


@router.get("/centres-list")
def centres_list(user=Depends(require_super_admin)):
    """Lightweight id+name list for pickers."""
    out = [{"id": c.id, "name": (c.to_dict() or {}).get("name", c.id),
            "district_id": (c.to_dict() or {}).get("district_id")}
           for c in _db().collection("centres").stream()]
    return ok({"centres": sorted(out, key=lambda c: c["name"] or "")})


# ---------- users & roles ----------

@router.get("/users")
def list_users(user=Depends(require_super_admin)):
    out = []
    for d in _db().collection("roles").stream():
        r = d.to_dict() or {}
        entry = {"email": d.id, "role": r.get("role"), "centre_id": r.get("centre_id"),
                 "signed_in": False}
        try:
            fb_auth.get_user_by_email(d.id)
            entry["signed_in"] = True
        except fb_auth.UserNotFoundError:
            pass
        except Exception:
            entry["signed_in"] = None  # lookup unavailable; role record still shown
        out.append(entry)
    return ok({"users": sorted(out, key=lambda u: u["email"])})


class UserUpsert(BaseModel):
    email: str = Field(min_length=5, max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["district_admin", "phc_operator", "super_admin"]
    district_id: str | None = None
    centre_id: str | None = None


@router.post("/users")
def upsert_user(body: UserUpsert, user=Depends(require_super_admin)):
    db = _db()
    email = body.email.lower()
    if body.role == "phc_operator":
        if not body.centre_id:
            raise HTTPException(status_code=400, detail="An operator needs a centre.")
        centre = db.collection("centres").document(body.centre_id).get()
        if not centre.exists:
            raise HTTPException(status_code=404, detail="Centre not found.")
        district_id = (centre.to_dict() or {}).get("district_id")
    elif body.role == "district_admin":
        if not body.district_id or not db.collection("districts").document(body.district_id).get().exists:
            raise HTTPException(status_code=400, detail="A district admin needs a valid district.")
        district_id = body.district_id
    else:  # super_admin spans districts
        district_id = None

    from app.seed.demo_data import provision_account
    before = (db.collection("roles").document(email).get().to_dict())
    signed_in = provision_account(email, body.role, district_id,
                                  body.centre_id if body.role == "phc_operator" else None)
    audit.record("admin_role_set", body.centre_id or "-", district_id,
                 audit.actor_from_user(user, channel="admin"),
                 before=before, after={"email": email, "role": body.role,
                                       "centre_id": body.centre_id})
    return ok({"email": email, "role": body.role, "applies_now": signed_in,
               "note": None if signed_in else "Access applies after their first sign-in."})


@router.delete("/users/{email}")
def remove_user(email: str, user=Depends(require_super_admin)):
    email = email.lower()
    if email == (user.get("email") or "").lower():
        raise HTTPException(status_code=400, detail="You cannot remove your own access.")
    db = _db()
    doc = db.collection("roles").document(email).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="No such user record.")
    db.collection("roles").document(email).delete()
    try:
        u = fb_auth.get_user_by_email(email)
        fb_auth.set_custom_user_claims(u.uid, None)
    except fb_auth.UserNotFoundError:
        pass
    audit.record("admin_role_removed", "-", None,
                 audit.actor_from_user(user, channel="admin"),
                 before=doc.to_dict(), after=None, email=email)
    return ok({"removed": email})


# ---------- districts ----------

class DistrictCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=60)


@router.post("/districts")
def create_district(body: DistrictCreate, user=Depends(require_super_admin)):
    db = _db()
    district_id = _slug(body.name)
    ref = db.collection("districts").document(district_id)
    if ref.get().exists:
        raise HTTPException(status_code=409, detail="A district with this name already exists.")
    doc = {"name": body.name, "state": body.state,
           "default_language": default_language_for_state(body.state)}
    ref.set(doc)
    audit.record("admin_district_created", "-", district_id,
                 audit.actor_from_user(user, channel="admin"), before=None, after=doc)
    return ok({"id": district_id, **doc})


# ---------- per-centre medicine catalog ----------

@router.get("/centres/{centre_id}/medicines")
def list_medicines(centre_id: str, user=Depends(require_super_admin)):
    cref = _db().collection("centres").document(centre_id)
    if not cref.get().exists:
        raise HTTPException(status_code=404, detail="Centre not found.")
    meds = [{"id": s.id, **(s.to_dict() or {})} for s in cref.collection("stock").stream()]
    for m in meds:
        m.pop("consumption_history", None)  # config view, not a data dump
    return ok({"medicines": sorted(meds, key=lambda m: m.get("medicine_name") or m["id"])})


class MedicineCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    unit: str = Field(min_length=1, max_length=30)
    min_threshold: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)


@router.post("/centres/{centre_id}/medicines")
def add_medicine(centre_id: str, body: MedicineCreate, user=Depends(require_super_admin)):
    db = _db()
    cref = db.collection("centres").document(centre_id)
    centre = cref.get()
    if not centre.exists:
        raise HTTPException(status_code=404, detail="Centre not found.")
    med_id = _slug(body.name)
    mref = cref.collection("stock").document(med_id)
    if mref.get().exists:
        raise HTTPException(status_code=409, detail="This medicine already exists at this centre.")

    minimum, reorder = body.min_threshold, body.reorder_level
    if minimum is None or reorder is None:
        expected = (centre.to_dict() or {}).get("expected_daily_patients") or 50
        derived = derive_stock_levels(med_id, expected)
        minimum = minimum if minimum is not None else derived["min_threshold"]
        reorder = reorder if reorder is not None else derived["reorder_level"]

    doc = {"medicine_name": body.name, "unit": body.unit, "current_stock": 0,
           "consumption_history": [], "min_threshold": minimum, "reorder_level": reorder}
    mref.set(doc)
    audit.record("admin_medicine_added", centre_id, (centre.to_dict() or {}).get("district_id"),
                 audit.actor_from_user(user, channel="admin"), before=None,
                 after={"id": med_id, "name": body.name, "min": minimum, "reorder": reorder})
    return ok({"id": med_id, **{k: v for k, v in doc.items() if k != "consumption_history"}})


class MedicineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    unit: str | None = Field(default=None, min_length=1, max_length=30)
    min_threshold: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)


@router.patch("/centres/{centre_id}/medicines/{med_id}")
def update_medicine(centre_id: str, med_id: str, body: MedicineUpdate,
                    user=Depends(require_super_admin)):
    db = _db()
    mref = db.collection("centres").document(centre_id).collection("stock").document(med_id)
    before = mref.get().to_dict()
    if before is None:
        raise HTTPException(status_code=404, detail="Medicine not found at this centre.")
    updates = {}
    if body.name is not None:
        updates["medicine_name"] = body.name
    if body.unit is not None:
        updates["unit"] = body.unit
    if body.min_threshold is not None:
        updates["min_threshold"] = body.min_threshold
    if body.reorder_level is not None:
        updates["reorder_level"] = body.reorder_level
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update.")
    mref.update(updates)
    district_id = (db.collection("centres").document(centre_id).get().to_dict() or {}).get("district_id")
    audit.record("admin_medicine_updated", centre_id, district_id,
                 audit.actor_from_user(user, channel="admin"),
                 before={k: before.get(k) for k in updates},
                 after=updates, medicine_id=med_id)
    return ok({"id": med_id, "updated": list(updates)})


@router.delete("/centres/{centre_id}/medicines/{med_id}")
def remove_medicine(centre_id: str, med_id: str, user=Depends(require_super_admin)):
    db = _db()
    mref = db.collection("centres").document(centre_id).collection("stock").document(med_id)
    before = mref.get().to_dict()
    if before is None:
        raise HTTPException(status_code=404, detail="Medicine not found at this centre.")
    mref.delete()
    district_id = (db.collection("centres").document(centre_id).get().to_dict() or {}).get("district_id")
    audit.record("admin_medicine_removed", centre_id, district_id,
                 audit.actor_from_user(user, channel="admin"),
                 before={"id": med_id, "name": before.get("medicine_name")}, after=None)
    return ok({"removed": med_id})


# ---------- audit trail (read-only) ----------

@router.get("/audit")
def audit_trail(centre_id: str | None = None, limit: int = 50,
                user=Depends(require_super_admin)):
    from firebase_admin import firestore
    db = _db()
    limit = max(1, min(limit, 200))
    if centre_id:
        docs = list(db.collection("audit")
                    .where(filter=FieldFilter("centre_id", "==", centre_id))
                    .limit(200).stream())
        entries = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
        entries.sort(key=lambda e: str(e.get("at") or ""), reverse=True)
        entries = entries[:limit]
    else:
        docs = list(db.collection("audit")
                    .order_by("at", direction=firestore.Query.DESCENDING)
                    .limit(limit).stream())
        entries = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    for e in entries:
        at = e.get("at")
        e["at"] = at.isoformat() if hasattr(at, "isoformat") else str(at or "")
    return ok({"entries": entries})

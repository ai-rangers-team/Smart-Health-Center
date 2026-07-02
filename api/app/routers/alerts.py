"""Alert management (plan Task under BE lane — created by AI lane to unblock the
dashboard's Resolve action; DEVIK to own/extend).
"""
from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import firestore

from app.deps import get_current_user
from app.models.schemas import ok

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _db():
    from app.firestore_client import db
    return db


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: str, user=Depends(get_current_user)):
    if user.get("role") != "district_admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    _db().collection("alerts").document(alert_id).update(
        {"resolved": True, "resolved_at": firestore.SERVER_TIMESTAMP}
    )
    return ok({"resolved": True})

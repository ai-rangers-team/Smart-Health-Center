"""Alert resolution (plan file structure: routers/alerts.py # resolve).

Acknowledging an alert is a district-admin action from the dashboard's
AlertsPanel; it flips `resolved` so it drops out of the default alerts query.
Recompute will re-raise the same alert on the next write if the condition persists.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.deps import require_role
from app.models.schemas import ok

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _db():
    from app.firestore_client import db
    return db


@router.post("/{alert_id}/resolve")
def resolve_alert(alert_id: str, user=Depends(require_role("district_admin"))):
    ref = _db().collection("alerts").document(alert_id)
    if not ref.get().exists:
        raise HTTPException(status_code=404, detail="Alert not found")
    ref.update({"resolved": True})
    return ok({"resolved": True})

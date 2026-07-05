"""District overview + alerts list (plan Task 2.6)."""
from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.models.schemas import ok
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/api/district", tags=["dashboard"])


def _db():
    from app.firestore_client import db
    return db


@router.get("/{district_id}/overview")
def overview(district_id: str, user=Depends(get_current_user)):
    db = _db()
    centres = [{"id": d.id, **d.to_dict()} for d in
               db.collection("centres").where(filter=FieldFilter("district_id", "==", district_id)).stream()]

    alert_docs = list(db.collection("alerts").where(filter=FieldFilter("district_id", "==", district_id))
                       .where(filter=FieldFilter("resolved", "==", False)).stream())
    critical = sum(1 for a in alert_docs if a.to_dict().get("severity") == "critical")

    beds_total = beds_available = 0
    for c in centres:
        beds = (db.collection("centres").document(c["id"]).collection("beds")
                .document("current").get().to_dict()) or {}
        beds_total += beds.get("total", 0)
        beds_available += beds.get("available", 0)

    return ok({
        "centres": centres,
        "counts": {"critical": critical, "total_alerts": len(alert_docs), "total_centres": len(centres)},
        "beds": {"total": beds_total, "available": beds_available},
    })


@router.get("/{district_id}/alerts")
def alerts(district_id: str, resolved: bool = Query(False), user=Depends(get_current_user)):
    q = (_db().collection("alerts").where(filter=FieldFilter("district_id", "==", district_id))
         .where(filter=FieldFilter("resolved", "==", resolved)))
    return ok({"alerts": [{"id": d.id, **d.to_dict()} for d in q.stream()]})

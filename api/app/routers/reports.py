"""District period report endpoint (reporting module).

Readable by the district's own admin and by any super admin — the roles a
District Health Officer and the officials above them hold.
"""
from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user, require_district_access
from app.models.schemas import ok
from app.services.reporting import build_district_report

router = APIRouter(prefix="/api/district", tags=["reports"])


@router.get("/{district_id}/report")
def district_report(district_id: str, days: int = Query(30, ge=7, le=92),
                    user=Depends(get_current_user)):
    require_district_access(district_id, user)
    return ok(build_district_report(district_id, days))

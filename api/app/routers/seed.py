"""Demo-data loader (plan Task 1.4), gated behind SEED_ENABLED + district_admin.

Disabled by default (SEED_ENABLED=false) so it can be turned off entirely once
the live demo is seeded (plan Task 4.3), without redeploying the routers.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.deps import require_role
from app.models.schemas import ok
from app.seed import demo_data

router = APIRouter(prefix="/api/seed", tags=["seed"])


def _guard():
    if not settings.seed_enabled:
        raise HTTPException(status_code=403, detail="Seeding disabled")


@router.post("/district")
def seed(_=Depends(_guard), user=Depends(require_role("district_admin"))):
    demo_data.seed_district()
    return ok({"seeded": True})


@router.post("/reset")
def reset(_=Depends(_guard), user=Depends(require_role("district_admin"))):
    demo_data.reset_district()
    return ok({"reset": True})

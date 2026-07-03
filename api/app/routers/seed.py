"""Demo seed endpoints — gated by BOTH the SEED_ENABLED env flag AND the
district_admin role (spec §5). A public reset endpoint on the judged URL could
wipe the demo mid-judging; keep SEED_ENABLED=false in production unless a live
reset is explicitly wanted.
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
    results = demo_data.seed_district()
    accounts = demo_data.provision_accounts()
    return ok({"seeded": True, "centres": results, "accounts": accounts})


@router.post("/reset")
def reset(_=Depends(_guard), user=Depends(require_role("district_admin"))):
    demo_data.wipe_district()
    results = demo_data.seed_district()
    return ok({"reset": True, "centres": results})

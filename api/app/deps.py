"""Auth dependency + role guards (plan Task 1.2 — BE foundation).

NOTE: Created by the AI lane to unblock the AI endpoints. This is BE-owned
foundation — Devik should reconcile/extend rather than recreate.

Roles come from Firebase custom claims (role, district_id, centre_id); a valid
token with no role claim yields role=None (the "not provisioned" state).
"""
from fastapi import Depends, Header, HTTPException


def _user_from_token(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    # Lazy import: firestore_client initialises Firebase at import time, so keep this
    # out of module scope to allow importing deps without live credentials.
    from app.firestore_client import verify_id_token
    try:
        claims = verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "uid": claims.get("uid") or claims.get("user_id"),
        "email": claims.get("email"),
        "role": claims.get("role"),
        "district_id": claims.get("district_id"),
        "centre_id": claims.get("centre_id"),
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    return _user_from_token(authorization)


def require_role(role: str):
    def guard(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return guard


def require_own_centre(centre_id: str, user: dict):
    if user.get("role") != "phc_operator" or user.get("centre_id") != centre_id:
        raise HTTPException(status_code=403, detail="Not your centre")

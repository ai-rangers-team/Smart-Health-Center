"""Append-only audit log for operator-submitted data (anti-fraud accountability).

Every write to a centre's operational data is recorded immutably here with WHO
(uid/email/role/channel), WHEN (server timestamp), and the before/after values.
The `audit` collection is backend-write-only (see firestore.rules), so an operator
cannot alter or delete their own trail. Best-effort: a failure here is logged but
never blocks the underlying report.
"""
import logging

from firebase_admin import firestore


def _db():
    from app.firestore_client import db
    return db


def actor_from_user(user: dict, channel: str = "app") -> dict:
    """Identity to stamp on a report — from the authenticated custom claims."""
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "role": user.get("role"),
        "channel": channel,
    }


def record(action: str, centre_id: str, district_id: str | None, actor: dict,
           before, after, **extra) -> None:
    """Append one immutable audit entry. Never raises — accountability must not
    break the report it accompanies (the underlying write has already happened)."""
    try:
        _db().collection("audit").add({
            "action": action,
            "centre_id": centre_id,
            "district_id": district_id,
            "actor": actor,
            "before": before,
            "after": after,
            **extra,
            "at": firestore.SERVER_TIMESTAMP,
        })
    except Exception:
        logging.getLogger("audit").exception("audit record failed: %s %s", action, centre_id)

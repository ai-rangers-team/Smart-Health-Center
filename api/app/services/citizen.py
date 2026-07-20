"""Citizen corroboration (anti-fraud layer 3).

Breaks the single-source-of-truth: citizens scanning the public QR poster report
whether a doctor was actually present and whether they got their medicine. When
enough citizen reports contradict the operator's own claim, we raise an advisory
`CITIZEN_DISPUTE` alert for the district officer — an independent ground-truth
check the operator cannot fake.

`evaluate_disputes` is the pure decision logic (unit-tested); `refresh_disputes`
does the Firestore I/O and (re)writes the dispute alert idempotently, so it can be
called both when a citizen submits feedback and during recompute-on-write.
"""
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

DISPUTE_THRESHOLD = 3   # this many contradicting citizen reports raises a flag
_RECENT = 20            # look at the most recent N reports


def _db():
    from app.firestore_client import db
    return db


def evaluate_disputes(feedbacks, *, doctor_claimed_present, medicines_claimed_available):
    """feedbacks: recent [{doctor_present: bool, medicine_available: bool}].
    Returns dispute flag dicts only where citizens contradict the operator's claim."""
    no_doctor = sum(1 for f in feedbacks if f.get("doctor_present") is False)
    no_med = sum(1 for f in feedbacks if f.get("medicine_available") is False)
    flags = []
    if doctor_claimed_present and no_doctor >= DISPUTE_THRESHOLD:
        flags.append({
            "check_type": "DOCTOR_ABSENCE", "count": no_doctor,
            "message": (f"{no_doctor} citizens report no doctor present today, but the "
                        f"centre reports a doctor on duty"),
        })
    if medicines_claimed_available and no_med >= DISPUTE_THRESHOLD:
        flags.append({
            "check_type": "MEDICINE_UNAVAILABLE", "count": no_med,
            "message": (f"{no_med} citizens report medicine unavailable, but the centre "
                        f"reports stock in hand"),
        })
    return flags


def refresh_disputes(centre_id: str) -> None:
    """Re-evaluate citizen disputes for a centre and (re)write its CITIZEN_DISPUTE
    alert idempotently. Best-effort — never breaks the caller."""
    try:
        db = _db()
        cref = db.collection("centres").document(centre_id)
        centre = cref.get().to_dict() or {}

        # NB: no order_by here — where + order_by on different fields would need a
        # composite Firestore index. Count-based threshold doesn't need ordering; a
        # time-windowed "recent" view is a roadmap item (add the index then).
        feedbacks = [f.to_dict() for f in db.collection("citizen_feedback")
                     .where(filter=FieldFilter("centre_id", "==", centre_id))
                     .limit(_RECENT).stream()]

        att = list(cref.collection("attendance")
                   .order_by("date", direction=firestore.Query.DESCENDING).limit(1).stream())
        doctor_claimed = bool(att) and (att[0].to_dict().get("doctors_present", 0) or 0) > 0
        stock = [s.to_dict() for s in cref.collection("stock").stream()]
        med_claimed = any((m.get("current_stock", 0) or 0) > 0 for m in stock)

        flags = evaluate_disputes(feedbacks, doctor_claimed_present=doctor_claimed,
                                  medicines_claimed_available=med_claimed)

        for a in (db.collection("alerts")
                  .where(filter=FieldFilter("centre_id", "==", centre_id))
                  .where(filter=FieldFilter("type", "==", "CITIZEN_DISPUTE"))
                  .where(filter=FieldFilter("resolved", "==", False)).stream()):
            a.reference.delete()

        base = {"centre_id": centre_id, "centre_name": centre.get("name"),
                "district_id": centre.get("district_id"), "resolved": False}
        for fl in flags:
            db.collection("alerts").add({**base, "type": "CITIZEN_DISPUTE", "severity": "high",
                                         **fl, "created_at": firestore.SERVER_TIMESTAMP})
    except Exception:
        import logging
        logging.getLogger("citizen").exception("refresh_disputes failed for %s", centre_id)

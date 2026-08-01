"""District period report — the numbers a District Health Officer forwards upward.

Aggregates what the system already records (footfall/attendance history, stock
forecasts, alerts, citizen feedback) into one weekly/monthly report per district.
Read-only: nothing here writes. The pure helpers are unit-tested; `build_district_report`
does the Firestore I/O.

Reporting compliance (days a centre actually filed its daily report) is derived
from footfall history — the one entry every daily report contains.
"""
from datetime import date, timedelta

from google.cloud.firestore_v1.base_query import FieldFilter


def _db():
    from app.firestore_client import db
    return db


def period_bounds(days: int, today: date | None = None) -> tuple[str, str]:
    """Inclusive ISO date bounds for the trailing N-day window."""
    end = today or date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def compliance(days_reported: int, days_in_period: int) -> int:
    """Reporting compliance as a whole percentage, capped to 100."""
    if days_in_period <= 0:
        return 0
    return min(100, round(100 * days_reported / days_in_period))


def classify_stock(stock_docs: list[dict]) -> dict:
    """Coarse risk profile of a centre's current stock."""
    out = low = watch = 0
    for m in stock_docs:
        current = m.get("current_stock", 0) or 0
        days_left = m.get("days_remaining")
        minimum = m.get("min_threshold") or 0
        if current <= 0:
            out += 1
        elif (days_left is not None and days_left <= 7) or (minimum and current <= minimum):
            low += 1
        elif days_left is not None and days_left <= 14:
            watch += 1
    return {"out": out, "low": low, "watch": watch}


def build_district_report(district_id: str, days: int = 30) -> dict:
    db = _db()
    start, end = period_bounds(days)

    district = (db.collection("districts").document(district_id).get().to_dict()) or {}
    centres = [{"id": d.id, **(d.to_dict() or {})} for d in
               db.collection("centres")
               .where(filter=FieldFilter("district_id", "==", district_id)).stream()]

    # Active alerts grouped once for the whole district
    alert_docs = [a.to_dict() for a in
                  db.collection("alerts")
                  .where(filter=FieldFilter("district_id", "==", district_id))
                  .where(filter=FieldFilter("resolved", "==", False)).stream()]
    alerts_by_centre: dict[str, dict] = {}
    alerts_by_type: dict[str, int] = {}
    for a in alert_docs:
        t = a.get("type", "OTHER")
        alerts_by_type[t] = alerts_by_type.get(t, 0) + 1
        c = alerts_by_centre.setdefault(a.get("centre_id"), {})
        c[t] = c.get(t, 0) + 1

    rows = []
    total_patients = 0
    attendance_rates = []
    for c in centres:
        cref = db.collection("centres").document(c["id"])

        foot = [f.to_dict() for f in cref.collection("footfall")
                .where(filter=FieldFilter("date", ">=", start)).stream()]
        patients = sum(f.get("count", 0) or 0 for f in foot)
        days_reported = len({f.get("date") for f in foot if f.get("date")})

        att = [a.to_dict() for a in cref.collection("attendance")
               .where(filter=FieldFilter("date", ">=", start)).stream()]
        rates = [a.get("attendance_rate") for a in att if a.get("attendance_rate") is not None]
        avg_rate = round(100 * sum(rates) / len(rates)) if rates else None
        if avg_rate is not None:
            attendance_rates.append(avg_rate)

        stock = [s.to_dict() for s in cref.collection("stock").stream()]

        total_patients += patients
        rows.append({
            "id": c["id"],
            "name": c.get("name"),
            "type": c.get("type"),
            "status": c.get("status"),
            "performance_score": c.get("performance_score"),
            "patients": patients,
            "avg_patients_per_day": round(patients / days) if days else 0,
            "days_reported": days_reported,
            "compliance_pct": compliance(days_reported, days),
            "avg_attendance_pct": avg_rate,
            "stock": classify_stock(stock),
            "alerts": alerts_by_centre.get(c["id"], {}),
        })
    rows.sort(key=lambda r: (r["compliance_pct"], r.get("performance_score") or 0))

    # Citizen participation in the period (date field is an ISO string)
    feedback = [f.to_dict() for f in
                db.collection("citizen_feedback")
                .where(filter=FieldFilter("district_id", "==", district_id)).stream()]
    feedback_in_period = [f for f in feedback if (f.get("date") or "9999") >= start]

    return {
        "district_id": district_id,
        "district_name": district.get("name", district_id),
        "period": {"from": start, "to": end, "days": days},
        "totals": {
            "centres": len(centres),
            "patients": total_patients,
            "avg_attendance_pct": (round(sum(attendance_rates) / len(attendance_rates))
                                   if attendance_rates else None),
            "active_alerts": len(alert_docs),
            "centres_fully_compliant": sum(1 for r in rows if r["compliance_pct"] >= 90),
        },
        "alerts_by_type": alerts_by_type,
        "citizen_feedback": {
            "reports_in_period": len(feedback_in_period),
            "disputes_active": alerts_by_type.get("CITIZEN_DISPUTE", 0),
            "integrity_flags_active": alerts_by_type.get("DATA_INTEGRITY", 0),
        },
        "centres": rows,
    }

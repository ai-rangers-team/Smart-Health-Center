"""Template-based alert generation (spec Task 2.4).

Deterministic, Gemini-free — alerts on the write path must never depend on an
external model call. Gemini enriches alerts elsewhere (narratives, briefings);
this module decides WHETHER an alert fires and what its raw message is.
"""

ESSENTIAL = ("malaria", "tb", "pregnancy")


def build_alerts(centre_id, centre_name, district_id, stock_forecasts, beds, attendance_rate, tests):
    alerts = []
    base = {"centre_id": centre_id, "centre_name": centre_name,
            "district_id": district_id, "resolved": False}

    for m in stock_forecasts:
        if m["severity"] == "critical":
            alerts.append(base | {
                "type": "STOCKOUT_CRITICAL", "severity": "critical",
                "medicine_name": m["medicine_name"], "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} will stock out in {m["days_remaining"]} days — reorder now',
            })
        elif m["severity"] == "high":
            alerts.append(base | {
                "type": "STOCKOUT_WARNING", "severity": "high",
                "medicine_name": m["medicine_name"], "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} low: {m["days_remaining"]} days remaining',
            })

    if beds and beds.get("available", 1) == 0:
        alerts.append(base | {"type": "BED_CRISIS", "severity": "high", "message": "No beds available"})

    if attendance_rate is not None and attendance_rate < 0.6:
        alerts.append(base | {
            "type": "ATTENDANCE_LOW", "severity": "medium",
            "message": f"Doctor attendance {attendance_rate * 100:.0f}% — below 60%",
        })

    for t in ESSENTIAL:
        if tests and tests.get(t) is False:
            alerts.append(base | {
                "type": "TEST_UNAVAILABLE", "severity": "medium",
                "message": f"Essential test unavailable: {t}",
            })

    return alerts

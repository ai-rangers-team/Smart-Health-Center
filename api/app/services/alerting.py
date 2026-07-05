"""Template-based alert generation (spec §3 recompute-on-write, plan task 2.4).

Deterministic — NO Gemini on this path. These alerts are written synchronously
during operator saves, so the live demo moment can never be broken by an
external API. The frontend re-renders the text per-language from the structured
fields; `message` is the English canonical record.
"""

ESSENTIAL = ("malaria", "tb", "pregnancy")


def build_alerts(centre_id, centre_name, district_id, stock_forecasts,
                 beds, attendance_rate, tests):
    alerts = []
    base = {
        "centre_id": centre_id,
        "centre_name": centre_name,
        "district_id": district_id,
        "resolved": False,
    }

    for m in stock_forecasts:
        if m["severity"] == "critical":
            alerts.append(base | {
                "type": "STOCKOUT_CRITICAL",
                "severity": "critical",
                "medicine_name": m["medicine_name"],
                "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} will stock out in '
                           f'{m["days_remaining"]} days — reorder now',
            })
        elif m["severity"] == "high":
            alerts.append(base | {
                "type": "STOCKOUT_WARNING",
                "severity": "high",
                "medicine_name": m["medicine_name"],
                "days_remaining": m["days_remaining"],
                "message": f'{m["medicine_name"]} low: '
                           f'{m["days_remaining"]} days remaining',
            })
        elif m.get("days_remaining", 0) >= 999:
            # Cold start: no consumption history yet, so no forecast exists.
            # Fall back to the admin-set stock levels (days_remaining=None
            # signals "threshold-based, not forecast-based" to the UI).
            stock = m.get("current_stock", 0)
            minimum = m.get("min_threshold", 0)
            if stock <= 0:
                alerts.append(base | {
                    "type": "STOCKOUT_CRITICAL",
                    "severity": "critical",
                    "medicine_name": m["medicine_name"],
                    "days_remaining": None,
                    "message": f'{m["medicine_name"]} is out of stock',
                })
            elif minimum and stock <= minimum:
                alerts.append(base | {
                    "type": "STOCKOUT_WARNING",
                    "severity": "high",
                    "medicine_name": m["medicine_name"],
                    "days_remaining": None,
                    "message": f'{m["medicine_name"]} below minimum stock level '
                               f'({stock} of {minimum})',
                })

    # Only meaningful once a bed capacity is configured — a freshly onboarded
    # centre with total=0 must not fire a false crisis.
    if beds and beds.get("total", 0) > 0 and beds.get("available", 1) == 0:
        alerts.append(base | {
            "type": "BED_CRISIS",
            "severity": "high",
            "message": "No beds available",
        })

    if attendance_rate is not None and attendance_rate < 0.6:
        alerts.append(base | {
            "type": "ATTENDANCE_LOW",
            "severity": "medium",
            "message": f"Doctor attendance {attendance_rate * 100:.0f}% — below 60%",
        })

    for t in ESSENTIAL:
        if tests and tests.get(t) is False:
            alerts.append(base | {
                "type": "TEST_UNAVAILABLE",
                "severity": "medium",
                "test_name": t,
                "message": f"Essential test unavailable: {t}",
            })

    return alerts

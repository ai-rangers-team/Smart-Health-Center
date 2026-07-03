from app.services.alerting import build_alerts


def test_critical_stockout_alert():
    alerts = build_alerts(
        "phc_mulshi", "PHC Mulshi", "pune_rural",
        [{"medicine_name": "Paracetamol 500mg", "days_remaining": 3, "severity": "critical"}],
        beds={"available": 5}, attendance_rate=0.8,
        tests={"malaria": True, "tb": True, "pregnancy": True},
    )
    a = [x for x in alerts if x["type"] == "STOCKOUT_CRITICAL"]
    assert a and "Paracetamol" in a[0]["message"] and a[0]["resolved"] is False


def test_high_stockout_warning():
    alerts = build_alerts(
        "c", "C", "d",
        [{"medicine_name": "ORS", "days_remaining": 6, "severity": "high"}],
        beds={"available": 5}, attendance_rate=0.9,
        tests={"malaria": True, "tb": True, "pregnancy": True},
    )
    types = {x["type"] for x in alerts}
    assert types == {"STOCKOUT_WARNING"}


def test_bed_crisis_and_test_unavailable():
    alerts = build_alerts(
        "c", "C", "d", [], beds={"available": 0}, attendance_rate=0.9,
        tests={"malaria": False, "tb": True, "pregnancy": True},
    )
    types = {x["type"] for x in alerts}
    assert "BED_CRISIS" in types and "TEST_UNAVAILABLE" in types


def test_no_alerts_when_all_healthy():
    alerts = build_alerts(
        "c", "C", "d",
        [{"medicine_name": "X", "days_remaining": 30, "severity": "low"}],
        beds={"available": 5}, attendance_rate=0.9,
        tests={"malaria": True, "tb": True, "pregnancy": True},
    )
    assert alerts == []


def test_low_attendance_alert():
    alerts = build_alerts("c", "C", "d", [], beds=None, attendance_rate=0.52, tests=None)
    types = {x["type"] for x in alerts}
    assert types == {"ATTENDANCE_LOW"}

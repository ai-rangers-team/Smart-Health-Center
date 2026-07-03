from app.services.alerting import build_alerts


def test_critical_stockout_alert():
    alerts = build_alerts(
        "phc_mulshi", "PHC Mulshi", "pune_rural",
        [{"medicine_name": "Paracetamol 500mg", "days_remaining": 3, "severity": "critical"}],
        beds={"available": 5},
        attendance_rate=0.8,
        tests={"malaria": True, "tb": True, "pregnancy": True},
    )
    a = [x for x in alerts if x["type"] == "STOCKOUT_CRITICAL"]
    assert a and "Paracetamol" in a[0]["message"] and a[0]["resolved"] is False
    assert a[0]["days_remaining"] == 3 and a[0]["severity"] == "critical"


def test_high_stockout_becomes_warning():
    alerts = build_alerts(
        "c", "C", "d",
        [{"medicine_name": "ORS Sachets", "days_remaining": 5, "severity": "high"}],
        beds={"available": 2}, attendance_rate=0.9, tests={},
    )
    assert [x for x in alerts if x["type"] == "STOCKOUT_WARNING"]


def test_bed_crisis_and_test_unavailable():
    alerts = build_alerts(
        "c", "C", "d", [],
        beds={"available": 0}, attendance_rate=0.9,
        tests={"malaria": False, "tb": True, "pregnancy": True},
    )
    types = {x["type"] for x in alerts}
    assert "BED_CRISIS" in types and "TEST_UNAVAILABLE" in types


def test_low_attendance_alert():
    alerts = build_alerts("c", "C", "d", [], beds={"available": 3},
                          attendance_rate=0.5, tests={})
    assert [x for x in alerts if x["type"] == "ATTENDANCE_LOW"]


def test_healthy_centre_no_alerts():
    alerts = build_alerts(
        "c", "C", "d",
        [{"medicine_name": "Metformin", "days_remaining": 18, "severity": "low"}],
        beds={"available": 3}, attendance_rate=0.9,
        tests={"malaria": True, "tb": True, "pregnancy": True},
    )
    assert alerts == []

from app.services.scoring import compute_performance_score


def _centre(**overrides):
    base = {
        "avg_attendance_rate": 0.9,
        "avg_footfall": 80,
        "district_avg_footfall": 78,
        "critical_stockouts": 0,
        "bed_occupancy_rate": 0.6,
        "essential_tests_unavailable": 0,
    }
    base.update(overrides)
    return base


def test_healthy_centre_scores_high():
    r = compute_performance_score(_centre())
    assert r["score"] >= 90 and r["status"] == "operational"


def test_velhe_flagged_underperforming():
    r = compute_performance_score(_centre(
        avg_attendance_rate=0.52, avg_footfall=40, critical_stockouts=1,
        bed_occupancy_rate=0.2, essential_tests_unavailable=1))
    assert r["status"] in ("critical", "under_resourced")
    assert any("attendance" in f.lower() for f in r["flags"])


def test_score_never_negative():
    r = compute_performance_score(_centre(
        avg_attendance_rate=0.0, avg_footfall=0, critical_stockouts=5,
        bed_occupancy_rate=0.0, essential_tests_unavailable=3))
    assert r["score"] == 0 and r["status"] == "critical"


def test_test_unavailability_produces_flag():
    r = compute_performance_score(_centre(essential_tests_unavailable=2))
    assert any("test" in f.lower() for f in r["flags"])

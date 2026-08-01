from datetime import date

from app.services.reporting import classify_stock, compliance, period_bounds


def test_period_bounds_inclusive():
    start, end = period_bounds(7, today=date(2026, 8, 1))
    assert (start, end) == ("2026-07-26", "2026-08-01")


def test_compliance_caps_and_rounds():
    assert compliance(30, 30) == 100
    assert compliance(22, 30) == 73
    assert compliance(31, 30) == 100  # double report days can't exceed 100
    assert compliance(0, 30) == 0
    assert compliance(5, 0) == 0


def test_classify_stock_buckets():
    stock = [
        {"current_stock": 0},                                        # out
        {"current_stock": 40, "days_remaining": 5},                  # low (days)
        {"current_stock": 10, "min_threshold": 20},                  # low (threshold)
        {"current_stock": 200, "days_remaining": 12},                # watch
        {"current_stock": 500, "days_remaining": 60},                # fine
    ]
    assert classify_stock(stock) == {"out": 1, "low": 2, "watch": 1}


def test_classify_stock_threshold_only_cold_start():
    # New centre: no forecast yet (days_remaining None) — thresholds still classify.
    stock = [{"current_stock": 3, "min_threshold": 10, "days_remaining": None}]
    assert classify_stock(stock) == {"out": 0, "low": 1, "watch": 0}

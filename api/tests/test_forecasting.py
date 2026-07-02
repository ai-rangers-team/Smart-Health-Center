from app.services import forecasting as f


def test_ewma_weights_recent_higher():
    assert f.ewma([10, 10, 10]) == 10
    assert f.ewma([0, 0, 20]) > f.ewma([20, 0, 0])


def test_ewma_empty_series():
    assert f.ewma([]) == 0.0


def test_stockout_severity_critical_at_three_days():
    r = f.forecast_stockout([10, 10, 10], current_stock=25)  # ~2.5 days
    assert r["severity"] == "critical"
    assert r["days_remaining"] <= 3


def test_stockout_low_when_ample():
    r = f.forecast_stockout([10, 10, 10], current_stock=1000)
    assert r["severity"] == "low"


def test_stockout_zero_consumption_is_low():
    r = f.forecast_stockout([0, 0, 0], current_stock=100)
    assert r["severity"] == "low"
    assert r["days_remaining"] == 999.0


def test_footfall_trend_falling():
    r = f.forecast_footfall([80, 70, 60, 50, 40])
    assert r["trend"] == "falling"


def test_footfall_trend_rising():
    r = f.forecast_footfall([40, 50, 60, 70, 90])
    assert r["trend"] == "rising"

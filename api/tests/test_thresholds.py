from app.services.thresholds import derive_stock_levels


def test_levels_scale_with_expected_patients():
    small = derive_stock_levels("paracetamol", expected_daily_patients=40)
    big = derive_stock_levels("paracetamol", expected_daily_patients=120)
    assert big["min_threshold"] > small["min_threshold"]
    assert big["reorder_level"] > big["min_threshold"]


def test_levels_reasonable_for_typical_phc():
    # ~80 patients/day, paracetamol ~0.5/patient -> ~40/day usage:
    # min ≈ 3-day buffer (~120), reorder ≈ a week (~280)
    lv = derive_stock_levels("paracetamol", expected_daily_patients=80)
    assert 100 <= lv["min_threshold"] <= 150
    assert 250 <= lv["reorder_level"] <= 320
    assert lv["estimated_daily_usage"] > 0


def test_unknown_medicine_or_no_estimate_falls_back_to_defaults():
    lv = derive_stock_levels("paracetamol", expected_daily_patients=None)
    assert lv["min_threshold"] == 100 and lv["reorder_level"] == 200  # MEDS defaults
    lv2 = derive_stock_levels("unknown_med", expected_daily_patients=80)
    assert lv2["min_threshold"] > 0

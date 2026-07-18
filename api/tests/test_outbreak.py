from app.services.outbreak import detect_outbreaks, is_surge


def test_is_surge_needs_history_and_baseline():
    assert is_surge([20])[0] is False               # too short
    assert is_surge([1, 1, 1, 3])[0] is False       # baseline below noise floor
    assert is_surge([10, 10, 10, 30])[0] is True    # 3x jump on a real baseline
    assert is_surge([10, 10, 10, 12])[0] is False   # mild rise, not a surge


def test_single_centre_surge_is_not_a_cluster():
    centres = [
        {"name": "A", "footfall": [40, 41, 40, 42], "consumption": {"ors": [24, 25, 24, 90]}},
        {"name": "B", "footfall": [30, 31, 30, 31], "consumption": {"ors": [20, 21, 20, 21]}},
    ]
    assert detect_outbreaks(centres) == []  # only A surges -> below MIN_CLUSTER


def test_cluster_surge_flags_indication_and_centres():
    centres = [
        {"name": "PHC Mulshi", "footfall": [40, 41, 40, 42], "consumption": {"ors": [24, 25, 24, 90]}},
        {"name": "PHC Haveli", "footfall": [30, 31, 30, 31], "consumption": {"ors": [20, 21, 20, 80]}},
        {"name": "PHC Bhor", "footfall": [30, 31, 30, 31], "consumption": {"ors": [20, 21, 20, 21]}},
    ]
    out = detect_outbreaks(centres)
    assert len(out) == 1
    o = out[0]
    assert o["signal"] == "ors"
    assert o["indication"] == "diarrhoeal illness"
    assert set(o["centres"]) == {"PHC Mulshi", "PHC Haveli"}
    assert o["centre_count"] == 2
    assert o["severity"] == "medium"  # 2 centres; 3+ would be high


def test_non_marker_medicine_is_ignored():
    centres = [
        {"name": "A", "footfall": [1, 1, 1, 1], "consumption": {"metformin": [10, 10, 10, 90]}},
        {"name": "B", "footfall": [1, 1, 1, 1], "consumption": {"metformin": [10, 10, 10, 90]}},
    ]
    assert detect_outbreaks(centres) == []  # metformin isn't a marker

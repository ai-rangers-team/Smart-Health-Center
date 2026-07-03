from app.services.redistribution import compute_redistribution


def test_surplus_flows_to_deficit():
    centres = [
        {"id": "chc", "name": "CHC", "stock": {
            "para": {"current_stock": 900, "reorder_level": 200, "daily_avg": 30, "days_remaining": 30}}},
        {"id": "mulshi", "name": "Mulshi", "stock": {
            "para": {"current_stock": 120, "reorder_level": 200, "daily_avg": 40, "days_remaining": 3}}},
    ]
    recs = compute_redistribution(centres)
    assert len(recs) == 1
    assert recs[0]["from_centre"] == "CHC" and recs[0]["to_centre"] == "Mulshi"
    assert recs[0]["quantity"] > 0
    assert recs[0]["urgency"] == "critical"


def test_no_surplus_no_recommendation():
    centres = [
        {"id": "a", "name": "A", "stock": {
            "para": {"current_stock": 100, "reorder_level": 200, "daily_avg": 40, "days_remaining": 2}}},
        {"id": "b", "name": "B", "stock": {
            "para": {"current_stock": 90, "reorder_level": 200, "daily_avg": 40, "days_remaining": 2}}},
    ]
    assert compute_redistribution(centres) == []


def test_donor_not_drained_below_buffer():
    # donor has modest surplus; ensure we never transfer more than (stock - reorder_level)
    centres = [
        {"id": "chc", "name": "CHC", "stock": {
            "para": {"current_stock": 400, "reorder_level": 200, "daily_avg": 30, "days_remaining": 13}}},
        {"id": "x", "name": "X", "stock": {
            "para": {"current_stock": 40, "reorder_level": 200, "daily_avg": 40, "days_remaining": 1}}},
    ]
    recs = compute_redistribution(centres)
    assert recs and recs[0]["quantity"] <= 200  # 400 - 200 buffer


def test_never_recommends_a_centre_transfer_to_itself():
    # A centre can hold ample raw quantity (surplus by the buffer rule) while still
    # burning through it fast enough to be short on runway (deficit by days_remaining)
    # for the SAME medicine — it must never be matched to itself.
    centres = [
        {"id": "ambegaon", "name": "Ambegaon", "stock": {
            "iron_folic": {"current_stock": 450, "reorder_level": 100, "daily_avg": 90, "days_remaining": 5}}},
    ]
    assert compute_redistribution(centres) == []


def test_self_match_skipped_in_favour_of_other_donor():
    centres = [
        {"id": "ambegaon", "name": "Ambegaon", "stock": {
            "iron_folic": {"current_stock": 450, "reorder_level": 100, "daily_avg": 90, "days_remaining": 5}}},
        {"id": "chc", "name": "CHC", "stock": {
            "iron_folic": {"current_stock": 900, "reorder_level": 100, "daily_avg": 10, "days_remaining": 90}}},
    ]
    recs = compute_redistribution(centres)
    assert len(recs) == 1
    assert recs[0]["from_centre"] == "CHC" and recs[0]["to_centre"] == "Ambegaon"

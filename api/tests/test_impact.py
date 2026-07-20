from app.services.impact import EMERGENCY_PREMIUM, UNIT_COST, compute_impact


def test_counts_only_forecast_based_early_flags():
    forecasts = [
        {"id": "paracetamol", "severity": "critical", "days_remaining": 3.0},
        {"id": "ors", "severity": "high", "days_remaining": 6.0},
        {"id": "ifa", "severity": "low", "days_remaining": 40.0},      # not at risk
        {"id": "amoxicillin", "severity": "critical", "days_remaining": None},  # cold-start
        {"id": "metformin", "severity": "critical", "days_remaining": 0},        # already out
    ]
    out = compute_impact(forecasts, [])
    assert out["stockouts_flagged_early"] == 2
    assert out["avg_lead_time_days"] == 4.5  # (3 + 6) / 2


def test_redistribution_value_and_patients():
    recs = [
        {"medicine_id": "paracetamol", "quantity": 100},  # usage 0.5 -> 200 patient-days
        {"medicine_id": "ors", "quantity": 60},           # usage 0.3 -> 200 patient-days
    ]
    out = compute_impact([], recs)
    assert out["units_redistributed"] == 160
    assert out["patients_protected"] == 400
    assert out["transfers_confirmed"] is False  # opportunity, not yet delivered
    expected_rupees = round(
        100 * UNIT_COST["paracetamol"] * EMERGENCY_PREMIUM
        + 60 * UNIT_COST["ors"] * EMERGENCY_PREMIUM
    )
    assert out["rupees_saved"] == expected_rupees


def test_confirmed_transfers_override_planned_opportunity():
    # Plan proposed 100 paracetamol, but the recipient only confirmed 40 received.
    recs = [{"medicine_id": "paracetamol", "quantity": 100}]
    confirmed = [{"medicine_id": "paracetamol", "received_qty": 40}]
    out = compute_impact([], recs, confirmed=confirmed)
    assert out["units_redistributed"] == 40           # delivered, not planned
    assert out["patients_protected"] == 80            # 40 / 0.5
    assert out["transfers_confirmed"] is True


def test_empty_inputs_are_zeroed():
    out = compute_impact([], [])
    assert out == {
        "stockouts_flagged_early": 0,
        "avg_lead_time_days": 0.0,
        "units_redistributed": 0,
        "patients_protected": 0,
        "rupees_saved": 0,
        "transfers_confirmed": False,
    }

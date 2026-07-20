from app.services.citizen import DISPUTE_THRESHOLD, evaluate_disputes


def _fb(doctor, medicine, n):
    return [{"doctor_present": doctor, "medicine_available": medicine} for _ in range(n)]


def test_no_dispute_when_citizens_agree_with_operator():
    fbs = _fb(True, True, 5)
    assert evaluate_disputes(fbs, doctor_claimed_present=True,
                             medicines_claimed_available=True) == []


def test_doctor_dispute_when_enough_contradict_claim():
    fbs = _fb(False, True, DISPUTE_THRESHOLD)
    flags = evaluate_disputes(fbs, doctor_claimed_present=True,
                              medicines_claimed_available=True)
    assert [f["check_type"] for f in flags] == ["DOCTOR_ABSENCE"]
    assert flags[0]["count"] == DISPUTE_THRESHOLD


def test_below_threshold_does_not_flag():
    fbs = _fb(False, False, DISPUTE_THRESHOLD - 1)
    assert evaluate_disputes(fbs, doctor_claimed_present=True,
                             medicines_claimed_available=True) == []


def test_no_dispute_if_operator_also_reports_absent():
    # Operator honestly reports no doctor -> citizens agreeing is not a dispute.
    fbs = _fb(False, True, 5)
    assert evaluate_disputes(fbs, doctor_claimed_present=False,
                             medicines_claimed_available=True) == []


def test_medicine_dispute():
    fbs = _fb(True, False, 4)
    flags = evaluate_disputes(fbs, doctor_claimed_present=True,
                              medicines_claimed_available=True)
    assert [f["check_type"] for f in flags] == ["MEDICINE_UNAVAILABLE"]

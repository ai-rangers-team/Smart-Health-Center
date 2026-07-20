from app.services.integrity import check_integrity


def _base(**over):
    args = dict(medicines=[], avg_footfall=80, foot_counts=[80, 79, 81, 78, 82, 80],
                avg_attendance=0.8)
    args.update(over)
    return args


def test_honest_centre_produces_no_flags():
    # Normal footfall + normal per-patient consumption + wobbling counts -> clean.
    meds = [{"medicine_name": "Paracetamol 500mg", "daily_rate": 40}]  # 40/80 = 0.5/patient
    assert check_integrity(**_base(medicines=meds)) == []


def test_consumption_without_patients_flags_diversion():
    # 200 units/day but only 40 patients -> 5 units/patient, far above ceiling.
    meds = [{"medicine_name": "Paracetamol 500mg", "daily_rate": 200}]
    flags = check_integrity(**_base(medicines=meds, avg_footfall=40))
    assert len(flags) == 1
    assert flags[0]["check_type"] == "CONSUMPTION_WITHOUT_PATIENTS"
    assert flags[0]["medicine_name"] == "Paracetamol 500mg"
    assert flags[0]["observed"] == 5.0


def test_trivial_volume_medicine_is_ignored():
    # High per-patient ratio but tiny absolute rate -> not flagged (noise floor).
    meds = [{"medicine_name": "Amoxicillin 250mg", "daily_rate": 8}]
    assert check_integrity(**_base(medicines=meds, avg_footfall=1)) == []


def test_flatline_footfall_flags_fabrication():
    flags = check_integrity(**_base(foot_counts=[70, 70, 70, 70, 70, 70]))
    assert any(f["check_type"] == "FLATLINE_FOOTFALL" for f in flags)
    # a single varying value breaks the flatline
    assert not any(f["check_type"] == "FLATLINE_FOOTFALL"
                   for f in check_integrity(**_base(foot_counts=[70, 70, 70, 70, 70, 71])))


def test_ghost_staffing_flags_full_attendance_no_patients():
    flags = check_integrity(**_base(avg_attendance=1.0, avg_footfall=3,
                                    foot_counts=[3, 4, 2, 3, 5, 3]))
    assert any(f["check_type"] == "GHOST_STAFFING" for f in flags)
    # normal footfall with full attendance is fine
    assert not any(f["check_type"] == "GHOST_STAFFING"
                   for f in check_integrity(**_base(avg_attendance=1.0, avg_footfall=80)))

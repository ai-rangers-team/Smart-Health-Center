from app.services.sms_report import parse_sms_report

_CATALOG = [
    {"id": "paracetamol", "name": "Paracetamol 500mg"},
    {"id": "ors", "name": "ORS Sachets"},
    {"id": "ifa", "name": "Iron + Folic Acid"},
    {"id": "metformin", "name": "Metformin 500mg"},
]


def test_parses_codes_and_numbers():
    out = parse_sms_report("PARA 120 ORS 40 IFA 300", _CATALOG)
    assert out["unmatched"] == []
    assert out["updates"] == [
        {"medicine_id": "paracetamol", "medicine_name": "Paracetamol 500mg", "current_stock": 120},
        {"medicine_id": "ors", "medicine_name": "ORS Sachets", "current_stock": 40},
        {"medicine_id": "ifa", "medicine_name": "Iron + Folic Acid", "current_stock": 300},
    ]


def test_tolerates_punctuation_and_case_and_prefix():
    out = parse_sms_report("paracetamol:120, iron=300", _CATALOG)
    ids = [u["medicine_id"] for u in out["updates"]]
    assert ids == ["paracetamol", "ifa"]  # 'iron' alias + full-name both resolve


def test_unknown_token_is_reported_unmatched():
    out = parse_sms_report("PARA 120 XYZ 5", _CATALOG)
    assert [u["medicine_id"] for u in out["updates"]] == ["paracetamol"]
    assert out["unmatched"] == ["XYZ"]


def test_code_for_medicine_not_in_this_catalog_is_unmatched():
    out = parse_sms_report("AMOX 50", _CATALOG)  # amoxicillin not stocked here
    assert out["updates"] == []
    assert out["unmatched"] == ["AMOX"]


def test_last_value_wins_on_duplicate():
    out = parse_sms_report("ORS 40 ORS 55", _CATALOG)
    assert out["updates"] == [
        {"medicine_id": "ors", "medicine_name": "ORS Sachets", "current_stock": 55}]


def test_empty_text():
    assert parse_sms_report("", _CATALOG) == {"updates": [], "unmatched": []}


def test_report_endpoint_rejects_bad_secret():
    """The secret check runs before any Firestore access, so no DB is needed."""
    from app.main import app
    from fastapi.testclient import TestClient

    r = TestClient(app).post(
        "/api/sms/report",
        json={"centre_id": "phc_x", "text": "ORS 10", "secret": "wrong-secret"},
    )
    assert r.status_code == 403

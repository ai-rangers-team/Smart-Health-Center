from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_centre_stock_requires_auth():
    r = client.get("/api/centres/phc_mulshi/stock")
    assert r.status_code == 401


def test_centre_beds_requires_auth():
    assert client.get("/api/centres/phc_mulshi/beds").status_code == 401


def test_centre_attendance_requires_auth():
    assert client.get("/api/centres/phc_mulshi/attendance").status_code == 401


def test_centre_footfall_requires_auth():
    assert client.get("/api/centres/phc_mulshi/footfall").status_code == 401


def test_centre_tests_requires_auth():
    assert client.get("/api/centres/phc_mulshi/tests").status_code == 401


def test_operator_stock_write_requires_auth():
    r = client.patch("/api/centres/phc_mulshi/stock", json={"medicine_id": "paracetamol", "current_stock": 80})
    assert r.status_code == 401


def test_district_overview_requires_auth():
    assert client.get("/api/district/pune_rural/overview").status_code == 401


def test_district_alerts_requires_auth():
    assert client.get("/api/district/pune_rural/alerts").status_code == 401


def test_alert_resolve_requires_auth():
    assert client.post("/api/alerts/some_id/resolve").status_code == 401


def test_seed_disabled_by_default():
    r = client.post("/api/seed/district")
    assert r.status_code == 403

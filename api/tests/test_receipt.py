"""Two-sided redistribution receipt (anti-fraud layer 4).

Verifies the reconciliation logic: a full receipt marks 'received'; a short receipt
marks 'disputed' with the shortfall; only the recipient centre's operator may confirm.
Firestore + recompute + audit are faked so this runs offline.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import ai

client = TestClient(app)


class _Ref:
    def __init__(self, store, key):
        self._store, self._key = store, key

    def get(self):
        class _D:
            def __init__(s, data): s._d = data
            def to_dict(s): return s._d
        return _D(self._store.get(self._key))

    def update(self, patch):
        self._store.setdefault(self._key, {}).update(patch)


class _StockColl:
    def __init__(self, store): self._store = store
    def document(self, mid): return _Ref(self._store, ("stock", mid))


class _CentreRef:
    def __init__(self, store): self._store = store
    def collection(self, name):
        assert name == "stock"
        return _StockColl(self._store)


class _CentresColl:
    def __init__(self, store): self._store = store
    def document(self, cid): return _CentreRef(self._store)


class _RecColl:
    def __init__(self, store): self._store = store
    def document(self, rid): return _Ref(self._store, ("rec", rid))


class _DB:
    def __init__(self, store): self._store = store
    def collection(self, name):
        if name == "recommendations": return _RecColl(self._store)
        if name == "centres": return _CentresColl(self._store)
        raise AssertionError(name)


def _setup(monkeypatch, rec, stock_now=100):
    from app import firestore_client
    store = {("rec", "rec1"): dict(rec), ("stock", "ifa"): {"current_stock": stock_now}}
    monkeypatch.setattr(firestore_client, "_db", _DB(store))
    monkeypatch.setattr(ai, "recompute_centre", lambda cid: None)
    monkeypatch.setattr(ai.audit, "record", lambda *a, **k: None)

    def fake_verify(token):
        return {"uid": "u1", "email": "op@test.com", "role": "phc_operator",
                "district_id": "pune_rural", "centre_id": "phc_ambegaon"}
    monkeypatch.setattr(firestore_client, "verify_id_token", fake_verify)
    return store


_REC = {"to_centre_id": "phc_ambegaon", "medicine_id": "ifa", "quantity": 300,
        "status": "pending"}
_HDR = {"Authorization": "Bearer x"}


def test_full_receipt_marks_received_and_adds_stock(monkeypatch):
    store = _setup(monkeypatch, _REC, stock_now=100)
    r = client.post("/api/recommendations/rec1/confirm-receipt",
                    headers=_HDR, json={"received_qty": 300})
    assert r.status_code == 200
    assert r.json()["data"] == {"status": "received", "shortfall": 0}
    assert store[("stock", "ifa")]["current_stock"] == 400
    assert store[("rec", "rec1")]["status"] == "received"


def test_short_receipt_marks_disputed_with_shortfall(monkeypatch):
    store = _setup(monkeypatch, _REC, stock_now=100)
    r = client.post("/api/recommendations/rec1/confirm-receipt",
                    headers=_HDR, json={"received_qty": 210})
    assert r.json()["data"] == {"status": "disputed", "shortfall": 90}
    assert store[("stock", "ifa")]["current_stock"] == 310
    assert store[("rec", "rec1")]["received_qty"] == 210


def test_only_recipient_centre_operator_may_confirm(monkeypatch):
    _setup(monkeypatch, {**_REC, "to_centre_id": "phc_other"})
    r = client.post("/api/recommendations/rec1/confirm-receipt",
                    headers=_HDR, json={"received_qty": 300})
    assert r.status_code == 403  # operator's centre != recipient centre


def test_already_confirmed_is_idempotent(monkeypatch):
    _setup(monkeypatch, {**_REC, "status": "received"})
    r = client.post("/api/recommendations/rec1/confirm-receipt",
                    headers=_HDR, json={"received_qty": 300})
    assert r.json()["data"]["already"] is True


def test_missing_recommendation_404(monkeypatch):
    from app import firestore_client
    store = {}
    monkeypatch.setattr(firestore_client, "_db", _DB(store))
    monkeypatch.setattr(firestore_client, "verify_id_token",
                        lambda t: {"uid": "u1", "role": "phc_operator",
                                   "centre_id": "phc_ambegaon"})
    r = client.post("/api/recommendations/rec1/confirm-receipt",
                    headers=_HDR, json={"received_qty": 10})
    assert r.status_code == 404

"""Unit + endpoint tests for restock-invoice extraction.

Mirrors test_gemini.py: monkeypatch the extraction call so these run offline
and deterministically, and test_endpoints.py's auth-guard style for the route.
"""
import io

from fastapi.testclient import TestClient

from app.main import app
from app.routers import operator
from app.services.invoice_extract import ExtractedItem

client = TestClient(app)


class _FakeDoc:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return self._data


class _FakeStockCollection:
    def __init__(self, docs):
        self._docs = docs

    def stream(self):
        return iter(self._docs)


class _FakeCentreDoc:
    def __init__(self, stock_docs):
        self._stock_docs = stock_docs

    def collection(self, name):
        assert name == "stock"
        return _FakeStockCollection(self._stock_docs)


class _FakeCentresCollection:
    def __init__(self, centre_id, stock_docs):
        self._centre_id = centre_id
        self._stock_docs = stock_docs

    def document(self, doc_id):
        assert doc_id == self._centre_id
        return _FakeCentreDoc(self._stock_docs)


class _FakeDB:
    def __init__(self, centre_id, stock_docs):
        self._centres = _FakeCentresCollection(centre_id, stock_docs)

    def collection(self, name):
        assert name == "centres"
        return self._centres


_STOCK_DOCS = [
    _FakeDoc("paracetamol", {"medicine_name": "Paracetamol 500mg", "unit": "tablets", "current_stock": 120}),
    _FakeDoc("ors", {"medicine_name": "ORS Sachets", "unit": "sachets", "current_stock": 340}),
]


def _auth_headers(monkeypatch, centre_id="phc_haveli"):
    from app import firestore_client

    def fake_verify(token):
        return {"uid": "u1", "email": "op@test.com", "role": "phc_operator",
                "district_id": "pune_rural", "centre_id": centre_id}

    monkeypatch.setattr(firestore_client, "verify_id_token", fake_verify)
    return {"Authorization": "Bearer faketoken"}


def _patch_db(monkeypatch, centre_id="phc_haveli", stock_docs=_STOCK_DOCS):
    from app import firestore_client
    monkeypatch.setattr(firestore_client, "_db", _FakeDB(centre_id, stock_docs))


def test_extract_requires_auth():
    r = client.post("/api/centres/phc_haveli/stock/extract",
                     files={"file": ("invoice.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 401


def test_extract_forbidden_for_other_centre(monkeypatch):
    headers = _auth_headers(monkeypatch, centre_id="phc_haveli")
    r = client.post("/api/centres/phc_mulshi/stock/extract", headers=headers,
                     files={"file": ("invoice.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 403


def test_extract_rejects_unsupported_file_type(monkeypatch):
    headers = _auth_headers(monkeypatch)
    r = client.post("/api/centres/phc_haveli/stock/extract", headers=headers,
                     files={"file": ("invoice.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_extract_rejects_oversized_file(monkeypatch):
    headers = _auth_headers(monkeypatch)
    big = b"0" * (8 * 1024 * 1024 + 1)
    r = client.post("/api/centres/phc_haveli/stock/extract", headers=headers,
                     files={"file": ("invoice.pdf", big, "application/pdf")})
    assert r.status_code == 400


def test_extract_maps_matched_and_unmatched_items(monkeypatch):
    headers = _auth_headers(monkeypatch)
    _patch_db(monkeypatch)

    def fake_extract(file_bytes, mime_type, catalog):
        return [
            ExtractedItem(raw_name="Paracetamol 500mg Tabs", medicine_id="paracetamol",
                          quantity=100, confidence="high"),
            ExtractedItem(raw_name="Cotton Bandage Roll", medicine_id=None,
                          quantity=20, confidence="low"),
        ]

    monkeypatch.setattr(operator, "extract_restock_items", fake_extract)
    r = client.post("/api/centres/phc_haveli/stock/extract", headers=headers,
                     files={"file": ("invoice.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["items"] == [{
        "medicine_id": "paracetamol", "medicine_name": "Paracetamol 500mg",
        "unit": "tablets", "current_stock": 120, "quantity_received": 100,
        "proposed_stock": 220, "confidence": "high",
    }]
    assert data["unmatched"] == ["Cotton Bandage Roll"]


def test_extract_failure_returns_502(monkeypatch):
    headers = _auth_headers(monkeypatch)
    _patch_db(monkeypatch)

    def fake_extract(file_bytes, mime_type, catalog):
        raise RuntimeError("boom")

    monkeypatch.setattr(operator, "extract_restock_items", fake_extract)
    r = client.post("/api/centres/phc_haveli/stock/extract", headers=headers,
                     files={"file": ("invoice.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 502

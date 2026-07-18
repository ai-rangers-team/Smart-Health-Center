"""Endpoint tests for spoken-stock extraction.

Reuses the invoice test's Firestore/auth fakes; monkeypatches the Gemini call so
these run offline and deterministically.
"""
from app.main import app
from app.routers import operator
from app.services.voice_extract import SpokenItem, SpokenStock
from fastapi.testclient import TestClient

from tests.test_invoice_extract import _auth_headers, _patch_db

client = TestClient(app)

_AUDIO = ("report.webm", b"RIFFfake-audio", "audio/webm")


def test_voice_requires_auth():
    r = client.post("/api/centres/phc_haveli/stock/voice",
                     files={"file": _AUDIO})
    assert r.status_code == 401


def test_voice_forbidden_for_other_centre(monkeypatch):
    headers = _auth_headers(monkeypatch, centre_id="phc_haveli")
    r = client.post("/api/centres/phc_mulshi/stock/voice", headers=headers,
                     files={"file": _AUDIO})
    assert r.status_code == 403


def test_voice_rejects_unsupported_audio_type(monkeypatch):
    headers = _auth_headers(monkeypatch)
    r = client.post("/api/centres/phc_haveli/stock/voice", headers=headers,
                     files={"file": ("report.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_voice_accepts_mime_with_codecs_suffix(monkeypatch):
    headers = _auth_headers(monkeypatch)
    _patch_db(monkeypatch)

    def fake_extract(audio_bytes, mime_type, catalog, lang):
        assert mime_type == "audio/webm"  # codecs= suffix stripped before the check
        return SpokenStock(transcript="paracetamol 90", items=[
            SpokenItem(raw_name="paracetamol", medicine_id="paracetamol",
                       quantity=90, confidence="high")])

    monkeypatch.setattr(operator, "extract_stock_from_speech", fake_extract)
    r = client.post("/api/centres/phc_haveli/stock/voice", headers=headers,
                     files={"file": ("report.webm", b"audio", "audio/webm;codecs=opus")})
    assert r.status_code == 200


def test_voice_maps_spoken_counts_as_absolute_stock(monkeypatch):
    headers = _auth_headers(monkeypatch)
    _patch_db(monkeypatch)

    def fake_extract(audio_bytes, mime_type, catalog, lang):
        return SpokenStock(transcript="paracetamol ninety, bandages twenty", items=[
            SpokenItem(raw_name="paracetamol", medicine_id="paracetamol",
                       quantity=90, confidence="high"),
            SpokenItem(raw_name="bandages", medicine_id=None, quantity=20, confidence="low"),
        ])

    monkeypatch.setattr(operator, "extract_stock_from_speech", fake_extract)
    r = client.post("/api/centres/phc_haveli/stock/voice?lang=en", headers=headers,
                     files={"file": _AUDIO})
    assert r.status_code == 200
    data = r.json()["data"]
    # spoken count is the REMAINING stock -> proposed_stock, not added to current
    assert data["items"] == [{
        "medicine_id": "paracetamol", "medicine_name": "Paracetamol 500mg",
        "unit": "tablets", "proposed_stock": 90, "confidence": "high",
    }]
    assert data["unmatched"] == ["bandages"]
    assert data["transcript"] == "paracetamol ninety, bandages twenty"


def test_voice_failure_returns_502(monkeypatch):
    headers = _auth_headers(monkeypatch)
    _patch_db(monkeypatch)

    def fake_extract(audio_bytes, mime_type, catalog, lang):
        raise RuntimeError("boom")

    monkeypatch.setattr(operator, "extract_stock_from_speech", fake_extract)
    r = client.post("/api/centres/phc_haveli/stock/voice", headers=headers, files={"file": _AUDIO})
    assert r.status_code == 502

"""Unit tests for the Gemini enrichment layer.

We monkeypatch `generate` so these run offline and deterministically — they verify
each enrichment function builds a prompt containing the right structured data and
returns the model's text. The live model call is covered by scripts/verify_gemini.py.
"""
from app.services import gemini


def _capture(monkeypatch):
    calls = {}

    def fake_generate(prompt, language="mr"):
        calls["prompt"] = prompt
        calls["language"] = language
        return "CANNED"

    monkeypatch.setattr(gemini, "generate", fake_generate)
    return calls


def test_stockout_narrative_includes_medicine_and_days(monkeypatch):
    calls = _capture(monkeypatch)
    out = gemini.stockout_narrative(
        [{"name": "Paracetamol 500mg", "days_remaining": 3}], language="en")
    assert out == "CANNED"
    assert "Paracetamol 500mg" in calls["prompt"] and "3" in calls["prompt"]
    assert calls["language"] == "en"


def test_stockout_narrative_empty_returns_blank_without_calling(monkeypatch):
    called = {"hit": False}
    monkeypatch.setattr(gemini, "generate", lambda *a, **k: called.__setitem__("hit", True) or "X")
    assert gemini.stockout_narrative([], language="en") == ""
    assert called["hit"] is False


def test_redistribution_instruction_includes_transfer_details(monkeypatch):
    calls = _capture(monkeypatch)
    out = gemini.redistribution_instruction(
        {"from_centre": "CHC", "to_centre": "PHC Mulshi", "medicine": "Paracetamol",
         "quantity": 200, "urgency": "critical"}, language="mr")
    assert out == "CANNED"
    for token in ("CHC", "PHC Mulshi", "Paracetamol", "200"):
        assert token in calls["prompt"]


def test_underperformance_explanation_includes_score_and_flags(monkeypatch):
    calls = _capture(monkeypatch)
    out = gemini.underperformance_explanation(
        38, ["Doctor attendance 52% (target 80%)"], language="en")
    assert out == "CANNED"
    assert "38" in calls["prompt"] and "attendance" in calls["prompt"].lower()


def test_district_briefing_includes_counts(monkeypatch):
    calls = _capture(monkeypatch)
    out = gemini.district_briefing(4, 2, ["Paracetamol stock-out at Mulshi"], language="hi")
    assert out == "CANNED"
    assert "2" in calls["prompt"] and "Mulshi" in calls["prompt"]

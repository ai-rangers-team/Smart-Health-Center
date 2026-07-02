"""Gemini communication layer (spec §6).

Gemini turns already-computed structured data (forecasts, scores, redistribution
matches) into human-readable text. It is NEVER on the live operator-write path —
these functions enrich, they don't gate. `generate` swallows errors and returns ""
so a Gemini hiccup can never break a request.
"""
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)

_LANG = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def generate(prompt: str, language: str = "mr") -> str:
    full = f"{prompt}\n\nRespond in {_LANG.get(language, 'English')}. Be concise."
    try:
        return _model.generate_content(full).text.strip()
    except Exception:
        return ""


def stockout_narrative(at_risk: list[dict], language: str = "mr") -> str:
    """at_risk: [{name, days_remaining}, ...] for medicines at high/critical severity."""
    if not at_risk:
        return ""
    items = "; ".join(f'{m["name"]} ({m["days_remaining"]} days)' for m in at_risk)
    return generate(
        "You are a district health supply-chain officer. Medicines at risk of stock-out: "
        f"{items}. Write a 2-sentence alert for the facility in-charge, naming the "
        "most urgent medicine first.",
        language,
    )


def redistribution_instruction(rec: dict, language: str = "mr") -> str:
    """rec: {from_centre, to_centre, medicine, quantity, urgency}."""
    return generate(
        "Write a one-sentence stock-transfer instruction for a district health officer. "
        f'Transfer {rec["quantity"]} units of {rec["medicine"]} from {rec["from_centre"]} '
        f'to {rec["to_centre"]} (urgency: {rec["urgency"]}).',
        language,
    )


def underperformance_explanation(score: int, flags: list[str], language: str = "mr") -> str:
    """flags: human-readable deduction reasons from scoring.compute_performance_score."""
    reasons = "; ".join(flags) if flags else "no major issues"
    return generate(
        f"A health centre scored {score}/100 on operational performance. "
        f"Issues: {reasons}. Explain in 2 sentences for a district officer and "
        "recommend one concrete action.",
        language,
    )


def district_briefing(total_alerts: int, critical: int, messages: list[str],
                      language: str = "mr") -> str:
    """messages: short strings of the top active alerts across the district."""
    joined = "; ".join(messages[:6]) if messages else "no active alerts"
    return generate(
        f"District status: {total_alerts} active alerts, {critical} critical. "
        f"Key items: {joined}. Write a 3-sentence executive briefing for the "
        "District Health Officer, most urgent issue first.",
        language,
    )

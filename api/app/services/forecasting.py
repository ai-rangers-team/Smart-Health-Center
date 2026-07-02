"""EWMA-based forecasting for medicine stock-out and patient footfall (spec §6.1, §6.4).

Pure functions — no external dependencies. The real decision layer; Gemini only
narrates the output elsewhere.
"""
from datetime import datetime, timedelta, timezone


def ewma(series: list[float], alpha: float = 0.3) -> float:
    """Recency-weighted average; the newest observation gets full weight and older
    ones decay by (1 - alpha) per step.

    This is the normalized EWMA form: it avoids the cold-start bias of the naive
    seeded recursion (which, on a short series with alpha < 0.5, over-weights the
    OLDEST value). Here recent consumption genuinely dominates the estimate, which
    is what the spec (§6.1) intends.
    """
    if not series:
        return 0.0
    n = len(series)
    num = den = 0.0
    for i, x in enumerate(series):
        w = (1 - alpha) ** (n - 1 - i)  # newest (i = n-1) → weight 1.0
        num += w * x
        den += w
    return num / den


def forecast_stockout(history: list[float], current_stock: float) -> dict:
    """Predict days until stock-out from a consumption history + current stock."""
    rate = ewma(history)
    days = current_stock / rate if rate > 0 else 999.0
    if days <= 3:
        sev = "critical"
    elif days <= 7:
        sev = "high"
    elif days <= 14:
        sev = "medium"
    else:
        sev = "low"
    return {
        "days_remaining": round(days, 1),
        "daily_consumption_forecast": round(rate, 2),
        "predicted_stockout_date": (
            datetime.now(timezone.utc) + timedelta(days=days)
        ).isoformat(),
        "severity": sev,
        "trend": "increasing" if history and history[-1] > rate else "stable",
    }


def forecast_footfall(history: list[int]) -> dict:
    """Project patient demand from a footfall history (spec §6.4)."""
    rate = ewma([float(x) for x in history])
    trend = "stable"
    if len(history) >= 2:
        if history[-1] < rate * 0.9:
            trend = "falling"
        elif history[-1] > rate * 1.1:
            trend = "rising"
    return {"projection": round(rate), "trend": trend}

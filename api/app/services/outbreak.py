"""Consumption/footfall anomaly detection -> possible disease-cluster early warning.

An extension beyond the literal brief: the same daily reports that drive stock
forecasts also reveal demand surges. A sudden jump in a *marker* medicine's
consumption (ORS -> diarrhoeal illness; antipyretics -> febrile illness) or in
patient footfall, happening across MULTIPLE centres at once, is an early signal
of an outbreak the district officer should investigate before it spreads.

Pure function — no Gemini, no external deps. A single centre surging is treated
as ordinary local variation; only a CLUSTER (>= MIN_CLUSTER centres on the same
signal) is surfaced, which is what makes it an outbreak signal rather than noise.
"""

# marker medicine id -> the syndrome a sustained consumption surge may indicate
MARKERS = {
    "ors": "diarrhoeal illness",
    "paracetamol": "febrile illness",
    "amoxicillin": "respiratory/bacterial infection",
}

SPIKE_RATIO = 1.75   # latest day >= 1.75x the recent baseline counts as a surge
MIN_BASELINE = 5.0   # ignore tiny-count noise (a jump from 1 to 3 is not a signal)
MIN_HISTORY = 4      # need a few days of baseline before calling anything a spike
MIN_CLUSTER = 2      # >= this many centres surging on one signal => cluster warning


def is_surge(series: list[float], ratio: float = SPIKE_RATIO) -> tuple[bool, float]:
    """series oldest->newest. Compare the latest value to the mean of the prior window."""
    if len(series) < MIN_HISTORY:
        return False, 0.0
    prior = series[:-1]
    baseline = sum(prior) / len(prior)
    if baseline < MIN_BASELINE:
        return False, 0.0
    r = series[-1] / baseline
    return r >= ratio, r


def detect_outbreaks(centres: list[dict]) -> list[dict]:
    """centres: [{name, footfall: [oldest->newest], consumption: {med_id: [oldest->newest]}}]."""
    signals: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for c in centres:
        surge, r = is_surge(c.get("footfall", []))
        if surge:
            signals.setdefault(("footfall", "patient footfall"), []).append((c["name"], r))
        for med, series in (c.get("consumption") or {}).items():
            if med not in MARKERS:
                continue
            surge, r = is_surge(series)
            if surge:
                signals.setdefault((med, MARKERS[med]), []).append((c["name"], r))

    out = []
    for (sig, label), hits in signals.items():
        if len(hits) >= MIN_CLUSTER:
            out.append({
                "signal": sig,
                "indication": label,
                "centres": [h[0] for h in hits],
                "centre_count": len(hits),
                "peak_ratio": round(max(h[1] for h in hits), 1),
                "severity": "high" if len(hits) >= 3 else "medium",
            })
    out.sort(key=lambda o: (-o["centre_count"], -o["peak_ratio"]))
    return out

"""Weighted rule-based underperformance scoring (spec §6.3).

Weights sum to 100: attendance 25, footfall 20, stock-outs 20, beds 15, tests 20.
Gemini narrates the returned flags elsewhere; this function is the decision layer.
"""


def compute_performance_score(c: dict) -> dict:
    score = 100.0
    flags: list[str] = []

    if c["avg_attendance_rate"] < 0.6:
        score -= min((0.6 - c["avg_attendance_rate"]) * 100, 25)
        flags.append(f"Doctor attendance {c['avg_attendance_rate'] * 100:.0f}% (target 80%)")

    if c["district_avg_footfall"] and c["avg_footfall"] / c["district_avg_footfall"] < 0.6:
        score -= 20
        flags.append(
            f"Footfall {c['avg_footfall'] / c['district_avg_footfall'] * 100:.0f}% of district average"
        )

    if c["critical_stockouts"]:
        score -= min(c["critical_stockouts"] * 8, 20)
        flags.append(f"{c['critical_stockouts']} medicine(s) in critical stock-out")

    if c["bed_occupancy_rate"] < 0.3:
        score -= 15
        flags.append(f"Bed occupancy {c['bed_occupancy_rate'] * 100:.0f}% — underutilised")

    if c["essential_tests_unavailable"]:
        score -= min(c["essential_tests_unavailable"] * 10, 20)
        flags.append(f"{c['essential_tests_unavailable']} essential test(s) unavailable")

    score = max(0, round(score))
    status = "critical" if score < 40 else "under_resourced" if score < 65 else "operational"
    return {"score": score, "flags": flags, "status": status}

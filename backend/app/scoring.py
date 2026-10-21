"""Transparent, configurable risk-prioritisation score (0-100).

This is a PRIORITISATION AID for triage. It is not a prediction that an accident
will or will not happen.

    score = 100 * ( w_severity * severity_n
                  + w_similar  * similar_n
                  + w_age      * age_n )

    severity_n = (severity - 1) / 4                    severity is a 1-5 estimate
    similar_n  = min(other_open_related, CAP) / CAP    corroborating open reports
    age_n      = min(days_unresolved, CAP_DAYS) / CAP_DAYS
"""
from . import config


def _level(score: float, levels=None) -> str:
    for name, minimum in levels or config.PRIORITY_LEVELS:
        if score >= minimum:
            return name
    return "low"


def compute_score(
    severity: int,
    similar_open: int,
    age_days: float,
    weights: dict | None = None,
    similar_cap: int | None = None,
    age_cap_days: float | None = None,
) -> dict:
    if not 1 <= int(severity) <= 5:
        raise ValueError("severity must be between 1 and 5")
    if similar_open < 0 or age_days < 0:
        raise ValueError("similar_open and age_days must be non-negative")
    weights = dict(weights or config.SCORE_WEIGHTS)
    total_w = sum(weights.values())
    if total_w <= 0:
        raise ValueError("weights must sum to a positive number")
    weights = {k: v / total_w for k, v in weights.items()}  # normalise to 1.0
    similar_cap = similar_cap or config.SIMILAR_CAP
    age_cap_days = age_cap_days or config.AGE_CAP_DAYS

    sev_n = (severity - 1) / 4
    sim_n = min(similar_open, similar_cap) / similar_cap
    age_n = min(age_days, age_cap_days) / age_cap_days

    parts = [
        {
            "key": "severity",
            "label": "Estimated severity",
            "raw": severity,
            "normalized": round(sev_n, 3),
            "weight": round(weights["severity"], 3),
            "points": round(100 * weights["severity"] * sev_n, 1),
            "explanation": f"Severity {severity}/5 (admin-adjustable estimate)",
        },
        {
            "key": "similar_reports",
            "label": "Similar open reports",
            "raw": similar_open,
            "normalized": round(sim_n, 3),
            "weight": round(weights["similar_reports"], 3),
            "points": round(100 * weights["similar_reports"] * sim_n, 1),
            "explanation": f"{similar_open} other open report(s) at the same place and category (full marks at {similar_cap}+)",
        },
        {
            "key": "unresolved_age",
            "label": "Time unresolved",
            "raw": round(age_days, 1),
            "normalized": round(age_n, 3),
            "weight": round(weights["unresolved_age"], 3),
            "points": round(100 * weights["unresolved_age"] * age_n, 1),
            "explanation": f"{age_days:.1f} day(s) since first report (full marks at {age_cap_days:g}+ days)",
        },
    ]
    score = round(sum(p["points"] for p in parts), 1)
    score = max(0.0, min(100.0, score))
    return {
        "score": score,
        "level": _level(score),
        "components": parts,
        "note": "Illustrative weights. A prioritisation aid, not a prediction of accidents.",
    }

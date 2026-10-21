"""Deterministic, explainable grouping of likely-duplicate reports.

Rule (documented, not machine learning):
  Two reports are LINKED when they share the same building/block AND the same
  confirmed hazard category.
Supporting evidence shown to the admin (never used to merge anything):
  * word overlap (Jaccard) between the two descriptions
  * whether the optional location details share words
Reports are never merged or deleted automatically; they are only linked.
"""
import re

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "at", "in", "on", "of", "to", "and",
    "or", "near", "by", "with", "it", "this", "that", "there", "has", "have", "very",
    "from", "for", "be", "been", "its", "some", "again", "still", "please", "seems",
}


def tokenize(text: str | None) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for w in words:
        if w in _STOP or len(w) < 3:
            continue
        for suffix in ("ing", "es", "s"):  # crude stemming, good enough to be explainable
            if w.endswith(suffix) and len(w) - len(suffix) >= 3:
                w = w[: -len(suffix)]
                break
        out.add(w)
    return out


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def group_key(report: dict) -> tuple[str, str]:
    return (report["building"], report["category"])


def related_reports(target: dict, others: list[dict]) -> list[dict]:
    """Return reports linked to `target`, with the evidence for each link."""
    key = group_key(target)
    t_desc, t_loc = tokenize(target.get("description")), tokenize(target.get("location_details"))
    out = []
    for o in others:
        if o["id"] == target["id"] or group_key(o) != key:
            continue
        out.append(
            {
                "id": o["id"],
                "status": o["status"],
                "created_at": o["created_at"],
                "description": o["description"],
                "description_similarity": round(jaccard(t_desc, tokenize(o["description"])), 2),
                "location_details_overlap": bool(t_loc & tokenize(o.get("location_details"))),
            }
        )
    out.sort(key=lambda r: r["created_at"])
    return out


def build_groups(reports: list[dict]) -> list[dict]:
    """All groups with 2+ linked reports."""
    buckets: dict[tuple, list[dict]] = {}
    for r in reports:
        buckets.setdefault(group_key(r), []).append(r)
    groups = []
    for (building, category), items in buckets.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda r: r["created_at"])
        groups.append(
            {
                "building": building,
                "category": category,
                "report_ids": [r["id"] for r in items],
                "size": len(items),
                "open_count": sum(1 for r in items if r["status"] != "resolved"),
                "rule": "same building/block + same confirmed category",
            }
        )
    groups.sort(key=lambda g: -g["open_count"])
    return groups

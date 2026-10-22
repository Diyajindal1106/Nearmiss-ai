"""Data access + business rules. Framework-free so it is directly unit-testable."""
import json
from datetime import datetime, timezone

from . import config, grouping, scoring
from .db import now_iso, parse_iso

PRIORITY_RANK = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


class NotFound(Exception):
    pass


class RuleViolation(ValueError):
    """A business-rule failure (mapped to HTTP 422/400)."""


# ------------------------------------------------------------------- helpers
def _row(r) -> dict:
    d = dict(r)
    d["is_demo"] = bool(d["is_demo"])
    d["ai_result"] = json.loads(d["ai_result"]) if d.get("ai_result") else None
    d["image_url"] = f"/api/images/{d['image_filename']}" if d.get("image_filename") else None
    return d


def _all(conn) -> list[dict]:
    return [_row(r) for r in conn.execute("SELECT * FROM reports ORDER BY created_at, id")]


def _age_days(r: dict, now: datetime) -> float:
    end = parse_iso(r["resolved_at"]) if r.get("resolved_at") else now
    return max(0.0, (end - parse_iso(r["created_at"])).total_seconds() / 86400)


def enrich(r: dict, everyone: list[dict], now: datetime | None = None) -> dict:
    """Attach related-report evidence, risk score and effective priority."""
    now = now or datetime.now(timezone.utc)
    related = grouping.related_reports(r, everyone)
    similar_open = sum(1 for x in related if x["status"] != "resolved")
    score = scoring.compute_score(r["severity"], similar_open, _age_days(r, now))
    out = dict(r)
    out["related_count"] = len(related)
    out["related_open_count"] = similar_open
    out["group_size"] = len(related) + 1
    out["score"] = score["score"]
    out["computed_priority"] = score["level"]
    out["priority"] = r["priority_override"] or score["level"]
    out["priority_source"] = "admin_override" if r["priority_override"] else "computed"
    out["score_breakdown"] = score
    out["age_days"] = round(_age_days(r, now), 1)
    return out


def _brief(e: dict) -> dict:
    keep = [
        "id", "description", "building", "location_details", "category", "status", "severity",
        "priority", "priority_source", "computed_priority", "score", "assignee", "is_demo",
        "created_at", "updated_at", "image_url", "ai_status", "related_count",
        "related_open_count", "group_size", "age_days",
    ]
    return {k: e[k] for k in keep}


def _log(conn, report_id, field, old, new, note=None, at=None):
    conn.execute(
        "INSERT INTO status_history(report_id, field, old_value, new_value, note, changed_at)"
        " VALUES (?,?,?,?,?,?)",
        (report_id, field, None if old is None else str(old), None if new is None else str(new), note, at or now_iso()),
    )


# -------------------------------------------------------------------- create
def create_report(conn, data: dict, is_demo: bool = False, created_at: str | None = None) -> dict:
    analysis = None
    image_filename = None
    if data.get("upload_id"):
        row = conn.execute("SELECT * FROM analyses WHERE id=?", (data["upload_id"],)).fetchone()
        if not row:
            raise RuleViolation("Unknown upload_id. Please re-upload the image.")
        analysis = json.loads(row["result"])
        image_filename = row["image_filename"]

    category = data["category"]
    ai_cat = analysis.get("suggested_category") if analysis else None
    if ai_cat:
        source = "ai_confirmed" if ai_cat == category else "ai_overridden"
    else:
        source = "manual"
    ts = created_at or now_iso()
    cur = conn.execute(
        """INSERT INTO reports(description, building, location_details, category, category_source,
               severity, status, image_filename, ai_status, ai_category, ai_result, is_demo,
               created_at, updated_at)
           VALUES (?,?,?,?,?,?, 'open', ?,?,?,?,?, ?,?)""",
        (
            data["description"].strip(), data["building"], (data.get("location_details") or "").strip() or None,
            category, source, config.CATEGORIES[category]["default_severity"], image_filename,
            analysis["status"] if analysis else "not_run", ai_cat,
            json.dumps(analysis) if analysis else None, int(is_demo), ts, ts,
        ),
    )
    rid = cur.lastrowid
    _log(conn, rid, "created", None, "open", "Report submitted" + (" (demo seed)" if is_demo else ""), at=ts)
    return get_report(conn, rid)


# ---------------------------------------------------------------------- read
def get_report(conn, report_id: int) -> dict:
    everyone = _all(conn)
    target = next((r for r in everyone if r["id"] == report_id), None)
    if not target:
        raise NotFound(f"Report {report_id} not found")
    e = enrich(target, everyone)
    e["related"] = grouping.related_reports(target, everyone)
    e["history"] = [
        dict(h) for h in conn.execute(
            "SELECT field, old_value, new_value, note, changed_by, changed_at"
            " FROM status_history WHERE report_id=? ORDER BY id", (report_id,))
    ]
    e["ai_disclaimer"] = "AI suggestion — human verification required."
    return e


def list_reports(conn, search=None, status=None, category=None, priority=None,
                 building=None, sort="priority") -> list[dict]:
    everyone = _all(conn)
    now = datetime.now(timezone.utc)
    items = [enrich(r, everyone, now) for r in everyone]
    if status:
        items = [i for i in items if i["status"] == status]
    if category:
        items = [i for i in items if i["category"] == category]
    if building:
        items = [i for i in items if i["building"] == building]
    if priority:
        items = [i for i in items if i["priority"] == priority]
    if search:
        q = search.strip().lower()
        items = [
            i for i in items
            if q in " ".join(str(i.get(k) or "") for k in
                             ("description", "location_details", "assignee", "id")).lower()
            or q in config.BUILDINGS.get(i["building"], {}).get("label", "").lower()
            or q in config.CATEGORIES.get(i["category"], {}).get("label", "").lower()
        ]
    if sort == "newest":
        items.sort(key=lambda i: i["created_at"], reverse=True)
    elif sort == "oldest":
        items.sort(key=lambda i: i["created_at"])
    elif sort == "severity":
        items.sort(key=lambda i: (-i["severity"], -i["score"]))
    else:  # priority: unresolved first, then effective level, then score
        items.sort(key=lambda i: (i["status"] == "resolved", -PRIORITY_RANK[i["priority"]], -i["score"]))
    return [_brief(i) for i in items]


# -------------------------------------------------------------------- update
def update_report(conn, report_id: int, changes: dict) -> dict:
    row = conn.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        raise NotFound(f"Report {report_id} not found")
    cur = _row(row)
    sets: dict = {}

    def change(field, new, *, column=None):
        old = cur[column or field]
        if (old or None) != (new or None):
            sets[column or field] = new
            _log(conn, report_id, field, old, new)

    if "category" in changes and changes["category"] is not None:
        if changes["category"] not in config.CATEGORIES:
            raise RuleViolation("Unknown category.")
        if changes["category"] != cur["category"]:
            change("category", changes["category"])
            sets["category_source"] = "admin_changed"
    if "severity" in changes and changes["severity"] is not None:
        if not 1 <= changes["severity"] <= 5:
            raise RuleViolation("Severity must be between 1 and 5.")
        change("severity", changes["severity"])
    if "priority_override" in changes:
        po = changes["priority_override"]
        po = None if po in (None, "auto", "") else po
        if po is not None and po not in config.PRIORITY_OVERRIDES:
            raise RuleViolation("Unknown priority level.")
        change("priority", po, column="priority_override")
    if "assignee" in changes:
        change("assignee", (changes["assignee"] or "").strip() or None)
    notes = cur["resolution_notes"]
    if "resolution_notes" in changes:
        notes = (changes["resolution_notes"] or "").strip() or None
        change("resolution_notes", notes)
    if "status" in changes and changes["status"] is not None:
        new_status = changes["status"]
        if new_status not in config.STATUSES:
            raise RuleViolation("Unknown status.")
        if new_status == "resolved" and not notes:
            raise RuleViolation("Add resolution notes before marking a report as Resolved.")
        if new_status != cur["status"]:
            change("status", new_status)
            sets["resolved_at"] = now_iso() if new_status == "resolved" else None
    if sets:
        sets["updated_at"] = now_iso()
        cols = ", ".join(f"{k}=?" for k in sets)
        conn.execute(f"UPDATE reports SET {cols} WHERE id=?", (*sets.values(), report_id))
    return get_report(conn, report_id)


# ----------------------------------------------------------------- dashboard
def stats(conn) -> dict:
    everyone = _all(conn)
    now = datetime.now(timezone.utc)
    items = [enrich(r, everyone, now) for r in everyone]
    unresolved = [i for i in items if i["status"] != "resolved"]
    count = lambda xs, key, keys: {k: sum(1 for x in xs if x[key] == k) for k in keys}  # noqa: E731
    by_date = {}
    for i in items:
        day = i["created_at"][:10]
        by_date[day] = by_date.get(day, 0) + 1
    recent_trend = [{"date": d, "count": by_date[d]} for d in sorted(by_date.keys())[-7:]]
    return {
        "total": len(items),
        "open": sum(1 for i in items if i["status"] == "open"),
        "in_progress": sum(1 for i in items if i["status"] == "in_progress"),
        "unresolved": len(unresolved),
        "resolved": sum(1 for i in items if i["status"] == "resolved"),
        "urgent_high": sum(1 for i in unresolved if i["priority"] in ("urgent", "high")),
        "by_priority": count(unresolved, "priority", list(PRIORITY_RANK)[::-1]),
        "by_category": count(items, "category", list(config.CATEGORIES)),
        "by_status": count(items, "status", config.STATUSES),
        "by_building": {
            b: {
                "total": sum(1 for i in items if i["building"] == b),
                "unresolved": sum(1 for i in unresolved if i["building"] == b),
                "top_priority": max(
                    (i["priority"] for i in unresolved if i["building"] == b),
                    key=lambda p: PRIORITY_RANK[p], default=None),
            }
            for b in config.BUILDINGS
        },
        "demo_count": sum(1 for i in items if i["is_demo"]),
        "groups": grouping.build_groups(everyone),
        "recent_trend": recent_trend,
        "generated_at": now_iso(),
    }

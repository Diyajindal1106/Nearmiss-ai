import json

import pytest

from app import db, repository as repo, seed


def new(conn, **kw):
    d = dict(description="Cracked step at the entrance stairs", building="block_b",
             category="broken_stairs", location_details="Entrance")
    d.update(kw)
    return repo.create_report(conn, d)


def test_create_persists_across_connections(tmp_env):
    with db.connect() as c:
        rid = new(c)["id"]
    with db.connect() as c:
        r = repo.get_report(c, rid)
    assert r["status"] == "open" and r["severity"] == 4 and r["category_source"] == "manual"
    assert r["history"][0]["field"] == "created"


def test_ai_provenance_is_copied_server_side(tmp_env):
    analysis = {"status": "ok", "suggested_category": "pothole", "scores": []}
    with db.connect() as c:
        c.execute("INSERT INTO analyses VALUES (?,?,?,?)", ("a" * 32, "x.png", json.dumps(analysis), db.now_iso()))
        confirmed = new(c, category="pothole", building="main_gate", upload_id="a" * 32)
        overridden = new(c, category="wet_floor", upload_id="a" * 32)
    assert confirmed["category_source"] == "ai_confirmed" and confirmed["ai_category"] == "pothole"
    assert overridden["category_source"] == "ai_overridden"


def test_unknown_upload_rejected(tmp_env):
    with db.connect() as c, pytest.raises(repo.RuleViolation):
        new(c, upload_id="b" * 32)


def test_uncertain_analysis_is_stored_as_manual(tmp_env):
    analysis = {"status": "uncertain", "suggested_category": None}
    with db.connect() as c:
        c.execute("INSERT INTO analyses VALUES (?,?,?,?)", ("c" * 32, "y.png", json.dumps(analysis), db.now_iso()))
        r = new(c, upload_id="c" * 32)
    assert r["ai_status"] == "uncertain" and r["category_source"] == "manual"


def test_duplicate_grouping_raises_score_and_links(tmp_env):
    with db.connect() as c:
        a = new(c)
        base = a["score"]
        b = new(c, description="Broken step by the entrance, tripped over it")
        new(c, building="library")  # unrelated: must not link
        a2 = repo.get_report(c, a["id"])
    assert a2["related_count"] == 1 and a2["related"][0]["id"] == b["id"]
    assert a2["score"] > base


def test_update_status_category_priority_assignment_with_history(tmp_env):
    with db.connect() as c:
        rid = new(c)["id"]
        r = repo.update_report(c, rid, {"status": "in_progress", "assignee": " Civil team ",
                                        "priority_override": "urgent", "category": "pothole", "severity": 2})
    assert (r["status"], r["assignee"], r["priority"], r["priority_source"]) == ("in_progress", "Civil team", "urgent", "admin_override")
    assert r["category"] == "pothole" and r["category_source"] == "admin_changed" and r["severity"] == 2
    assert {h["field"] for h in r["history"]} >= {"status", "assignee", "priority", "category", "severity"}
    with db.connect() as c:  # persisted
        assert repo.get_report(c, rid)["assignee"] == "Civil team"
        r = repo.update_report(c, rid, {"priority_override": "auto"})
    assert r["priority_source"] == "computed"


def test_resolve_requires_notes_then_freezes_age(tmp_env):
    with db.connect() as c:
        rid = new(c)["id"]
        with pytest.raises(repo.RuleViolation):
            repo.update_report(c, rid, {"status": "resolved"})
        r = repo.update_report(c, rid, {"status": "resolved", "resolution_notes": "Step replaced"})
        assert r["resolved_at"] and r["resolution_notes"] == "Step replaced"
        r = repo.update_report(c, rid, {"status": "open"})
        assert r["resolved_at"] is None


def test_no_change_writes_no_history(tmp_env):
    with db.connect() as c:
        rid = new(c)["id"]
        n = len(repo.get_report(c, rid)["history"])
        assert len(repo.update_report(c, rid, {"status": "open"})["history"]) == n


def test_stats_reflect_new_reports_and_are_derived(tmp_env):
    with db.connect() as c:
        s0 = repo.stats(c)
        assert s0["total"] == 0 and s0["urgent_high"] == 0
        new(c)
        rid = new(c, building="library", category="wet_floor")["id"]
        repo.update_report(c, rid, {"status": "resolved", "resolution_notes": "mopped"})
        s = repo.stats(c)
    assert (s["total"], s["unresolved"], s["resolved"]) == (2, 1, 1)
    assert s["by_category"]["broken_stairs"] == 1 and s["by_building"]["block_b"]["unresolved"] == 1


def test_list_filter_search_sort(tmp_env):
    with db.connect() as c:
        new(c)
        new(c, building="library", category="wet_floor", description="Puddle in the lobby near entrance")
        assert len(repo.list_reports(c, search="puddle")) == 1
        assert len(repo.list_reports(c, category="wet_floor")) == 1
        assert len(repo.list_reports(c, search="library")) == 1
        assert repo.list_reports(c, sort="severity")[0]["category"] == "broken_stairs"


def test_seed_is_idempotent_labelled_and_groups(tmp_env):
    assert seed.seed() == len(seed.DEMO)
    assert seed.seed() == 0
    with db.connect() as c:
        s = repo.stats(c)
        items = repo.list_reports(c)
    assert s["demo_count"] == s["total"] == len(seed.DEMO)
    assert all(i["is_demo"] for i in items)
    assert any(g["building"] == "block_b" and g["size"] == 3 for g in s["groups"])


def test_missing_report(tmp_env):
    with db.connect() as c, pytest.raises(repo.NotFound):
        repo.get_report(c, 999)

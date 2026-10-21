"""Create the database and load clearly-labelled ILLUSTRATIVE demo reports.

    python -m app.seed          # add demo data if the DB has no reports
    python -m app.seed --reset  # wipe the DB and re-seed

Every seeded row has is_demo=1 and is shown as 'Sample data' in the UI. These are NOT
real incidents. `days_ago` is applied to the creation time so the age factor in the
score has something to show.
"""
import argparse
from datetime import datetime, timedelta, timezone

from . import db, repository, config

DEMO = [
    # (days_ago, building, category, description, location_details, status, assignee, notes)
    (9, "block_b", "broken_stairs", "Third step at the Block B entrance is cracked and loose; people trip on it.", "Main entrance stairs", "open", None, None),
    (6, "block_b", "broken_stairs", "Loose broken step by the Block B front stairs, nearly slipped this morning.", "Entrance stairs, left side", "open", None, None),
    (2, "block_b", "broken_stairs", "Damaged stair edge at Block B entrance, concrete is crumbling.", "Entrance stairs", "open", None, None),
    (3, "science_lab", "exposed_wire", "Exposed wires hanging from the socket panel near the lab bench 4.", "Lab 2, bench 4 wall", "in_progress", "Electrical maintenance team", None),
    (11, "main_gate", "pothole", "Deep pothole just inside the main gate, vehicles swerve around it.", "Inside the gate, left lane", "open", None, None),
    (8, "main_gate", "pothole", "Large pothole filling with water near the main gate entrance.", "Gate entrance", "open", None, None),
    (1, "block_a", "wet_floor", "Water leaking onto the corridor floor outside room A-104, very slippery.", "Corridor outside A-104", "open", None, None),
    (14, "library", "wet_floor", "Wet floor near the library entrance after mopping, no sign placed.", "Entrance lobby", "resolved", "Housekeeping", "Floor dried and wet-floor signage added (demo record)."),
]


def seed(reset: bool = False) -> int:
    if reset and config.DB_PATH.exists():
        config.DB_PATH.unlink()
    db.init_db()
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with db.connect() as conn:
        if conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]:
            return 0
        for days, b, cat, desc, loc, status, who, notes in DEMO:
            created = (now - timedelta(days=days)).isoformat()
            r = repository.create_report(
                conn,
                {"description": desc, "building": b, "category": cat, "location_details": loc},
                is_demo=True, created_at=created,
            )
            if status != "open" or who:
                changes = {"assignee": who}
                if notes:
                    changes["resolution_notes"] = notes
                if status != "open":
                    changes["status"] = status
                repository.update_report(conn, r["id"], changes)
        return len(DEMO)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true")
    n = seed(ap.parse_args().reset)
    print(f"Seeded {n} demo reports." if n else "Database already has reports; nothing seeded.")

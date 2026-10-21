import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    description      TEXT NOT NULL,
    building         TEXT NOT NULL,
    location_details TEXT,
    category         TEXT NOT NULL,
    category_source  TEXT NOT NULL,           -- ai_confirmed | manual | ai_overridden | admin_changed
    severity         INTEGER NOT NULL,
    priority_override TEXT,                   -- NULL = use computed level
    status           TEXT NOT NULL DEFAULT 'open',
    assignee         TEXT,
    resolution_notes TEXT,
    image_filename   TEXT,
    ai_status        TEXT NOT NULL DEFAULT 'not_run',  -- ok | uncertain | unavailable | not_run
    ai_category      TEXT,
    ai_result        TEXT,                    -- full JSON analysis as returned by the model
    is_demo          INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    resolved_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_reports_group ON reports(building, category);
CREATE TABLE IF NOT EXISTS status_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id  INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    field      TEXT NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    note       TEXT,
    changed_by TEXT NOT NULL DEFAULT 'admin',
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id             TEXT PRIMARY KEY,          -- the generated image filename stem
    image_filename TEXT NOT NULL,
    result         TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s)


@contextmanager
def connect(path=None):
    path = path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path=None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)

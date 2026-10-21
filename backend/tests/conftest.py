import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture()
def tmp_env(tmp_path, monkeypatch):
    """Isolated DB + upload dir for each test."""
    from app import config, db

    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    db.init_db()
    return tmp_path

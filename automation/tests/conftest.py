"""Shared fixtures. `db` gives every money-safety test an isolated SQLite file
seeded with the real schema, with every module's get_db pointed at it."""
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def db(tmp_path):
    schema = (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(tmp_path / "test.db"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(schema)
    conn.commit()

    targets = [
        "utils.db.get_db",
        "utils.approvals.get_db",
        "commands.apply_approved.get_db",
        "commands.strategize.get_db",
        "commands.tune_ads.get_db",
    ]
    patchers = []
    for t in targets:
        try:
            p = patch(t, return_value=conn)
            p.start()
            patchers.append(p)
        except (AttributeError, ModuleNotFoundError):
            pass
    yield conn
    for p in patchers:
        p.stop()
    conn.close()

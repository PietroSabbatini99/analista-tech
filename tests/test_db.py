import sqlite3
import os
import tempfile
from modules.db import init_db, get_connection


def test_init_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "companies" in tables
        assert "daily_scores" in tables
        assert "alerts" in tables
        assert "news_cache" in tables
    finally:
        os.unlink(db_path)


def test_get_connection_returns_row_factory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        init_db(db_path)
        conn = get_connection(db_path)
        row = conn.execute("SELECT 1 AS val").fetchone()
        assert row["val"] == 1
        conn.close()
    finally:
        os.unlink(db_path)

from __future__ import annotations

import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from agent.guards import safe_db_path

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def db_path() -> Path:
    return safe_db_path()


def connect() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise FileNotFoundError("Falta data/erp.db. Corré: python scripts/seed.py")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)

"""Crea data/erp.db a partir de data/seed.sql."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed.sql"
DB = ROOT / "data" / "erp.db"


def main() -> None:
    if not SEED.exists():
        sys.exit(f"No encuentro {SEED}")
    DB.parent.mkdir(parents=True, exist_ok=True)
    sql = SEED.read_text(encoding="utf-8")
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()
    print(f"OK seed -> {DB}")


if __name__ == "__main__":
    main()

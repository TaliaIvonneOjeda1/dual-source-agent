"""Chequea las 3 mentiras plantadas: API vs SQL. Sin LLM."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.seed import main as seed_db  # noqa: E402
from erp_mock.app import app  # noqa: E402
from erp_mock.db import db_path  # noqa: E402

TOKEN = {"Authorization": "Bearer demo-token"}


def sql_contacto(contacto_id: int) -> dict | None:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, email FROM contactos WHERE id = ?",
            (contacto_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def sql_comprobante(numero: str) -> dict | None:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT numero_completo, total FROM comprobantes WHERE numero_completo = ?",
            (numero,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def main() -> None:
    seed_db()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200, health.text

    no_token = client.get("/contactos/501")
    assert no_token.status_code == 401, no_token.text

    api_501 = client.get("/contactos/501", headers=TOKEN)
    assert api_501.status_code == 200, api_501.text
    sql_501 = sql_contacto(501)
    assert sql_501 is not None
    assert api_501.json()["email"] == "ana@mail.com"
    assert sql_501["email"] == "ana.viejo@mail.com"
    assert api_501.json()["email"] != sql_501["email"]
    print("OK mentira 1: contacto 501 mail distinto API vs SQL")

    numero = "FC A 0003-00001890"
    api_fc = client.get(f"/comprobantes/{numero}", headers=TOKEN)
    sql_fc = sql_comprobante(numero)
    assert api_fc.status_code == 404, api_fc.text
    assert sql_fc is not None
    print("OK mentira 2: factura en SQL y 404 en la API")

    numero_imp = "FC A 0001-00004500"
    api_imp = client.get(f"/comprobantes/{numero_imp}", headers=TOKEN)
    sql_imp = sql_comprobante(numero_imp)
    assert api_imp.status_code == 200, api_imp.text
    assert sql_imp is not None
    assert float(api_imp.json()["total"]) == 15000.00
    assert float(sql_imp["total"]) == 150000.00
    print("OK mentira 3: importe con un cero de menos en la API")

    match = client.get("/contactos/502", headers=TOKEN)
    sql_502 = sql_contacto(502)
    assert match.status_code == 200
    assert sql_502 is not None
    assert match.json()["email"] == sql_502["email"]
    print("OK control: contacto 502 coincide")

    print("TODOS LOS CHEQUEOS OK")


if __name__ == "__main__":
    main()

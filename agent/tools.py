"""Tools de solo lectura. El modelo las elige; Python las ejecuta."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import httpx
from dotenv import load_dotenv

from agent.guards import GuardError, clean_tool_args, erp_base_url, safe_db_path
from agent.log import log_event

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _api_base() -> str:
    return erp_base_url()


def _token() -> str:
    return os.getenv("ERP_API_TOKEN", "demo-token")


def _db_path() -> Path:
    return safe_db_path()


def _connect() -> sqlite3.Connection:
    path = _db_path()
    if not path.exists():
        raise GuardError("Falta la base data/erp.db. Corré: python scripts/seed.py")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def get_contacto_api(contacto_id: int) -> dict:
    """Trae un contacto desde la API REST del ERP (JSON + token). No usa SQL.

    Args:
        contacto_id: ID numérico del contacto, por ejemplo 501.
    """
    url = f"{_api_base()}/contactos/{contacto_id}"
    try:
        response = httpx.get(url, headers=_headers(), timeout=5.0, follow_redirects=False)
    except httpx.HTTPError:
        payload = {
            "found": False,
            "source": "api",
            "error": "erp_unreachable",
            "detail": "No pude hablar con el ERP (puerto 8001). ¿Está prendido python scripts/run_erp.py?",
        }
        log_event({"tool": "get_contacto_api", "args": {"contacto_id": contacto_id}, "http_status": None, "ok": False})
        return payload
    log_event(
        {
            "tool": "get_contacto_api",
            "args": {"contacto_id": contacto_id},
            "http_status": response.status_code,
            "ok": response.status_code == 200,
        }
    )
    if response.status_code == 200:
        return {"found": True, "source": "api", "data": response.json()}
    return {
        "found": False,
        "source": "api",
        "http_status": response.status_code,
    }


def get_contacto_sql(contacto_id: int) -> dict:
    """Trae un contacto desde SQL (tablas de verdad). SELECT acotado, nunca SQL libre.

    Args:
        contacto_id: ID numérico del contacto, por ejemplo 501.
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, empresa_id, nombre, email, telefono FROM contactos WHERE id = ?",
            (contacto_id,),
        ).fetchone()
    finally:
        conn.close()
    found = row is not None
    log_event(
        {
            "tool": "get_contacto_sql",
            "args": {"contacto_id": contacto_id},
            "http_status": None,
            "ok": found,
        }
    )
    if not found:
        return {"found": False, "source": "sql"}
    return {"found": True, "source": "sql", "data": dict(row)}


def get_comprobante_api(numero_completo: str) -> dict:
    """Trae un comprobante desde la API REST del ERP. No usa SQL.

    Args:
        numero_completo: Número tal cual, por ejemplo 'FC A 0003-00001890'.
    """
    url = f"{_api_base()}/comprobantes/{numero_completo}"
    try:
        response = httpx.get(url, headers=_headers(), timeout=5.0, follow_redirects=False)
    except httpx.HTTPError:
        payload = {
            "found": False,
            "source": "api",
            "error": "erp_unreachable",
            "detail": "No pude hablar con el ERP (puerto 8001). ¿Está prendido python scripts/run_erp.py?",
        }
        log_event(
            {
                "tool": "get_comprobante_api",
                "args": {"numero_completo": numero_completo},
                "http_status": None,
                "ok": False,
            }
        )
        return payload
    log_event(
        {
            "tool": "get_comprobante_api",
            "args": {"numero_completo": numero_completo},
            "http_status": response.status_code,
            "ok": response.status_code == 200,
        }
    )
    if response.status_code == 200:
        return {"found": True, "source": "api", "data": response.json()}
    return {
        "found": False,
        "source": "api",
        "http_status": response.status_code,
    }


def get_comprobante_sql(numero_completo: str) -> dict:
    """Trae un comprobante desde SQL. SELECT acotado por numero_completo.

    Args:
        numero_completo: Número tal cual, por ejemplo 'FC A 0003-00001890'.
    """
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, empresa_id, tipo, punto_venta, numero, numero_completo, total, estado
            FROM comprobantes
            WHERE numero_completo = ?
            """,
            (numero_completo,),
        ).fetchone()
    finally:
        conn.close()
    found = row is not None
    log_event(
        {
            "tool": "get_comprobante_sql",
            "args": {"numero_completo": numero_completo},
            "http_status": None,
            "ok": found,
        }
    )
    if not found:
        return {"found": False, "source": "sql"}
    return {"found": True, "source": "sql", "data": dict(row)}


DISPATCH = {
    "get_contacto_api": get_contacto_api,
    "get_contacto_sql": get_contacto_sql,
    "get_comprobante_api": get_comprobante_api,
    "get_comprobante_sql": get_comprobante_sql,
}


def run_tool(name: str, args: dict) -> dict:
    try:
        cleaned = clean_tool_args(name, args)
        fn = DISPATCH[name]
        return fn(**cleaned)
    except GuardError as exc:
        return {"found": False, "error": exc.public}

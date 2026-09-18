"""Tools de solo lectura. El modelo las elige; Python las ejecuta."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import httpx
from dotenv import load_dotenv

from agent.log import log_event

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def _api_base() -> str:
    return os.getenv("ERP_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def _token() -> str:
    return os.getenv("ERP_API_TOKEN", "demo-token")


def _db_path() -> Path:
    raw = os.getenv("ERP_DB_PATH", "data/erp.db")
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


def get_contacto_api(contacto_id: int) -> dict:
    """Trae un contacto desde la API REST del ERP (JSON + token). No usa SQL.

    Args:
        contacto_id: ID numérico del contacto, por ejemplo 501.
    """
    url = f"{_api_base()}/contactos/{contacto_id}"
    try:
        response = httpx.get(url, headers=_headers(), timeout=5.0)
    except httpx.HTTPError as exc:
        payload = {"found": False, "source": "api", "error": str(exc)}
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
        "detail": response.text,
    }


def get_contacto_sql(contacto_id: int) -> dict:
    """Trae un contacto desde SQL (tablas de verdad). SELECT acotado, nunca SQL libre.

    Args:
        contacto_id: ID numérico del contacto, por ejemplo 501.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
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
        response = httpx.get(url, headers=_headers(), timeout=5.0)
    except httpx.HTTPError as exc:
        payload = {"found": False, "source": "api", "error": str(exc)}
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
        "detail": response.text,
    }


def get_comprobante_sql(numero_completo: str) -> dict:
    """Trae un comprobante desde SQL. SELECT acotado por numero_completo.

    Args:
        numero_completo: Número tal cual, por ejemplo 'FC A 0003-00001890'.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
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
    fn = DISPATCH.get(name)
    if fn is None:
        return {"found": False, "error": f"tool desconocida: {name}"}
    return fn(**args)

"""ERP mock: API REST que lee las tablas api_* (la copia desfasada)."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from erp_mock.auth import require_token
from erp_mock.db import connect, row_to_dict

app = FastAPI(
    title="ERP mock",
    version="0.1.0",
    description="API desfasada a propósito (tablas `api_*`). En /docs: Authorize → `demo-token`.",
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/contactos/{contacto_id}", dependencies=[Depends(require_token)])
def get_contacto(contacto_id: int) -> dict:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id, empresa_id, nombre, email, telefono FROM api_contactos WHERE id = ?",
            (contacto_id,),
        ).fetchone()
    finally:
        conn.close()
    data = row_to_dict(row)
    if data is None:
        raise HTTPException(status_code=404, detail="contacto no encontrado en la API")
    return data


@app.get("/comprobantes/{numero_completo}", dependencies=[Depends(require_token)])
def get_comprobante(numero_completo: str) -> dict:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT id, empresa_id, tipo, punto_venta, numero, numero_completo, total, estado
            FROM api_comprobantes
            WHERE numero_completo = ?
            """,
            (numero_completo,),
        ).fetchone()
    finally:
        conn.close()
    data = row_to_dict(row)
    if data is None:
        raise HTTPException(status_code=404, detail="comprobante no encontrado en la API")
    return data

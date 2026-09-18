"""ERP mock: API REST que lee las tablas api_* (la copia desfasada)."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from erp_mock.auth import require_token
from erp_mock.db import connect, row_to_dict

app = FastAPI(
    title="ERP mock",
    version="0.1.0",
    description="API desfasada a propósito (tablas `api_*`). En /docs: Authorize → `demo-token`.",
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "testserver"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_params(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "El id o el número de comprobante no es válido. Probá 501 o FC A 0003-00001890."
        },
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/contactos/{contacto_id}", dependencies=[Depends(require_token)])
def get_contacto(
    contacto_id: int = Path(ge=1, le=999_999),
) -> dict:
    try:
        conn = connect()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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
def get_comprobante(
    numero_completo: str = Path(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,39}$"),
) -> dict:
    try:
        conn = connect()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
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

from __future__ import annotations

from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field, ValidationError

from agent.guards import QUERY_MAX, RateLimiter, gemini_key_set, safe_db_path, erp_base_url, GuardError
from agent.llm import run_query

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
STATIC_DIR = Path(__file__).resolve().parent / "static"
QUERY_LIMITER = RateLimiter(max_calls=10, window_s=60.0)

app = FastAPI(
    title="Verificador de dos fuentes",
    version="0.1.0",
    description="El modelo elige tools. Python compara API vs SQL. UI en GET /.",
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "testserver"],
)


class QueryIn(BaseModel):
    q: str = Field(min_length=1, max_length=QUERY_MAX)


def _public_error(status: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail=detail)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_body(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": (
                "La consulta está vacía o es demasiado larga "
                f"(máximo {QUERY_MAX} caracteres). Elegí un ejemplo o escribí un contacto o factura."
            )
        },
    )


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/cv")
def cv() -> FileResponse:
    path = STATIC_DIR / "CV-Talia-Ojeda.pdf"
    if not path.exists():
        raise _public_error(404, "No encontré el CV en el servidor.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="CV-Talia-Ojeda.pdf",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    erp_ok = False
    try:
        response = httpx.get(
            erp_base_url() + "/health",
            timeout=2.0,
            follow_redirects=False,
        )
        erp_ok = response.status_code == 200
    except (httpx.HTTPError, GuardError):
        erp_ok = False
    db_ok = False
    try:
        db_ok = safe_db_path().exists()
    except GuardError:
        db_ok = False
    return {
        "agent": True,
        "erp": erp_ok,
        "db": db_ok,
        "gemini_key": gemini_key_set(),
    }


@app.post("/agent/query")
def query(body: QueryIn) -> dict:
    if not QUERY_LIMITER.allow():
        raise _public_error(
            429,
            "Hay demasiadas consultas seguidas. Esperá un minuto y reintentá una sola vez "
            "(así no se gasta la cuota gratis de Gemini).",
        )
    question = body.q.strip()
    if not question:
        raise _public_error(
            422,
            "Escribí qué contacto o factura querés comparar, o tocá un ejemplo a la izquierda.",
        )
    try:
        finding = run_query(question)
    except RuntimeError as exc:
        text = str(exc)
        if "GEMINI_API_KEY" in text:
            raise _public_error(
                503,
                "Falta GEMINI_API_KEY en el archivo .env. Copiá .env.example, pegá la key "
                "de https://aistudio.google.com/apikey y no subas ese archivo.",
            ) from exc
        if "8001" in text or "ERP" in text or "run_erp" in text:
            raise _public_error(
                503,
                "No pude hablar con el ERP (puerto 8001). "
                "En otra terminal, con (.venv): python scripts/run_erp.py y dejala abierta.",
            ) from exc
        if "erp.db" in text or "seed.py" in text:
            raise _public_error(
                503,
                "Falta la base data/erp.db. Corré: python scripts/seed.py",
            ) from exc
        raise _public_error(
            500,
            "Algo falló en el agente. Revisá que el ERP siga prendido y que .env tenga la key.",
        ) from exc
    except genai_errors.ClientError as exc:
        text = str(exc)
        if "429" in text or "RESOURCE_EXHAUSTED" in text:
            raise _public_error(
                429,
                "Se acabó la cuota gratis de Gemini por ahora "
                "(este modelo deja unas 20 consultas al día). "
                "Esperá un minuto y reintentá una sola vez. "
                "El mock y los tests (Camino A) no usan Gemini.",
            ) from exc
        raise _public_error(
            502,
            "Gemini rechazó el pedido. Reintentá en un minuto.",
        ) from exc
    except genai_errors.ServerError as exc:
        raise _public_error(
            503,
            "Gemini está saturado. Reintentá en un minuto.",
        ) from exc
    except ValidationError:
        raise _public_error(
            500,
            "El resultado no se pudo armar. Reintentá; si sigue, avisá con la pregunta que usaste.",
        )
    return finding.model_dump()

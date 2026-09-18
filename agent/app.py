from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from google.genai import errors as genai_errors
from pydantic import BaseModel

from agent.llm import run_query

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Verificador de dos fuentes",
    version="0.1.0",
    description="El modelo elige tools. Python compara API vs SQL. UI en GET /.",
)


class QueryIn(BaseModel):
    q: str


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/cv")
def cv() -> FileResponse:
    path = STATIC_DIR / "CV-Talia-Ojeda.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="CV no encontrado")
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
            os.getenv("ERP_API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
            + "/health",
            timeout=2.0,
        )
        erp_ok = response.status_code == 200
    except httpx.HTTPError:
        erp_ok = False
    return {"agent": True, "erp": erp_ok}


@app.post("/agent/query")
def query(body: QueryIn) -> dict:
    try:
        finding = run_query(body.q)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except genai_errors.ClientError as exc:
        text = str(exc)
        if "429" in text or "RESOURCE_EXHAUSTED" in text:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Se acabó la cuota gratis de Gemini por ahora "
                    "(este modelo deja unas 20 consultas al día). "
                    "Esperá un minuto y reintentá una sola vez. "
                    "El mock y los tests (Camino A) no usan Gemini."
                ),
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Gemini rechazó el pedido. Reintentá en un minuto.",
        ) from exc
    except genai_errors.ServerError as exc:
        raise HTTPException(
            status_code=503,
            detail="Gemini está saturado. Reintentá en un minuto.",
        ) from exc
    return finding.model_dump()

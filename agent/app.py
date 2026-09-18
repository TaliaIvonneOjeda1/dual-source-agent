from __future__ import annotations

from fastapi import FastAPI, HTTPException
from google.genai import errors as genai_errors
from pydantic import BaseModel

from agent.llm import run_query

app = FastAPI(
    title="dual-source-agent",
    version="0.1.0",
    description="El modelo elige tools. Python compara API vs SQL. POST /agent/query con {\"q\": \"...\"}.",
)


class QueryIn(BaseModel):
    q: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/agent/query")
def query(body: QueryIn) -> dict:
    try:
        finding = run_query(body.q)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except genai_errors.ClientError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini rechazó el pedido: {exc}",
        ) from exc
    except genai_errors.ServerError as exc:
        raise HTTPException(
            status_code=503,
            detail="Gemini está saturado. Reintentá en un minuto.",
        ) from exc
    return finding.model_dump()

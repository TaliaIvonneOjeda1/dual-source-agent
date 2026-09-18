from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from agent.llm import run_query

app = FastAPI(title="dual-source-agent", version="0.1.0")


class QueryIn(BaseModel):
    q: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/agent/query")
def query(body: QueryIn) -> dict:
    finding = run_query(body.q)
    return finding.model_dump()

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal[
    "match",
    "mismatch",
    "missing_in_api",
    "missing_in_sql",
    "insufficient_evidence",
]
Entity = Literal["contacto", "comprobante", "desconocido"]
Severity = Literal["alta", "media", "baja", "nula"]
Action = Literal["revisar_humano", "ninguna"]


class Finding(BaseModel):
    status: Status
    entity: Entity
    id: str | None = None
    field: str | None = None
    api_value: str | None = None
    sql_value: str | None = None
    severity: Severity
    action: Action
    evidence: list[str] = Field(default_factory=list)

"""Compara API vs SQL. Sin LLM: dos dicts entran, un Finding sale."""

from __future__ import annotations

from typing import Any

from agent.schema import Finding


def _s(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _called(side: dict | None) -> bool:
    return side is not None


def _found(side: dict | None) -> bool:
    return bool(side) and side.get("found") is True


def _data(side: dict | None) -> dict:
    if not side:
        return {}
    return side.get("data") or {}


def _insufficient(entity: str, ident: str | None, evidence: list[str]) -> Finding:
    return Finding(
        status="insufficient_evidence",
        entity=entity if entity in ("contacto", "comprobante") else "desconocido",
        id=ident,
        field=None,
        api_value=None,
        sql_value=None,
        severity="media",
        action="revisar_humano",
        evidence=evidence or ["no se consultaron API y SQL"],
    )


def compare_entity(
    *,
    entity: str,
    ident: str | None,
    api_side: dict | None,
    sql_side: dict | None,
    fields: list[str],
    evidence: list[str],
) -> Finding:
    if not _called(api_side) or not _called(sql_side):
        return _insufficient(entity, ident, evidence)

    api_ok = _found(api_side)
    sql_ok = _found(sql_side)

    if not api_ok and not sql_ok:
        return _insufficient(entity, ident, evidence + ["no hay fila en API ni en SQL"])

    if not api_ok and sql_ok:
        sql_val = _data(sql_side)
        preview = _s(sql_val.get(fields[0])) if fields else None
        return Finding(
            status="missing_in_api",
            entity=entity,  # type: ignore[arg-type]
            id=ident,
            field=None,
            api_value=None,
            sql_value=preview,
            severity="alta",
            action="revisar_humano",
            evidence=evidence,
        )

    if api_ok and not sql_ok:
        api_val = _data(api_side)
        preview = _s(api_val.get(fields[0])) if fields else None
        return Finding(
            status="missing_in_sql",
            entity=entity,  # type: ignore[arg-type]
            id=ident,
            field=None,
            api_value=preview,
            sql_value=None,
            severity="alta",
            action="revisar_humano",
            evidence=evidence,
        )

    api_val = _data(api_side)
    sql_val = _data(sql_side)
    for field in fields:
        left = _s(api_val.get(field))
        right = _s(sql_val.get(field))
        if left != right:
            return Finding(
                status="mismatch",
                entity=entity,  # type: ignore[arg-type]
                id=ident,
                field=field,
                api_value=left,
                sql_value=right,
                severity="alta",
                action="revisar_humano",
                evidence=evidence,
            )

    return Finding(
        status="match",
        entity=entity,  # type: ignore[arg-type]
        id=ident,
        field=None,
        api_value=_s(api_val.get(fields[0])) if fields else None,
        sql_value=_s(sql_val.get(fields[0])) if fields else None,
        severity="nula",
        action="ninguna",
        evidence=evidence,
    )


def build_finding(gathered: dict, evidence: list[str]) -> Finding:
    """Arma el Finding a partir de lo que las tools trajeron en esta corrida."""
    has_contacto = gathered.get("contacto_api") is not None or gathered.get(
        "contacto_sql"
    ) is not None
    has_comp = gathered.get("comprobante_api") is not None or gathered.get(
        "comprobante_sql"
    ) is not None

    if has_comp:
        api_side = gathered.get("comprobante_api")
        sql_side = gathered.get("comprobante_sql")
        ident = None
        for side in (sql_side, api_side):
            data = _data(side)
            if data.get("numero_completo"):
                ident = str(data["numero_completo"])
                break
        ident = ident or gathered.get("comprobante_id")
        return compare_entity(
            entity="comprobante",
            ident=ident,
            api_side=api_side,
            sql_side=sql_side,
            fields=["total", "estado", "empresa_id", "tipo"],
            evidence=evidence,
        )

    if has_contacto:
        api_side = gathered.get("contacto_api")
        sql_side = gathered.get("contacto_sql")
        ident = None
        for side in (sql_side, api_side):
            data = _data(side)
            if data.get("id") is not None:
                ident = str(data["id"])
                break
        ident = ident or gathered.get("contacto_id")
        return compare_entity(
            entity="contacto",
            ident=ident,
            api_side=api_side,
            sql_side=sql_side,
            fields=["email", "nombre", "telefono", "empresa_id"],
            evidence=evidence,
        )

    return _insufficient("desconocido", None, evidence)

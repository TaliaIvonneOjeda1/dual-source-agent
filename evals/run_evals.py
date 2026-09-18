"""Evals live: Gemini elige tools, Python compara. El ERP tiene que estar en :8001."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.llm import run_query  # noqa: E402

CASES_PATH = ROOT / "evals" / "cases.json"
MAX_TRIES = 3


def _has_tool(evidence: list[str], name: str) -> bool:
    return any(name in item for item in evidence)


def _run_once(question: str):
    last_error: Exception | None = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            return run_query(question)
        except Exception as exc:
            last_error = exc
            print(f"  intento {attempt}/{MAX_TRIES} falló: {type(exc).__name__}: {exc}")
            if attempt < MAX_TRIES:
                time.sleep(4 * attempt)
    raise last_error  # type: ignore[misc]


def main() -> None:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    passed = 0
    rows: list[dict] = []

    for case in cases:
        print("=" * 60)
        print(f"{case['id']}: {case['q']}")
        try:
            finding = _run_once(case["q"])
        except Exception as exc:
            print(f"FAIL  no se pudo correr: {exc}")
            rows.append({"id": case["id"], "ok": False, "detail": str(exc)})
            continue

        payload = finding.model_dump()
        print(json.dumps(payload, ensure_ascii=False))

        reasons: list[str] = []
        if payload["status"] not in case["expect_status"]:
            reasons.append(
                f"status {payload['status']!r} no está en {case['expect_status']}"
            )
        expect_field = case.get("expect_field")
        if expect_field and payload.get("field") != expect_field:
            reasons.append(f"field {payload.get('field')!r} != {expect_field!r}")
        for tool_name in case.get("require_tools") or []:
            if not _has_tool(payload.get("evidence") or [], tool_name):
                reasons.append(f"falta tool {tool_name} en evidence")

        ok = not reasons
        if ok:
            passed += 1
            print("OK")
        else:
            print("FAIL ", "; ".join(reasons))
        rows.append({"id": case["id"], "ok": ok, "detail": "; ".join(reasons)})

    total = len(cases)
    print("=" * 60)
    print(f"SCORE {passed}/{total}")
    for row in rows:
        mark = "OK" if row["ok"] else "FAIL"
        extra = f" — {row['detail']}" if row["detail"] else ""
        print(f"  {mark}  {row['id']}{extra}")
    if passed < total:
        print("Hay fallos. Se documentan; no se esconden.")
        sys.exit(1)


if __name__ == "__main__":
    main()

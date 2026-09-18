"""Las 4 preguntas live. El ERP (:8001) y el agente (:8000) tienen que estar prendidos."""

from __future__ import annotations

import json
import sys

import httpx

QUESTIONS = [
    "Verifica el mail del contacto 501 entre API y SQL",
    "Verifica si la factura FC A 0003-00001890 existe en API y en SQL",
    "Verifica el importe de la factura FC A 0001-00004500 entre API y SQL",
    "Verifica si el contacto 502 coincide entre API y SQL",
]


def main() -> None:
    for question in QUESTIONS:
        print("=" * 60)
        print(question)
        try:
            response = httpx.post(
                "http://127.0.0.1:8000/agent/query",
                json={"q": question},
                timeout=120.0,
            )
        except httpx.HTTPError as exc:
            print("No pude hablar con el agente:", exc)
            print("Prendé: python scripts/run_erp.py y python scripts/run_agent.py")
            sys.exit(1)
        print("HTTP", response.status_code)
        try:
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        except ValueError:
            print(response.text)
        if response.status_code != 200:
            sys.exit(1)


if __name__ == "__main__":
    main()

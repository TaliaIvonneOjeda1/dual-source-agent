"""Loop Gemini: el modelo elige tools; Python hace el diff al final."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agent.diff import build_finding
from agent.prompts import SYSTEM
from agent.schema import Finding
from agent.tools import run_tool

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

MAX_ROUNDS = 6

FUNCTION_DECLARATIONS = [
    types.FunctionDeclaration(
        name="get_contacto_api",
        description="Trae un contacto desde la API REST del ERP (JSON + token). No usa SQL.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "contacto_id": {
                    "type": "integer",
                    "description": "ID numérico del contacto, por ejemplo 501.",
                }
            },
            "required": ["contacto_id"],
        },
    ),
    types.FunctionDeclaration(
        name="get_contacto_sql",
        description="Trae un contacto desde SQL. SELECT acotado, nunca SQL libre.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "contacto_id": {
                    "type": "integer",
                    "description": "ID numérico del contacto, por ejemplo 501.",
                }
            },
            "required": ["contacto_id"],
        },
    ),
    types.FunctionDeclaration(
        name="get_comprobante_api",
        description="Trae un comprobante desde la API REST del ERP. No usa SQL.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "numero_completo": {
                    "type": "string",
                    "description": "Número tal cual, por ejemplo 'FC A 0003-00001890'.",
                }
            },
            "required": ["numero_completo"],
        },
    ),
    types.FunctionDeclaration(
        name="get_comprobante_sql",
        description="Trae un comprobante desde SQL. SELECT acotado por numero_completo.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "numero_completo": {
                    "type": "string",
                    "description": "Número tal cual, por ejemplo 'FC A 0003-00001890'.",
                }
            },
            "required": ["numero_completo"],
        },
    ),
]


def _client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Falta GEMINI_API_KEY en .env. Creala en https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=key)


def _remember(gathered: dict, name: str, args: dict, result: dict) -> None:
    if name == "get_contacto_api":
        gathered["contacto_api"] = result
        gathered["contacto_id"] = str(args.get("contacto_id"))
    elif name == "get_contacto_sql":
        gathered["contacto_sql"] = result
        gathered["contacto_id"] = str(args.get("contacto_id"))
    elif name == "get_comprobante_api":
        gathered["comprobante_api"] = result
        gathered["comprobante_id"] = str(args.get("numero_completo", ""))
    elif name == "get_comprobante_sql":
        gathered["comprobante_sql"] = result
        gathered["comprobante_id"] = str(args.get("numero_completo", ""))


def _coerce_args(args: dict) -> dict:
    out = dict(args)
    if "contacto_id" in out:
        out["contacto_id"] = int(out["contacto_id"])
    return out


def run_query(question: str) -> Finding:
    client = _client()
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    tool = types.Tool(function_declarations=FUNCTION_DECLARATIONS)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[tool],
        temperature=0,
    )
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=question)])
    ]
    gathered: dict = {}
    evidence: list[str] = []

    for _ in range(MAX_ROUNDS):
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        candidate = response.candidates[0] if response.candidates else None
        if candidate is None or candidate.content is None:
            break
        fn_calls = [
            part.function_call
            for part in (candidate.content.parts or [])
            if part.function_call is not None
        ]
        if not fn_calls:
            break
        contents.append(candidate.content)
        response_parts: list[types.Part] = []
        for fc in fn_calls:
            name = fc.name or ""
            args = _coerce_args(dict(fc.args or {}))
            result = run_tool(name, args)
            _remember(gathered, name, args, result)
            label = name
            if "contacto_id" in args:
                label = f"{name}({args['contacto_id']})"
            elif "numero_completo" in args:
                label = f"{name}({args['numero_completo']})"
            evidence.append(label)
            response_parts.append(
                types.Part.from_function_response(name=name, response=result)
            )
        contents.append(types.Content(role="user", parts=response_parts))

        both_contacto = "contacto_api" in gathered and "contacto_sql" in gathered
        both_comp = "comprobante_api" in gathered and "comprobante_sql" in gathered
        if both_contacto or both_comp:
            break

    return build_finding(gathered, evidence)

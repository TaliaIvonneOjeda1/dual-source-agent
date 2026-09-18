"""Tests del diff. Sin Gemini, sin red."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.diff import build_finding, compare_entity  # noqa: E402


def _api(data: dict | None, found: bool = True) -> dict:
    if not found:
        return {"found": False, "source": "api"}
    return {"found": True, "source": "api", "data": data}


def _sql(data: dict | None, found: bool = True) -> dict:
    if not found:
        return {"found": False, "source": "sql"}
    return {"found": True, "source": "sql", "data": data}


class DiffTests(unittest.TestCase):
    def test_mail_501_mismatch(self) -> None:
        finding = compare_entity(
            entity="contacto",
            ident="501",
            api_side=_api({"id": 501, "email": "ana@mail.com", "nombre": "Ana Perez"}),
            sql_side=_sql({"id": 501, "email": "ana.viejo@mail.com", "nombre": "Ana Perez"}),
            fields=["email", "nombre"],
            evidence=["get_contacto_api(501)", "get_contacto_sql(501)"],
        )
        self.assertEqual(finding.status, "mismatch")
        self.assertEqual(finding.field, "email")
        self.assertEqual(finding.api_value, "ana@mail.com")
        self.assertEqual(finding.sql_value, "ana.viejo@mail.com")

    def test_factura_missing_in_api(self) -> None:
        finding = compare_entity(
            entity="comprobante",
            ident="FC A 0003-00001890",
            api_side=_api(None, found=False),
            sql_side=_sql({"numero_completo": "FC A 0003-00001890", "total": 150000.0}),
            fields=["total"],
            evidence=["get_comprobante_api", "get_comprobante_sql"],
        )
        self.assertEqual(finding.status, "missing_in_api")

    def test_single_source_is_insufficient(self) -> None:
        finding = build_finding(
            {"contacto_api": _api({"id": 501, "email": "ana@mail.com"})},
            evidence=["get_contacto_api(501)"],
        )
        self.assertEqual(finding.status, "insufficient_evidence")

    def test_match(self) -> None:
        finding = compare_entity(
            entity="contacto",
            ident="502",
            api_side=_api({"id": 502, "email": "luis.gomez@papelera.com"}),
            sql_side=_sql({"id": 502, "email": "luis.gomez@papelera.com"}),
            fields=["email"],
            evidence=["api", "sql"],
        )
        self.assertEqual(finding.status, "match")


if __name__ == "__main__":
    unittest.main()

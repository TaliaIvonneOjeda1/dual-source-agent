"""Validaciones locales. Sin Gemini, sin red."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.guards import (  # noqa: E402
    GuardError,
    clean_tool_args,
    erp_base_url,
    safe_db_path,
)
from agent.tools import run_tool  # noqa: E402


class GuardTests(unittest.TestCase):
    def test_tool_unknown_is_rejected(self) -> None:
        result = run_tool("drop_table", {"contacto_id": 501})
        self.assertFalse(result["found"])
        self.assertIn("no está permitida", result["error"])

    def test_extra_tool_args_are_dropped(self) -> None:
        cleaned = clean_tool_args(
            "get_contacto_sql",
            {"contacto_id": 501, "sql": "DROP TABLE contactos"},
        )
        self.assertEqual(cleaned, {"contacto_id": 501})

    def test_sql_injection_in_invoice_is_rejected(self) -> None:
        with self.assertRaises(GuardError):
            clean_tool_args(
                "get_comprobante_sql",
                {"numero_completo": "FC A 0001'; DROP TABLE comprobantes;--"},
            )

    def test_valid_invoice_passes(self) -> None:
        cleaned = clean_tool_args(
            "get_comprobante_sql",
            {"numero_completo": "FC A 0003-00001890"},
        )
        self.assertEqual(cleaned["numero_completo"], "FC A 0003-00001890")

    def test_contacto_out_of_range(self) -> None:
        with self.assertRaises(GuardError):
            clean_tool_args("get_contacto_api", {"contacto_id": 0})
        with self.assertRaises(GuardError):
            clean_tool_args("get_contacto_api", {"contacto_id": 10_000_000})

    def test_db_path_cannot_leave_repo(self) -> None:
        with self.assertRaises(GuardError):
            safe_db_path("C:/Windows/System32/drivers/etc/hosts")
        with self.assertRaises(GuardError):
            safe_db_path("/etc/hosts")
        with mock.patch.dict(os.environ, {"ERP_DB_PATH": "../fuera.db"}):
            with self.assertRaises(GuardError):
                safe_db_path()

    def test_erp_url_must_be_localhost(self) -> None:
        with mock.patch.dict(os.environ, {"ERP_API_BASE_URL": "http://evil.example/"}):
            with self.assertRaises(GuardError):
                erp_base_url()
        with mock.patch.dict(os.environ, {"ERP_API_BASE_URL": "http://127.0.0.1:8001"}):
            self.assertEqual(erp_base_url(), "http://127.0.0.1:8001")


class HttpGuardTests(unittest.TestCase):
    def test_empty_query_is_spanish_422(self) -> None:
        from fastapi.testclient import TestClient

        from agent.app import app

        client = TestClient(app)
        response = client.post("/agent/query", json={"q": ""})
        self.assertEqual(response.status_code, 422)
        self.assertIn("vacía", response.json()["detail"])

    def test_ready_never_returns_the_gemini_key(self) -> None:
        from fastapi.testclient import TestClient

        from agent.app import app

        client = TestClient(app)
        payload = client.get("/ready").json()
        self.assertIn("gemini_key", payload)
        self.assertIsInstance(payload["gemini_key"], bool)
        blob = str(payload).lower()
        self.assertNotIn("gemini_api_key", blob)
        self.assertNotIn("sk-", blob)


if __name__ == "__main__":
    unittest.main()

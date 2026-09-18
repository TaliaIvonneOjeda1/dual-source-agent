"""Límites en Python: no confiar en el texto del usuario ni en lo que pida el modelo."""

from __future__ import annotations

import os
import re
import time
from collections import deque
from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

QUERY_MAX = 400
CONTACTO_MIN = 1
CONTACTO_MAX = 999_999
NUMERO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,39}$")
ALLOWED_ERP_HOSTS = {"127.0.0.1", "localhost"}
TOOL_ARGS = {
    "get_contacto_api": ("contacto_id",),
    "get_contacto_sql": ("contacto_id",),
    "get_comprobante_api": ("numero_completo",),
    "get_comprobante_sql": ("numero_completo",),
}


class GuardError(ValueError):
    def __init__(self, public: str) -> None:
        super().__init__(public)
        self.public = public


def gemini_key_set() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _is_outside_path(raw: str) -> bool:
    native = Path(raw)
    windows = PureWindowsPath(raw)
    return bool(
        native.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or raw.startswith(("\\\\", "//"))
    )


def safe_db_path(raw: str | None = None) -> Path:
    value = (raw or os.getenv("ERP_DB_PATH", "data/erp.db")).strip() or "data/erp.db"
    if _is_outside_path(value):
        raise GuardError("La ruta de la base está fuera del proyecto.")
    resolved = (ROOT / Path(value)).resolve()
    root = ROOT.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GuardError("La ruta de la base está fuera del proyecto.") from exc
    return resolved


def erp_base_url() -> str:
    raw = os.getenv("ERP_API_BASE_URL", "http://127.0.0.1:8001").strip()
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "http" or host not in ALLOWED_ERP_HOSTS:
        raise GuardError(
            "ERP_API_BASE_URL solo puede ser http://127.0.0.1 o localhost. "
            "Este mock no sale a internet."
        )
    return raw.rstrip("/")


def clean_tool_args(name: str, args: dict) -> dict:
    allowed = TOOL_ARGS.get(name)
    if allowed is None:
        raise GuardError("Esa consulta no está permitida.")
    cleaned: dict = {}
    for key in allowed:
        if key not in args:
            raise GuardError("Faltan datos para consultar.")
        cleaned[key] = args[key]
    if "contacto_id" in cleaned:
        try:
            contacto_id = int(cleaned["contacto_id"])
        except (TypeError, ValueError) as exc:
            raise GuardError("El id de contacto tiene que ser un número.") from exc
        if not CONTACTO_MIN <= contacto_id <= CONTACTO_MAX:
            raise GuardError("Ese id de contacto está fuera de rango.")
        cleaned["contacto_id"] = contacto_id
    if "numero_completo" in cleaned:
        numero = str(cleaned["numero_completo"]).strip()
        if not NUMERO_RE.fullmatch(numero):
            raise GuardError("Ese número de comprobante no tiene un formato válido.")
        cleaned["numero_completo"] = numero
    return cleaned


class RateLimiter:
    """Tope local para no quemar la cuota de Gemini ni saturar el mock."""

    def __init__(self, max_calls: int = 10, window_s: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window_s = window_s
        self._hits: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_s
        while self._hits and self._hits[0] < cutoff:
            self._hits.popleft()
        if len(self._hits) >= self.max_calls:
            return False
        self._hits.append(now)
        return True

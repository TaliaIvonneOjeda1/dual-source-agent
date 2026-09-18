"""Enciende el ERP mock en http://127.0.0.1:8001"""

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    uvicorn.run("erp_mock.app:app", host="127.0.0.1", port=8001, reload=False)

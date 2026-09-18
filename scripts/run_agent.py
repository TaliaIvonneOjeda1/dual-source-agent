"""Enciende el agente en http://127.0.0.1:8000 (el ERP tiene que estar en :8001)."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("agent.app:app", host="127.0.0.1", port=8000, reload=False)

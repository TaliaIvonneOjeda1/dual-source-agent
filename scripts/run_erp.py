"""Enciende el ERP mock en http://127.0.0.1:8001"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("erp_mock.app:app", host="127.0.0.1", port=8001, reload=False)

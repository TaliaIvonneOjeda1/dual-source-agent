# dual-source-agent

Agente en Python que **verifica si la API REST y el SQL de un ERP mock dicen lo mismo**.

No es un chatbot. El modelo (Gemini) solo elige herramientas. La comparación la hace Python. El hallazgo sale en JSON, con evidencia. El agente **no escribe** en el ERP.

Datos sintéticos. Nada de clientes reales.

## Estado

Día 0: cimientos del repo. El ERP mock y el agente se arman en los bloques siguientes.

## Cómo se simula el ERP

Dos fuentes que *deberían* coincidir y, a propósito, no coinciden:

- API REST en `localhost:8001` (JSON + token), como Táctica / Postman
- SQLite en `data/erp.db`, como HeidiSQL

El agente (puerto `8000`) es un cliente más: llama HTTP y hace `SELECT` acotados.

## Requisitos

- Python 3.12+ (probado con 3.14)
- Una API key de [Gemini](https://aistudio.google.com/apikey) (no se sube al repo)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Editá `.env` y pegá `GEMINI_API_KEY`. Ese archivo está en `.gitignore`.

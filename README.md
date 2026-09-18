# dual-source-agent

Agente en Python que **verifica si la API REST y el SQL de un ERP mock dicen lo mismo**.

No es un chatbot. Gemini solo elige herramientas. Un módulo Python hace el diff. El hallazgo sale en JSON, con evidencia. El agente **no escribe** en el ERP.

Datos sintéticos. Nada de clientes reales.

## El problema

En un ERP, la API (lo que consume un bot o Postman) y el SQL (lo que ves en una pantalla tipo HeidiSQL) **deberían** coincidir. A veces no: un mail viejo, una factura que no sale por API, un importe con un cero de menos.

Un humano cruza las dos fuentes a mano. Este repo automatiza ese cruce: el modelo junta evidencia, las reglas comparan, y si hay desfasaje la acción es `revisar_humano`.

En planta el mismo patrón sería lote vs remito. Acá el mock es contacto y factura, para no fingir un dominio que no operé.

## Cómo se simula el ERP

Dos procesos locales:

| Pieza | Puerto | Qué simula |
|---|---|---|
| `erp_mock` | `8001` | API REST + Bearer (`demo-token`). Lee tablas `api_*` (copia **desfasada**). |
| SQLite `data/erp.db` | archivo | SQL de verdad (tablas `contactos` / `comprobantes`). |
| Agente | `8000` | Cliente: llama HTTP y hace `SELECT` acotados (nunca SQL libre). |

Tres mentiras plantadas en `data/seed.sql`:

1. Contacto **501**: API `ana@mail.com` vs SQL `ana.viejo@mail.com`
2. Factura **FC A 0003-00001890**: existe en SQL, API 404
3. Factura **FC A 0001-00004500**: SQL `150000.00` vs API `15000.00`

Control que coincide: contacto **502**.

## Demo para evaluadores (acceso)

No hay URL en la nube: el camp pide llevar agentes a producción con honestidad, no un wrapper desplegado. El acceso es **este repo**. Todo se corre desde la carpeta del proyecto. Hay dos caminos.

### Setup (una vez)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Si `python` no se reconoce, usá `py`. Hace falta Python 3.12+.

### Camino A — sin API key (30 segundos)

Prueba el mock y el diff **sin Gemini**:

```powershell
python scripts/check_erp.py
python -m unittest tests.test_diff -v
```

Esperado: `TODOS LOS CHEQUEOS OK` y 4 tests `OK`. Un aviso de Starlette/`httpx2` no es un error.

`check_erp.py` siembra la base y afirma las 3 mentiras. `test_diff.py` cubre mismatch, missing, match e `insufficient_evidence`.

### Camino B — interfaz live (2 procesos)

Hace falta una key gratuita de [Google AI Studio](https://aistudio.google.com/apikey). Copiá `.env.example` → `.env` y pegá `GEMINI_API_KEY`. No subas ese archivo.

```powershell
python scripts/seed.py
```

**Terminal 1** — ERP. Dejala abierta cuando veas `Uvicorn running on http://127.0.0.1:8001`:

```powershell
python scripts/run_erp.py
```

**Terminal 2** — agente (otra ventana; activá el venv si hace falta):

```powershell
python scripts/run_agent.py
```

Abrí **http://127.0.0.1:8000**. Tiene que decir **ERP listo**. Tocá un ejemplo a la izquierda (completa la caja) y dale a **Comparar**. No es un chatbot: ves API vs SQL lado a lado.

Si Gemini está saturado (503), reintentá. El modelo vigente está en `.env.example` (`GEMINI_MODEL`).

Paso a paso, tabla de resultados y qué hacer si falla: [`docs/DEMO.md`](docs/DEMO.md).

## Ejemplo de Finding

```json
{
  "status": "mismatch",
  "entity": "contacto",
  "id": "501",
  "field": "email",
  "api_value": "ana@mail.com",
  "sql_value": "ana.viejo@mail.com",
  "severity": "alta",
  "action": "revisar_humano",
  "evidence": ["get_contacto_api(501)", "get_contacto_sql(501)"]
}
```

`status` puede ser: `match` | `mismatch` | `missing_in_api` | `missing_in_sql` | `insufficient_evidence`.

Si no se llamaron las **dos** fuentes, el diff no inventa: `insufficient_evidence`.

## Evals

Seis casos live (`evals/cases.json`): 3 desfasajes, 1 match, id 99999, y un adversarial (“¿cuál es el mail del 501?”) para que no responda de una sola fuente.

```powershell
python evals/run_evals.py
```

Corrida local: **6/6**. Un caso pidió retry por 503 de Google; está documentado, no escondido.

## Qué faltaría en producción

- Auth real (no `demo-token`), secretos en un vault, red privada al ERP.
- HITL de verdad: cola de findings, no solo el campo `action`.
- Observabilidad y evals en CI (acá Gemini es live y a veces 503).
- MCP para tools remotas; LangGraph si el flujo tiene más de un paso con estado; Azure AI Foundry / Semantic Kernel si el camp despliega ahí.
- El agente **seguiría sin escribir** en el ERP hasta tener un contrato de corrección humana.

v1 es deliberadamente chica: Python, FastAPI, SQLite, Gemini function calling. Sin Streamlit, Docker ni Azure en este repo.

## Stack

Python 3.12+ (probado en 3.14), FastAPI, httpx, sqlite3, Pydantic, `google-genai`.

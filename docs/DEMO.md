# Cómo correr la demo

Guía para quien clone el repo. El README tiene el contexto; acá están los pasos y los resultados esperados.

Hace falta Python 3.12+. El agente live usa una API key de [Gemini](https://aistudio.google.com/apikey) (gratis). El mock del ERP y los tests del diff **no** la necesitan.

## 1. Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

En `.env` pegá `GEMINI_API_KEY` solo si vas a usar el agente (camino B). Ese archivo está en `.gitignore`.

## 2. Camino A — sin Gemini (mock + diff)

Un comando cubre las tres mentiras plantadas en la API vs SQL:

```powershell
python scripts/check_erp.py
```

Tests del comparador (sin red):

```powershell
python -m unittest tests.test_diff -v
```

Esperado: 4 tests OK.

## 3. Camino B — agente live (2 procesos)

```powershell
python scripts/seed.py
```

Terminal 1:

```powershell
python scripts/run_erp.py
```

http://127.0.0.1:8001 — API del ERP mock (tablas `api_*`, token `demo-token`).

Terminal 2:

```powershell
python scripts/run_agent.py
```

http://127.0.0.1:8000 — el agente. Gemini elige tools; Python compara.

Las 4 preguntas de la demo:

```powershell
python scripts/demo.py
```

### Desde el navegador

- ERP: http://127.0.0.1:8001/docs → **Authorize** → `demo-token` (sin la palabra `Bearer`) → `GET /contactos/501`
- Agente: http://127.0.0.1:8000/docs → `POST /agent/query` con cuerpo `{"q":"Verifica el mail del contacto 501 entre API y SQL"}`

Detalle de la API del mock (Postman / SQL equivalente): [`como_probar_erp.md`](como_probar_erp.md).

## 4. Resultados esperados

| Pregunta | `status` | Qué tiene que verse |
|---|---|---|
| Mail del contacto 501 | `mismatch` | API `ana@mail.com` vs SQL `ana.viejo@mail.com`; `evidence` con las dos tools |
| Factura `FC A 0003-00001890` | `missing_in_api` | Existe en SQL; la API responde 404 |
| Importe `FC A 0001-00004500` | `mismatch` | API `15000.00` vs SQL `150000.00` |
| Contacto 502 | `match` | Mismo email en ambas fuentes |

Si Gemini no llamó las dos fuentes, el diff no inventa el dato: `insufficient_evidence`.

Si Google satura el modelo (503), reintentar. El nombre vigente está en `.env.example` (`GEMINI_MODEL`).

## 5. Evals

Seis casos live, incluido un adversarial (`¿cuál es el mail del 501?`) para que no responda de una sola fuente:

```powershell
python evals/run_evals.py
```

Corrida de referencia: 6/6 (un caso requirió retry por 503 de Google).

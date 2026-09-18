# Cómo correr la demo

Guía para quien clone el repo. El README tiene el contexto; acá están los pasos y lo que tenés que ver.

Hace falta **Python 3.12+**. En PowerShell: `python --version`. Si `python` no existe, probá `py --version`.

El agente live usa una API key de [Gemini](https://aistudio.google.com/apikey) (gratis). El mock del ERP y los tests del diff **no** la necesitan.

Todo se corre **desde la carpeta del repo** (`dual-source-agent`).

## 1. Setup (una sola vez)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Tiene que verse `(.venv)` a la izquierda del prompt. El venv no se hereda: **cada terminal nueva** (y cada `+` en Cursor) hay que correr otra vez `.venv\Scripts\activate` antes de `python` o `pip`.

Si Cursor avisa que instalaste paquetes en el entorno global y ofrece Create: **no**. Cerrá el aviso y activá `.venv`.

Si `Activate.ps1` está bloqueado, en esa terminal: `Set-ExecutionPolicy -Scope Process Bypass`.

## 2. Camino A — sin Gemini (mock + diff)

No hace falta `.env` ni API key.

```powershell
python scripts/check_erp.py
python -m unittest tests.test_diff -v
```

Esperado:

- `TODOS LOS CHEQUEOS OK` (las 3 mentiras + el control 502)
- `Ran 4 tests` … `OK`

Si aparece un aviso `StarletteDeprecationWarning` / `httpx2`, ignorarlo: no es un error. El resultado que cuenta es el `OK` del final.

## 3. Camino B — interfaz live (2 procesos)

Hace falta la key. Una sola vez:

```powershell
copy .env.example .env
```

Abrí `.env` y pegá la key en `GEMINI_API_KEY` (sin comillas). No subas ese archivo.

Sembrar la base:

```powershell
python scripts/seed.py
```

Esperado: `OK seed -> ...\data\erp.db`

### Terminal 1 — ERP (dejala abierta)

Primero `.venv\Scripts\activate` (tiene que verse `(.venv)`). `seed.py` puede andar sin venv porque solo usa SQLite; `run_erp.py` no: necesita `uvicorn`.

```powershell
python scripts/run_erp.py
```

Esperá a ver: `Uvicorn running on http://127.0.0.1:8001`. **No cierres esta terminal** ni apretés Ctrl+C: el mock tiene que seguir vivo.

### Terminal 2 — agente (otra ventana)

En Cursor / VS Code: `+` en el panel de terminales, o una PowerShell nueva. Activá el venv otra vez si hace falta (`.venv\Scripts\activate`).

```powershell
python scripts/run_agent.py
```

Esperá a ver: `Uvicorn running on http://127.0.0.1:8000`.

Eso **ya es el front**. No hay otro comando para “levantar la pantalla”. Abrí Chrome o Edge y pegá la URL (Enter). No la ejecutes en PowerShell.

### Navegador

1. Abrí **http://127.0.0.1:8000** (esa es la demo; no es un chat).
2. Arriba tiene que decir **ERP listo**. Si dice que falta el ERP, volvé a la terminal 1.
3. A la izquierda tocá un ejemplo (eso **completa** la caja; no corre solo).
4. Dale a **Comparar**. Tarda unos segundos.

| Ejemplo | Qué tenés que ver |
|---|---|
| 501, mail distinto | **No coinciden** · API `ana@mail.com` vs SQL `ana.viejo@mail.com` |
| Factura que la API no tiene | **Está en la base, no en la API** · `FC A 0003-00001890` |
| Importe con un cero menos | **No coinciden** · API `15000.00` vs SQL `150000.00` |
| 502 Luis | **Coinciden** |
| “¿Cuál es el mail del 501?” | No inventa el mail de una sola fuente; pide las dos o marca evidencia insuficiente |

El programa **no corrige** el ERP. Si hay desfasaje, la acción es que lo mire una persona.

### Si algo falla

| Qué ves | Qué suele ser |
|---|---|
| `python` no se reconoce | Usá `py` en lugar de `python` |
| `No module named 'uvicorn'` / `'dotenv'` | Esa terminal no tiene `(.venv)`. Corré `.venv\Scripts\activate` y repetí el comando |
| El agente arranca y la UI dice que falta el ERP | La terminal 1 se cerró o `run_erp.py` no quedó escuchando en 8001 |
| Error 503 / saturado | Gemini a veces se satura. Reintentá en un minuto. El modelo está en `.env.example` (`GEMINI_MODEL`) |
| Error 401 en el ERP | Token `demo-token` (en Swagger: Authorize → pegá solo `demo-token`) |

## 4. Opcional — script de las 4 preguntas

Con **las dos** terminales todavía abiertas, en una **tercera**:

```powershell
python scripts/demo.py
```

## 5. Opcional — Swagger del mock

http://127.0.0.1:8001/docs → **Authorize** (candado) → `demo-token` (sin la palabra Bearer) → `GET /contactos/501`.

Detalle de pedidos y el SQL equivalente: [`como_probar_erp.md`](como_probar_erp.md).

## 6. Evals (live, necesita key + los 2 procesos)

ERP (`run_erp.py`) y agente (`run_agent.py`) tienen que seguir corriendo. Abrí **otra** terminal (no uses las que tienen Uvicorn). Activá el venv y mirá que el prompt diga `(.venv)`:

```powershell
.venv\Scripts\activate
python evals/run_evals.py
```

Un comando por línea. Si el prompt no muestra `(.venv)`, va a fallar con `No module named 'dotenv'`.

Corrida de referencia: 6/6 (un caso requirió retry por 503 de Google).

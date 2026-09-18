# Cómo probar el ERP mock (sin el agente)

Dos terminales no hacen falta todavía. El script `scripts/check_erp.py` siembra la base y pega contra la API en memoria.

## 1. Sembrar la base

Desde la raíz del repo:

```text
.venv\Scripts\python.exe scripts/seed.py
```

Crea `data/erp.db`. Ese archivo no se sube a GitHub.

## 2. Encender la API

```text
.venv\Scripts\python.exe scripts/run_erp.py
```

Queda en `http://127.0.0.1:8001`.

## 3. Pedidos (Postman, Swagger o el navegador)

Header en todos menos `/health`:

```text
Authorization: Bearer demo-token
```

En http://127.0.0.1:8001/docs : botón **Authorize** (candado) → pegá `demo-token` (sin la palabra Bearer).

| Pedido | Qué tenés que ver |
|---|---|
| `GET /health` | `{"status":"ok"}` |
| `GET /contactos/501` | email `ana@mail.com` |
| `GET /contactos/502` | email `luis.gomez@papelera.com` (coincide con SQL) |
| `GET /comprobantes/FC A 0003-00001890` | **404** |
| `GET /comprobantes/FC A 0001-00004500` | total `15000.0` |

## 4. El SQL equivalente (la "pantalla / HeidiSQL")

```sql
SELECT id, email FROM contactos WHERE id = 501;
-- ana.viejo@mail.com  (distinto a la API)

SELECT numero_completo, total FROM comprobantes WHERE numero_completo = 'FC A 0003-00001890';
-- una fila; la API no la tiene

SELECT numero_completo, total FROM comprobantes WHERE numero_completo = 'FC A 0001-00004500';
-- 150000.0  (la API tiene 15000.0)
```

Si falta el token: **401**.

Chequeo automático (las 3 mentiras):

```text
.venv\Scripts\python.exe scripts/check_erp.py
```

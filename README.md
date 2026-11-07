# Cada hora cuenta · Planificación asistencial Teletón

MVP de la Botathon 2026: reemplaza el Excel de planificación asistencial. Contexto y decisiones: `CONTEXTO.md` y `CLAUDE.md`. Enunciado: `docs/desafio.md`.

**Arquitectura:** Blue Prism (VM) → `POST /api/v1/buk/sync` → FastAPI + SQLite → React.

## Cómo levantarlo (computador del backend)

Todos los comandos se ejecutan desde la carpeta del proyecto.

### 1. Instalar (una sola vez)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

En Windows, la ruta es `.venv\Scripts\pip`.

### 2. Generar la carga inicial (una sola vez, necesita los Excel del kit en `data/raw/`)

```bash
.venv/bin/python herramientas/generar_parametros.py
```

Crea `data/generados/parametros.xlsx` y `data/generados/entradas_planificacion.xlsx`.

### 3. Levantar el backend

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Al arrancar crea la base SQLite (`data/planificacion.db`, 28 tablas) y hace la carga inicial. `--host 0.0.0.0` permite que la VM de Blue Prism se conecte. Documentación de la API: http://localhost:8000/docs.

Para empezar de cero, se detiene el backend y se borra `data/planificacion.db`.

### 4. Enviar BUK (sin la VM, con el simulador del bot)

```bash
.venv/bin/python herramientas/simular_bot.py
```

Hace lo mismo que hará Blue Prism: lee el BUK y la hoja Excepciones, arma el JSON y lo envía. El backend calcula y el dashboard queda con datos. Con `--guardar carga.json` solo guarda el JSON, que sirve como ejemplo para el bot.

Para la demo de **detección de cambios**, después de la primera carga se envía un BUK «nuevo»:

```bash
.venv/bin/python herramientas/simular_bot.py --cambios
```

Trae un alta (999001, desde julio), una baja (71027), un cambio de jornada (134561, 40 → 30 h desde julio) y un cambio de cargo (117024, desde julio). El backend los detecta comparando con la carga anterior, los guarda en la tabla `cambios` y recalcula: la planificación cambia solo desde el mes en que rige cada cambio. Se ven en la sección Historial del dashboard.

### 5. Frontend

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173.

## Endpoints

| Endpoint | Quién llama | Para qué |
|---|---|---|
| `GET /api/salud` | Bot y frontend | Estado de la API y de la base |
| `POST /api/v1/buk/sync` | Blue Prism | Enviar la carga de BUK y el reparto multi-instituto; recalcula |
| `GET /api/v1/buk/ultima-version` | Blue Prism | Última carga aceptada (consulta) |
| `GET /api/v1/dashboard/kpis?it=&mes=` | Frontend | Profesionales, horas, atenciones, meta y FOJA |
| `GET /api/v1/dashboard/institutos?mes=` | Frontend | Totales por instituto |
| `GET /api/v1/profesionales?it=&mes=` | Frontend | Detalle por profesional con sus estados |
| `GET /api/v1/excepciones?it=` | Frontend | Alertas agrupadas y errores de la última carga |
| `GET /api/v1/parametros` · `PUT /api/v1/parametros/{clave}` | Frontend | Ver y cambiar parámetros (recalcula) |
| `GET /api/v1/versiones` | Frontend | Historial de versiones del cálculo |
| `GET /api/v1/cambios?it=&tipo=` | Frontend | Cambios detectados (altas, bajas, modificaciones) y cambios de parámetros |

## Pruebas y verificación

```bash
.venv/bin/python -m pytest backend/tests -v
```

```bash
.venv/bin/python herramientas/verificar_motor.py
```

El verificador compara el cálculo con el Excel de planificación: los 7 casos de prueba coinciden y la coincidencia estricta es de 96,3 % (98,2 % sin las diferencias conocidas del Excel).

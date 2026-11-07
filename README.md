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

Al arrancar crea la base SQLite (`data/planificacion.db`, 28 tablas) y hace la carga inicial. En bases existentes agrega, sin borrar datos, las columnas de huella del envío y cobertura completa. `--host 0.0.0.0` permite que la VM de Blue Prism se conecte. Documentación de la API: http://localhost:8000/docs.

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

### Contrato de carga y reintentos

- Por defecto una carga es **parcial**: actualiza únicamente `PersonaId + IT + Periodo` recibidos. La ausencia de otra persona no es una baja.
- Para reemplazar un reporte **nacional completo**, incluir `periodos_completos`, por ejemplo `["2026-06-01", "2026-07-01"]`. Solo esos meses permiten bajas por ausencia. También se permite un mes completo sin contratos. No declarar cobertura completa para un fragmento ni para un solo instituto.
- Las filas rechazadas identificables conservan su contrato previo. Si una exclusión no identifica persona e instituto, el backend rechaza la declaración de cobertura completa (422): hay que corregirla o enviar una actualización parcial.
- El simulador ya declara los meses completos del BUK. Blue Prism debe usar el mismo campo para detectar bajas por ausencia. Cada envío parcial distinto necesita su propio `ejecucion_id`; reutilizarlo no agrega otro lote.
- Los repartos multi-instituto se validan por fila y se actualizan por persona, instituto y mes, sin borrar los demás meses. Para anular horas de un reparto ya informado, enviar `HorasSemanales: 0`. Los rechazos quedan en `/api/v1/excepciones`; sus conteos se informan aparte como `reparto_validas` y `reparto_excluidas` en la primera respuesta.
- Mismo `ejecucion_id` y mismo contenido publicado: devuelve la versión existente. Mismo ID con otro contenido: **409**, sin modificar datos. La identidad se comprueba con el JSON normalizado, no solo con `hash_archivo`.
- Si el cálculo falla: **503**, la carga se revierte y queda un intento fallido en el historial. La última planificación publicada no cambia. Se puede reintentar el mismo ID y contenido. Si entretanto se aceptó una carga posterior, se devuelve 409 para evitar sobrescribirla con un reintento antiguo; revisar los datos y usar un nuevo ID.
- Las ejecuciones previas a esta reparación no tienen huella verificable: su reutilización devuelve 409 y requiere un nuevo ID. No se eliminan sus datos ni versiones.

Los contratos se calculan solo en meses que intersectan su vigencia. Las asignaciones y los ajustes se aplican únicamente en sus meses vigentes; los rechazados no cuentan. No se agregó un prorrateo diario: los meses de ingreso o término parcial siguen usando las entradas mensuales disponibles.

Un profesional existente sin semanas hábiles no recibe un cero válido: ese mes se excluye del cálculo y queda un error `RN-15` con el mes y el motivo. Un cero explícito sí es válido. Las altas sin entradas de planificación mantienen la estimación con calendario, señalada como `ALERTA`.

### Ejecutar las comprobaciones

```bash
.venv/bin/python -m pytest backend/tests -v
```

```bash
.venv/bin/python herramientas/verificar_motor.py
```

Verificado tras la reparación: **37 pruebas aprobadas** (13 de integración y 24 de regresión, estas últimas sin Excel). Las comprobaciones usan SQLite temporal, no la base de trabajo.

El verificador compara el cálculo con el Excel de planificación: los 7 casos de prueba coinciden y la coincidencia estricta es de 96,3 % (98,2 % aplicando las exclusiones del verificador). Persisten 94 diferencias fuera de esas exclusiones, en 25 filas: estos resultados no certifican que todas las reglas del desafío estén implementadas ni reemplazan la prueba real con Blue Prism.

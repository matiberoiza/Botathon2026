# Botathon 2026 · Desafío Teletón «Cada hora cuenta»

## Qué estamos construyendo

Un MVP que reemplaza el Excel de planificación asistencial de Teletón (más de 600 profesionales, todos los institutos del país). Incorpora los reportes de BUK (dotación) y SIC (atenciones realizadas), aplica reglas parametrizables y calcula, por profesional y por mes, las horas de atención directa, indirecta y no asistencial (NAS), las horas disponibles y la meta de atenciones.

El enunciado completo está en `docs/desafio.md`. Léelo cuando necesites detalle de requisitos o de la rúbrica.

Es una hackathon de unas 13 horas (viernes 20:21 a sábado 09:45). Prioridad: un núcleo sólido que funcione de punta a punta antes que muchas funciones a medias.

## Arquitectura acordada

**Fuente: plan de sprints y tablero del equipo (6 de noviembre de 2026).** Flujo: **Blue Prism (VM) → `POST /api/v1/buk/sync` (JSON) → FastAPI + SQLite → React**. **Base de datos: SQLite** (decidido el 7 de noviembre de 2026; reemplaza a SQL Server). Revisión del plan, riesgos y tarjetas que faltan: `docs/revision_plan_sprints.md`.

- **Blue Prism** corre en la VM de la organización y lo opera **una sola persona** (Vicente). El bot lee el Excel de BUK (y la hoja Excepciones), valida, normaliza, detecta cambios entre versiones y envía los datos por HTTP al backend. El proceso de Blue Prism NO vive en este repo.
- **Este repo** (se desarrolla fuera de la VM, un rol por capa):
  - `backend/`: API en FastAPI (rutas `/api/v1/...`). Recibe los datos del bot, los valida con Pydantic, los guarda en SQLite (un archivo `.db` en el computador del backend) y ejecuta el motor de cálculo de 8 pasos.
  - `frontend/`: React + Vite + Tailwind + Recharts + Lucide. Dashboard nacional con filtros por instituto y mes, vista por profesional, módulo de parámetros editable y comparativa SIC.
- **Traspaso de datos:** el bot llama a la API; no hay subida manual de Excel ni carpeta compartida.
- **Pendiente:** probar que la VM llega a esa máquina por HTTP (es el mayor riesgo).
- **Pendiente de confirmar con los mentores:** si el procesamiento de datos debe hacerse dentro de Blue Prism (las bases del sitio y el documento del desafío no dicen lo mismo). Si es así, el cálculo pasa al bot y este repo queda solo con la API de consulta y el frontend.

## Datos

- `data/raw/`: «Nac - Base contratos x mes» (BUK, unas 19 columnas) y «Nac - Planificación Asistencial x mes» (el Excel actual, unas 205 columnas; es la referencia de la lógica y la fuente de los casos de prueba). Datos ficticios.
- Nunca modificar `data/raw/`.
- Problemas de datos confirmados (lista completa y conteos en `docs/analisis_inicial.md`): encabezados fuera de la fila 1 (BUK en la fila 2, Dotacion_Asistencial en la 4), «O'Higgins» escrito de dos formas, vacíos guardados como texto `''`, entre otros. No hay profesionales de la planificación sin pareja en BUK: las 6 diferencias por instituto son de profesionales multi-instituto (BUK los registra en un solo instituto y el reparto viene de la hoja Excepciones). No se corrigen a mano: cada uno se convierte en una regla de validación que se reporta.
- Claves: profesional = `PersonaId`; contrato del mes = `PersonaId` + `IT` + `Periodo` (hay profesionales en dos o más institutos).
- El cargo se cruza con la hoja Distribución_NAC por cargo homologado.
- Mínimo de datos (ley chilena de protección de datos personales): guardar solo las columnas que usa el cálculo. De la fecha de nacimiento, como máximo el mes.
- No catalogar las 205 columnas una por una: las de licencias, vacaciones y permisos mes a mes se tratan como un patrón.

## Modelo de datos mínimo

Tablas: `profesionales`, `contratos_mes`, catálogos de parámetros, `resultados_planificacion` y `cambios` (trazabilidad: qué cambió, valor anterior, valor nuevo, fecha desde la que rige, quién y por qué).

Catálogos editables, extraídos automáticamente de las hojas Parámetros y Distribución_NAC (no transcritos a mano): institutos (código, nombre, zona), cargos homologados con % directa/indirecta/NAS por tramo y minutos estándar, asignaciones especiales y sus horas, factor grupal (Santiago/Concepción vs. otros institutos), días hábiles, feriados y vacaciones por mes e instituto.

## Lógica de cálculo (por profesional y mes)

1. Horas semanales por mes según la vigencia del contrato. En 2026: 44 h hasta abril y 42 h desde mayo.
2. Promedio ponderado anual de horas semanales → tramo: 40 h o más; entre 22 y 40; menos de 22. Marcar si hubo aumento o disminución de jornada.
3. Cargo homologado + tramo → % directa, % indirecta, % NAS.
4. Asignaciones especiales: se descuentan horas semanales fijas (Líder de equipo 2 h, Tutor docente 1 h, Comité paritario 0,5 h, Reunión sindical 0,25 h…). Máximo 2 asignaciones si el profesional tiene más de 30 h semanales; algunas requieren autorización de la dirección nacional.
5. Horas disponibles para atención, repartidas proporcionalmente entre directa e indirecta.
6. Atenciones = horas × 60 ÷ minutos estándar, **redondeando hacia abajo** (directa: 30, 40, 45 o 60 min; indirecta: 30 min). Las áreas grupales (Educación, Asistente Social, Arte, Deporte, Unidad Laboral) aplican además un % grupal y pacientes por grupo, distinto en Santiago/Concepción y en otros institutos.
7. Proyección anual con días hábiles, feriados (incluidos regionales, como Arica y Ñuble) y vacaciones (Aysén es distinto).
8. Meta de gestión = atenciones planificadas × 90% (parámetro). FOJA = horas mensuales disponibles para atención directa ÷ horas mensuales contratadas.

**Orden de los pasos 3 a 5 (confirmado).** La hoja Dotacion_Asistencial del Excel de referencia no tiene fórmulas (viene pegada como valores), así que el orden se reconstruyó comparando con los valores de sus 471 filas: primero los % por cargo y tramo; después las horas de asignaciones se suman al NAS (%NAS final = (horas NAS + horas de asignaciones) ÷ (horas semanales − colación)); al final, el resto se reparte entre directa e indirecta en la proporción de la tabla. Fórmulas y cuántas filas cuadran con cada una: `docs/analisis_inicial.md`. Ante cualquier diferencia, mandan los valores del Excel, no este resumen.

Casos especiales: multi-instituto (hoja Excepciones), reemplazos y plazo fijo, vacantes y cargos nuevos, licencias extensas (meses sin atención), cambio legal de jornada, zonas geográficas.

## Cómo trabajar en este repo

- Ningún porcentaje, minuto estándar, hora de asignación ni fecha va fijo en el código: todo sale de las tablas de parámetros.
- Casos de prueba: 2 o 3 profesionales del Excel de referencia (uno normal, uno con cambio de jornada, uno multi-instituto). El cálculo debe coincidir con el Excel en esos casos; escribe tests que lo verifiquen.
- Código simple y con comentarios en español: el equipo tiene que poder explicarlo ante el jurado.
- Antes de un cambio grande, propón el plan y espera confirmación.
- **`CONTEXTO.md` (raíz del proyecto) es el resumen vivo de todo lo hecho y decidido.** Léelo al empezar una sesión. Cada vez que hagas algo en el proyecto o el usuario entregue información nueva (documentos, decisiones, roles, arquitectura), actualízalo en el mismo turno y agrega una línea a su registro de cambios.
- **Git y GitHub:** autorizado por el equipo el 7 de noviembre de 2026. Repositorio público: https://github.com/matiberoiza/Botathon2026 (rama `main`). Haz commits o push solo cuando el usuario lo pida. El `.gitignore` excluye `data/raw/`, `data/entrada/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`, `node_modules/`, `dist/` y `.DS_Store`: los datos no se suben, aunque sean ficticios, y la cadena de conexión lleva contraseña.
- La ruta del archivo SQLite va en `backend/.env`; el `.db` no se sube a git. Rutas relativas; dependencias del backend en `requirements.txt` y del frontend en `frontend/package.json`.
- Dashboard accesible (es un criterio del jurado): buen contraste, navegable con teclado y un resumen en lenguaje simple.

## Estructura

```
data/raw/       Excel originales (solo lectura)
data/entrada/   archivos de cambios que deja el bot
docs/           enunciado, diccionario de datos, esquema T-SQL y análisis
backend/        API FastAPI + SQLite: config, db, schemas, carga_inicial, sincronizacion, motor, routers y tests
frontend/       React + Vite (src/pages: Resumen, Profesionales, Excepciones, Parametros, Historial)
herramientas/   scripts de apoyo (revisar_tipos.py: tipo de dato real de cada celda de un Excel)
```

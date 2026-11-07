# Revisión del plan de sprints y del tablero

**Documentos revisados:** `Plan_Sprints_Botathon_2026_Cada_Hora_Cuenta.docx` y el tablero de Canva «Botathon 2026 Tablero SCRUM Hackathon» (Gladys).
**Fecha:** 6 de noviembre de 2026.

## Conclusión

El plan y el tablero están bien armados: tarjetas por rol, duración estimada, casos de prueba asociados, flujo Backlog → To Do → In Progress → QA → Done y una definición de «terminado».

Antes de empezar hay que resolver tres cosas:

1. **La conexión de red entre la VM y el backend.** Es el mayor riesgo y hay que probarla primero.
2. **Agregar dos tarjetas que faltan.** Sin ellas no se llega al 95 % de coincidencia ni se pueden probar varios casos.
3. **Unificar los criterios** que hoy se contradicen entre documentos.

## 1. Arquitectura

**Blue Prism (VM) → `POST /api/v1/buk/sync` → FastAPI + SQL Server → React.**

- Reemplaza la decisión anterior de hacer «todo en Blue Prism». Hay que actualizar `CLAUDE.md`.
- Los datos llegan por JSON desde el bot: **ya no hay subida manual de Excel**.
- El backend del repo usa rutas `/api/...` y el plan usa `/api/v1/...`: hay que alinearlas.

## 2. Riesgo de red: probar antes que nada

El plan usa una API «para salvar restricciones de red entre la VM y la base», pero eso solo cambia el sentido del problema: ahora **la VM tiene que poder llegar al backend por HTTP**. Además el plan no dice **dónde corren FastAPI y SQL Server**.

**Acción:** antes de cualquier otra tarjeta, Vicente prueba un `POST` desde la VM hasta la máquina donde corra el backend.

## 3. Lo que ya existe en el repo

| Tarjeta | Avance | Falta |
|---|---|---|
| BACK-1 · Modelos y Pydantic | Esquema T-SQL de 24 tablas (`docs/esquema.sql`) y `backend/app/schemas.py` | Modelos de SQLAlchemy |
| BACK-2 · Motor de 8 pasos | Lógica reconstruida y verificada contra el Excel (`docs/analisis_inicial.md`); `parametros.xlsx` verificado | El código del motor |
| BACK-3 · Cambio legal 44 → 42 h | Regla confirmada: se recalculan las horas sin colación y se mantiene el NAS base (cuadra en 133 de 136 profesionales) | El código |
| FRONT-1 · Setup y layout | React + Vite + Tailwind funcionando y accesible | Barra lateral, filtro de instituto, íconos Lucide |
| QA-1 · CP-001 a CP-003 | Valores esperados del Excel para 134561, **117024 (CP-002)** y 134746 | Valores para 137732 (CP-001) y 71269 (CP-003) |
| RPA-1 · Lectura de BUK | Diccionario de datos con tipos verificados y `herramientas/revisar_tipos.py` | — |

## 4. Tarjetas que faltan

1. **Cargar los datos de planificación que no vienen en BUK** (Backend, Sprint 1): colación, asignaciones por persona, ausencias y semanas hábiles. Solo existen en el Excel de planificación y **sin ellos el motor no puede llegar al 95 %**. Ya están extraídos en `data/generados/entradas_planificacion.xlsx`.
2. **Crear archivos de prueba a propósito** (QA, Sprint 1): CP-006, CP-007, CP-011, CP-014, CP-015 y los casos E no se pueden probar con los datos del kit. Hay que armar copias del BUK con columna faltante, horas negativas, cargo sin parámetros, etc.

## 5. Correcciones a los casos de prueba

| Caso | Dice | Corrección |
|---|---|---|
| CP-002 | Promedio 42,33 h | (44×4 + 42×8) ÷ 12 = **42,67**; el Excel trunca y deja **42**. El tramo no cambia |
| CP-005 | 36 h Iquique + 8 h Coyhaique | Coyhaique tiene 8 h solo de enero a marzo y **6 h desde abril** |
| CP-008 | Horas disponibles 37 | Falta descontar el NAS: con 40 h, NAS 10 y 3 h de asignaciones quedan **27** |
| CP-003 | Válido en enero y febrero | Es válido, pero el Excel planifica **0 atenciones en febrero** (vacaciones colectivas y término el 28-02) |
| CP-011 | Vacante sin profesional | No hay vacantes en los datos: requiere archivo de prueba |

## 6. Inconsistencias entre documentos

| Tema | Plan de sprints | Tablero | Matriz de casos |
|---|---|---|---|
| Casos críticos | CP-001 a CP-020 | CP-001, 002, 003, 004, 014, 016, 020 | CP-001, 002, 003, 004, 006, 014, 015, 016, 020 |
| Inicio | 22:50 | 22:20 | — |
| Metodología | SCRUM | SCRUM | — |

- **Metodología:** se dijo que sería Kanban; en la práctica el tablero es un Scrumban (sprints + flujo de tarjetas).
- **Git:** la definición de «terminado» pide código versionado en Git, pero `CLAUDE.md` prohíbe hacer commits hasta que el equipo lo autorice. Hay que acordar cuándo se autoriza.
- **«14 institutos»:** BUK trae profesionales en **15** institutos y el catálogo tiene 18 códigos.

## 7. Decisiones pendientes del equipo

1. Dónde corren FastAPI y SQL Server, y si la VM llega a esa máquina.
2. Qué lista de casos críticos manda.
3. Cuándo se autoriza el uso de Git.
4. Qué tarjetas toma cada integrante.
5. Las preguntas abiertas del cálculo en `docs/analisis_inicial.md`: semanas hábiles de julio a diciembre, horas de asignaciones (¿catálogo o por persona?) y definición de la FOJA.

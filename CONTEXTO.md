# Contexto completo · Botathon 2026 «Cada hora cuenta»

> **Para la nueva conversación:** este archivo resume todo lo hecho y decidido en el proyecto. Léelo completo antes de actuar. Vive en la raíz del proyecto (`/Users/matiberoiza/Developer/botathon-teleton/CONTEXTO.md`), junto a `CLAUDE.md` (instrucciones del proyecto) y la carpeta `docs/`.
>
> **Regla:** cada vez que se haga algo en el proyecto o el usuario entregue información nueva (documentos, decisiones, cambios de roles o de arquitectura), **actualiza este archivo en el mismo turno**: corrige la sección que corresponda y anota el cambio en el registro del final.
>
> **Última actualización:** 7 de noviembre de 2026, 10:40.

---

## 1. Quién soy y cómo quiero trabajar

- Soy estudiante de **Ingeniería Informática en Duoc UC, de primer año** (casi terminando el segundo semestre). **Explícame con ejemplos simples**, sin dar por sabida la jerga.
- Responde **en español**.
- **Paso a paso:** haz **una tarea a la vez** y detente a mostrarme el resultado antes de seguir. No encadenes varios pasos de un plan. Si digo «todavía no hagas nada», no hagas nada.
- Los trabajos van **separados**: cada uno con su propio entregable y su criterio de «terminado».
- Cuando pido algo «en md» o «descargable», lo quiero como **archivo en `~/Downloads`, fuera del proyecto**, salvo que diga otra cosa. La excepción es **este `CONTEXTO.md`**, que vive en el proyecto y se mantiene siempre al día.
- **Documentos para compartir (desde el 7 de noviembre, 01:55):** todo documento nuevo que me entregues debe poder pasarse tal cual a mis compañeros:
  - solo con la información pedida y autocontenido;
  - sin referencias a archivos internos del proyecto (`docs/`, `herramientas/`, `backend/`, `CLAUDE.md`, este archivo, scripts);
  - sin menciones a versiones anteriores, a otras IA ni a la conversación;
  - las fuentes citadas son las que todo el equipo tiene: el desafío, los Excel del kit y los documentos del equipo por su nombre.

  No hace falta reescribir los documentos que ya existen.
- **Correcciones en .md (desde el 7 de noviembre, 02:00):** cada vez que comparta un archivo de un compañero y me des indicaciones de corrección, además de la respuesta en el chat entrégame un `.md` descargable en `~/Downloads` con esas correcciones, escrito para que el autor lo lea y lo aplique (con el mismo estilo de «documentos para compartir»).
- **Git:** no iniciar repositorio, no hacer commits ni crear el repo en GitHub hasta que el equipo lo autorice explícitamente.
- **Nunca modificar `data/raw/`** (los Excel originales, en solo lectura).
- Antes de un cambio grande: proponer el plan y esperar confirmación.
- Avisar apenas algo falle, en vez de seguir intentando solo.

---

## 2. El desafío

**Botathon 2026** (Duoc UC × SS&C Blue Prism × Fundación Teletón), desafío **«Cada hora cuenta»**. Enunciado completo: `docs/desafio.md` (copia del .docx `~/Downloads/Desafío Botathon 2026 - Cada hora cuenta.docx`, que además trae una imagen con el ejemplo del resumen esperado, transcrita en `docs/desafio.md`).

- **Horario:** hackathon nocturna, viernes 6 de noviembre ~22:20 / 22:50 → **sábado 7 de noviembre 09:00** (entrega y demo). `CLAUDE.md` menciona 09:45; el plan del equipo dice 09:00.
- **Problema:** la Teletón planifica en un **Excel gigante** (205 columnas, más de 600 profesionales, todos los institutos) cuántas horas de cada profesional van a atención **directa**, **indirecta** y **no asistencial (NAS)**, y de ahí la **meta de atenciones**. Se alimenta a mano desde BUK (dotación) y SIC (atenciones realizadas). Es frágil, no tiene trazabilidad, se versiona copiando hojas y los parámetros están escondidos.
- **Objetivo del MVP:** reemplazar ese Excel. Incorporar los datos sin copiar y pegar, detectar e informar errores, aplicar reglas parametrizables, calcular por profesional y mes, detectar cambios durante el año y mostrar un consolidado nacional con filtros.
- **Obligatorio:** **Blue Prism** como parte central y visible en la demo.
- **Indicadores:** Meta de gestión = atenciones planificadas × 90 %. FOJA = horas mensuales disponibles para atención directa ÷ horas mensuales contratadas.
- **Rúbrica del pitch (3 min) y demo (5 min):** problema y usuario, pertinencia del bot, innovación, funcionamiento del bot, viabilidad técnica, **accesibilidad e inclusión**, impacto medible, claridad y respuesta a preguntas.
- **Datos personales:** ley chilena; mínimo de datos (de la fecha de nacimiento, solo el mes), sin nombres ni RUT.

---

## 3. El equipo y los roles

| Persona | Rol |
|---|---|
| **Vicente Montenegro** | Blue Prism, en la VM de la organización (es el único con acceso a la VM) |
| **Andrés** | Backend (desarrollo). Antes era el encargado de las reglas de negocio |
| **Yo (Matías)** | **Frontend** (React) |
| **Gladys** | **El backend, la base de datos y el frontend corren en su computador.** Armó el tablero de tareas en Canva: <https://canva.link/rufv0kjba9ivzh2> |
| **Dante** | Hizo el diagrama AS-IS del proceso actual |
| QA y pitch | **Pendiente de definir** quién lo toma |

**Metodología:** me dijeron **Kanban**. El plan y el tablero dicen «SCRUM»; en la práctica es Scrumban (sprints + tablero de tarjetas).

---

## 4. Arquitectura vigente (del plan de sprints del equipo)

**Blue Prism (VM) → `POST /api/v1/buk/sync` (JSON) → FastAPI + SQLite → React**

> **Decisión del 7 de noviembre de 2026, 03:15: la base de datos es SQLite**, no SQL Server. Ya no hacen falta pyodbc, el driver ODBC ni un servidor de base de datos: la base es un archivo `.db` en el computador donde corre el backend (Andrés). Lo que diga «SQL Server» en el resto de este archivo o en los documentos anteriores debe leerse como SQLite. Pendiente: adaptar `backend/app/config.py` y `db.py`, `requirements.txt` (quitar pyodbc), el diccionario de datos y los documentos compartidos que mencionan SQL Server.

1. **Blue Prism** lee el Excel de BUK (hoja `Dotacion_2026`, encabezados en la fila 2) y la hoja `Excepciones`, valida, normaliza (por ejemplo «O´Higgins» → IT 61), detecta cambios entre versiones y envía los datos como JSON a la API.
2. **Backend (FastAPI)** valida con Pydantic, guarda en SQLite con SQLAlchemy y ejecuta el **motor de cálculo de 8 pasos**.
3. **Frontend (React)** consulta endpoints como `/api/v1/dashboard/kpis`, `/api/v1/dashboard/institutos/{it}`, `/api/v1/profesionales` y `/api/v1/parametros` (lectura y escritura), y muestra el dashboard.

**Historia de decisiones (para no confundirse):** la arquitectura cambió varias veces la noche del 6:
1. Python + SQLite + Streamlit (idea inicial de `CLAUDE.md`).
2. SQL Server + FastAPI + React, con subida manual de Excel desde la app.
3. «Todo en Blue Prism» (por los documentos de Andrés).
4. **Vigente:** el plan de sprints → stack web con el bot enviando por API. **Ya no hay subida manual de Excel.**

**Riesgos y pendientes de arquitectura:**
- **No está definido dónde corren FastAPI y SQL Server.** Mi Mac no tiene SQL Server ni Docker.
- **La VM tiene que poder llegar al backend por HTTP.** Es el mayor riesgo: probarlo antes que nada.
- Las rutas del backend actual son `/api/...`; el plan usa `/api/v1/...`. Hay que alinearlas.
- **Pendiente con los mentores:** si el procesamiento debe hacerse dentro de Blue Prism.

---

## 5. Herramientas

| Herramienta | Para qué |
|---|---|
| Blue Prism | RPA: el «robot» que lee el Excel y lo envía (obligatorio) |
| Python 3.14.3 | Lenguaje del backend y de las herramientas |
| FastAPI 0.162 + uvicorn | La API (las URL que reciben y responden) |
| Pydantic 2.14 | Valida la forma de cada JSON |
| SQLAlchemy 2.1 + pyodbc 5.4 | Puente entre Python y SQL Server |
| SQL Server (SSMS) | Base de datos |
| pandas 3.1 + openpyxl 3.1 | Leer Excel y calcular con tablas |
| React 19 + Vite 8 | Frontend |
| Tailwind 4 | Estilos |
| Recharts 3 | Gráficos |
| Lucide | Íconos (pedido en el plan, aún no instalado) |
| pytest + httpx | Pruebas del backend |

---

## 6. Estado del entorno en mi Mac

- Proyecto en `~/Developer/botathon-teleton`, fuera de iCloud (en este Mac pip se cuelga en carpetas sincronizadas).
- `.venv` creado con Python 3.14.3 y todo `requirements.txt` instalado.
- **La red es muy lenta** (~30–120 kB/s). Si pip pasa 2 minutos sin avanzar: cancelar y reintentar una vez con `--no-cache-dir --timeout 60`.
- **pyodbc no carga:** falta el driver ODBC de Microsoft. Requiere aceptar la licencia, así que lo instalo yo:
  ```bash
  brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
  HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18 mssql-tools18
  ```
- Node 24 y npm 11 instalados; `frontend/node_modules` instalado.
- `.claude/launch.json` tiene dos servidores: `backend` (puerto 8000) y `frontend` (puerto 5173). Ahora están detenidos.

---

## 7. Archivos del proyecto

```
botathon-teleton/
├── CONTEXTO.md               Este archivo: todo lo hecho y decidido (se actualiza siempre)
├── CLAUDE.md                 Contexto e instrucciones (arquitectura actualizada al plan de sprints)
├── INICIO.md                 Lista de pasos iniciales (ya cumplida)
├── README.md                 Cómo levantar todo · DESACTUALIZADO (habla de subida manual de Excel)
├── requirements.txt          Dependencias del backend con versiones exactas
├── data/
│   ├── raw/                  Excel originales (solo lectura, no se suben a git)
│   ├── entrada/              Vacía
│   └── generados/            Salidas de las herramientas (no se suben a git)
│       ├── parametros.xlsx
│       └── entradas_planificacion.xlsx
├── docs/
│   ├── desafio.md            Enunciado (con la tabla de ejemplo del resumen)
│   ├── analisis_inicial.md   Problemas de datos, orden del cálculo, casos de prueba, preguntas
│   ├── diccionario_datos.md  ~40 columnas usadas, con tipo verificado celda por celda
│   ├── esquema.sql           Esquema SQLite (28 tablas, probado con sqlite3)
│   └── revision_plan_sprints.md  Revisión del plan de sprints y del tablero
├── herramientas/
│   ├── comun.py              Rutas y lectura de los Excel
│   ├── revisar_tipos.py      Tipo de dato real de cada celda de un Excel
│   └── generar_parametros.py Genera los dos archivos de data/generados/
├── backend/                  Estructura base de FastAPI (ver sección 12)
└── frontend/                 Estructura base de React (ver sección 13)
```

**Fuera del proyecto, en `~/Downloads`:**
- `Nac - Base contratos x mes.xlsx` y `Nac - Planificación Asistencial x mes.xlsx` (originales).
- `ReglasNegocioYRequerimientos.md` y `matriz_casos_prueba_mvp.md` (de Andrés).
- `Plan_Sprints_Botathon_2026_Cada_Hora_Cuenta.docx` (plan de sprints del equipo).
- `revision_diagrama_as_is.md` (mi revisión del diagrama de Dante).

---

## 8. Los datos

**BUK — `Nac - Base contratos x mes.xlsx`, hoja `Dotacion_2026`:**
- Encabezados en la **fila 2**.
- 3.123 filas, 19 columnas, 462 personas, 15 institutos con personal.
- **Solo trae enero a julio de 2026.**
- Una fila por `PersonaId` + `IT` + `Periodo`.

**Planificación — `Nac - Planificación Asistencial x mes.xlsx`:**
- **Hojas:** `Parámetros`, `Calendario 2026`, `Distribucion_NAC`, `Resumen distribucion NAS`, `Planificacion Total`, `LOP`, `Excepciones` y `Dotacion_Asistencial`.
- **`Dotacion_Asistencial`:** encabezados en la **fila 4**, 471 filas (de la 5 a la 475) más la fila de totales, 205 columnas. **No tiene fórmulas**: viene pegada como valores. Por eso la lógica se reconstruyó comparando contra sus valores.
- **`Excepciones`:** 17 filas, 8 profesionales multi-instituto, con horas por instituto y mes.

**Claves:** el profesional es `PersonaId`; el contrato del mes es `PersonaId` + `IT` + `Periodo`.

---

## 9. Lógica de cálculo reconstruida (verificada contra el Excel)

**Qué fuente manda al corregir reglas de negocio** (de mayor a menor):
1. **Enunciado del desafío** (`docs/desafio.md`): define **qué** debe hacer el MVP y qué casos especiales soportar.
2. **Valores del Excel de referencia** (`Dotacion_Asistencial`): definen **cómo** se calcula cada número. La rúbrica exige que «la planificación coincida con el Excel en los casos de prueba», así que en un conflicto numérico manda el Excel. Por ejemplo, el desafío dice «promedio ponderado» y el Excel trunca; la meta mes a mes también se trunca.
3. **Documentos del equipo** (reglas de Andrés, plan de sprints): son interpretaciones y se corrigen cuando contradicen a 1 o 2.
4. **Opiniones externas** (otras IA, sugerencias): no ven el Excel. Cada propuesta se verifica contra los datos antes de cambiar una regla.

Lo que ni el desafío ni el Excel resuelven (FOJA, semanas hábiles de julio a diciembre, qué cuenta en el máximo de asignaciones) se pregunta a los mentores o lo decide el equipo, y se deja escrito.

Columnas de `Dotacion_Asistencial`. «n/N» = filas en que cuadra la fórmula, contando solo las filas con horas > 0 (447 de 471).

| Paso | Qué | Fórmula | Cuadra |
|---|---|---|---|
| 1 | Horas disponibles | `AD = horas semanales − colación (AC)` | 447/447 |
| 2 | Promedio y tramo | `X = TRUNCAR(promedio de las horas de los meses vigentes)`. Tramo: ≥ 40 · 22 a < 40 · < 22 (40 exactas → ≥ 40; 22 exactas → 22–40) | 423/431 |
| 3 | % por cargo y tramo | `% NAS, %Directo, %Indirecto` = `Distribucion_NAC[cargo, tramo]` | 466/471 |
| 3b | Horas NAS base | `AH = %NAS × X` (sobre el **promedio**, no sobre AD) | 447/447 |
| 4 | Se suman las asignaciones al NAS | `AT = (AH + horas de asignaciones) ÷ AD` | 438/447 |
| 5 | Reparto proporcional | `AW = 1 − AT`; `AU %Directo final = AW × %Dir ÷ (%Dir + %Ind)`; `AV = AW × %Ind ÷ (%Dir + %Ind)` | 447/447 |
| 6 | Atenciones por semana | `BA = REDONDEAR.MENOS(AD × AU × 60 ÷ min. directa)`; `BB = REDONDEAR.MENOS(AD × AV × 60 ÷ 30)` | 441 y 444/447 |
| 6b | Atención grupal (AS, ED, UEDA, ULAB, UTAC) | `BF = BA × (1 − %grupal) + BA × %grupal × pacientes` (sin redondeo) | 91/91 |
| 7 | Atenciones del mes | `PlanAteDir_m = REDONDEAR.MENOS(BF_m × SemHab_m)`; total = `REDONDEAR.MENOS((BF_m + BB_m) × SemHab_m)` | ver abajo |
| 8 | Meta del mes | `MG_m = REDONDEAR.MENOS(PlanAteDir_m × 0,9)` | 454/471 |

- **Cambio legal 44 → 42 h:** ya viene aplicado en las horas de BUK (134 personas: 44 h de enero a abril y 42 h desde mayo). Cada período se calcula con sus propias horas: `AD_m` cambia y `AT` se recalcula, pero `AH` se mantiene. Cuadran los 12 meses en 133 de 136; sin cambio de horas, en 282 de 285. Con los % de diciembre solo cuadran 29 de 136.
- **Semanas hábiles por persona (`SemHab`):** en enero y febrero = `semanas del mes − licencias − vacaciones − permisos`. De julio a diciembre hay descuentos adicionales por persona (feriado adicional prorrateado, cumpleaños, vísperas, días progresivos × 0,7…) cuya fórmula **no se pudo reconstruir**. Por ahora se usan los valores del Excel como entrada.
- **Pausa saludable** (10 % del promedio en tramo ≥ 40, 6 % en los otros) y colación de 15 min: son solo el desglose de AH; no cambian el resultado.
- **FOJA:** el Excel no la calcula. Propuesta: horas directas del mes ÷ (horas contratadas × semanas del mes). Pendiente de definir.

---

## 10. Casos de prueba con valores del Excel

**Caso 1 · Normal — PersonaId 134561** (fila 364): kinesiólogo, Santiago, 40 h, sin colación, tramo ≥ 40 (65/10/25), asignaciones 1,25 h. **Junio** (`SemHab` 4,2):
- %NAS final 0,28125; %Directo final 0,622917; %Indirecto final 0,095833.
- 28,75 h disponibles por semana; 37 atenciones directas y 7 indirectas por semana.
- Mes: **155** directas, **184** totales; meta **139 / 165**; FOJA 0,6229.

**Caso 2 · 44 → 42 h — PersonaId 117024** (fila 352): mismo cargo, instituto y asignaciones; promedio TRUNCAR(42,67) = 42; AH = 10,5.

| | Enero (44 h) | Junio (42 h) |
|---|---|---|
| Directas / totales | **172 / 205** | **163 / 197** |
| Meta | **154 / 184** | **146 / 177** |
| FOJA | 0,6352 | 0,6242 |

Mejor ejemplo para notar la diferencia: **71580** (fila 7). En enero el Excel tiene 159; recalculando da 159, y con los % de diciembre daría 155.

**Caso 3 · Multi-instituto — PersonaId 134746** (filas 109 y 110): BUK lo registra con 40 h en Coquimbo; `Excepciones` lo reparte en 34 h Coquimbo + 6 h Copiapó. Cada instituto se calcula por separado. **Junio:**
- Coquimbo: asignaciones 7,25 h; %NAS final 0,413235; directas/totales **100 / 130**; meta **90 / 117**.
- Copiapó: directas/totales **21 / 25**; meta **18 / 22**.

**Otros útiles:**
- **137732** (CP-001 de Andrés): fila 5, Arica, médico fisiatra, 40 h, Líder Equipo 2 h. Enero 151, febrero 36, marzo 149.
- **71269** (CP-003): Arica, médico general, 10 h, término 28-02-2026, promedio 10. Enero 30 atenciones, febrero 0.
- **137356:** jornada partida en dos filas (20 h hasta junio, 30 h desde julio).

---

## 11. Problemas de datos encontrados (25; detalle en `docs/analisis_inicial.md`)

1. **Encabezados fuera de la fila 1:** BUK fila 2, `Dotacion_Asistencial` fila 4, `Excepciones` fila 2, `Distribucion_NAC` filas 5–6.
2. **«O'Higgins» de dos formas:** BUK usa «O´Higgins» (acento agudo) en 33 filas; en el plan hay 4 con acento y 2 con apóstrofo; en `Excepciones`, 2 con apóstrofo. Además «Pmo» y «Valparaiso» sin tilde. Regla: identificar por el código IT, nunca por el nombre.
3. **«Sin pareja» en BUK:** por persona, **0**. Los 6 pares que no cuadran por instituto son multi-instituto.
4. **BUK solo de enero a julio;** 31 personas con menos de 7 meses (altas y bajas); 3 traslados de instituto; 2 cambios de cargo.
5. **Vacíos como texto `''`** (no celda vacía) en ~4.500 celdas, por ejemplo `Fecha Término` en 3.066.
6. **`Centro de Costo` de BUK viene como texto** («300513»).
7. **`Excepciones` con fórmulas rotas** (`#REF!`): Cargo y Ccosto en las 17 celdas, Fec_Ingreso en 15.
8. **41 casos de ajustes manuales** (% o minutos distintos de la tabla) en 9 filas.
9. **Asignaciones:**
   - 41 filas tienen 3 asignaciones con más de 30 h.
   - 401 filas tienen «Asignación 4» = 0,25 h sin nombre.
   - Hay nombres con espacio al final y 5 asignaciones con nombre pero sin horas.
   - **6 asignaciones usan horas distintas a las del catálogo** (por ejemplo, Investigación 5 h contra 2 h).
10. **MEDICO ODONTOLOGO** sin % indirecto (vacío = 0).
11. **Sin errores en:** duplicados de BUK, fechas, horas fuera de rango y catálogos (todos los cargos e institutos de BUK existen).

---

## 12. Lo que existe en código

**Backend (`backend/`, FastAPI + SQLite, validado en pruebas locales; integración real pendiente):**
- `app/config.py` y `app/db.py`: ruta del `.db` en `backend/.env`; SQLite con claves foráneas y modo WAL.
- `app/carga_inicial.py`: al arrancar, crea las tablas (`docs/esquema.sql`) y carga parámetros y entradas desde `data/generados/`.
- `app/schemas.py`: contrato de datos del bot (Pydantic).
- `app/sincronizacion.py`: `POST /api/v1/buk/sync`; valida contratos y reparto por fila, actualiza cargas parciales sin borrar otras personas y publica carga + cálculo en una transacción. `periodos_completos` declara cobertura nacional y permite bajas por ausencia. Un fallo revierte la carga y responde 503; el reintento recalcula. Comprueba identidad del contenido y rechaza conflictos con 409.
- `app/cambios.py`: compara el BUK nuevo con el anterior (solo los meses informados): ALTA, BAJA, MODIFICACION (horas, cargo, tipo de contrato, fecha de término, traslado de instituto), cada una con la fecha desde la que rige.
- `app/motor.py`: motor de 8 pasos; respeta la vigencia de contratos, asignaciones y ajustes mes a mes; no cuenta asignaciones/ajustes rechazados. Sin semanas hábiles excluye el mes y registra RN-15, en vez de publicar cero válido. Conserva la especialidad individual del Excel y la estimación con alerta para profesionales nuevos.
- `app/routers/`: salud, buk, dashboard (kpis, institutos, profesionales, excepciones, parámetros, versiones, cambios).
- `tests/test_api.py` y `tests/test_regresiones.py`: 37 pruebas aprobadas (13 de integración + 24 de regresión), incluidas fallas y reintentos, cargas concurrentes, cobertura completa vacía, vigencias y migración no destructiva. Verificador: 7/7 casos y 96,3 % estricto; persisten 94 meses distintos en 25 filas fuera de las exclusiones actuales.

**Frontend (`frontend/`, React + Vite + Tailwind + Recharts + Lucide):**
- Barra lateral y barra superior con filtros globales y estado de conexión.
- Resumen nacional (KPI, resumen en lenguaje simple, dona directa/indirecta/NAS, barras por instituto), Profesionales, Excepciones, Parámetros (edición con motivo) e Historial (cambios detectados + versiones del cálculo).
- Probado en el navegador en escritorio y celular.

**Herramientas:**
- `generar_parametros.py` crea:
  - **`parametros.xlsx`:** Institutos 18, AliasInstitutos 46, Cargos 86, Distribucion 258, Tramos, Asignaciones 32, FactorGrupal 10, Calendario 12, Feriados 26, JornadaLegal, Parametros.
  - **`entradas_planificacion.xlsx`:** FilasPlanificacion 471, Asignaciones 901, Ausencias 2.209, DiasAdicionales 2.956, SemanasHabiles 5.652, MultiInstituto 177, AjustesManuales 17.
  - Cada hoja tiene encabezados en la fila 1, sin fórmulas, para que el bot la lea como colección.
- **Verificación de los parámetros:** pasan 11 de 12 controles contra lo que usó el Excel (% por tramo 466/471, minutos 467/471, factor grupal 95/95, semanas, feriados, institutos, meta). Falla uno: las 6 asignaciones con horas distintas al catálogo. `entradas_planificacion.xlsx` trae las horas reales.
- **Propuestas mías, no datos del Excel:** `RequiereAutorizacionDMN` («SI» si la descripción menciona DMN), usar las semanas hábiles del Excel como entrada y mantener los ajustes manuales.

---

## 13. Plan de sprints y tablero del equipo

**Sprints:**
- **Sprint 1** (22:50–01:30): cimientos, ingesta y motor de 8 pasos. Casos CP-001, 002, 003 y 014–019.
- **Sprint 2** (01:30–05:00): dashboard, parámetros, multi-instituto y asignaciones. CP-004 a 011 y CP-E10.
- **Sprint 3** (05:00–07:30): cambios entre versiones de BUK, comparativa SIC y verificación ≥ 95 %. CP-012, 013 y 016–020.
- **Cierre** (07:30–09:00): demo de 5 min y pitch de 3 min.

**Mis tarjetas (frontend):**
- **FRONT-1:** setup React + Vite + Tailwind y layout base (navbar Teletón, barra lateral, filtro de instituto y de período). Ya hay setup; faltan la barra lateral, los filtros y Lucide.
- **FRONT-2:** dashboard con tarjetas de indicadores (horas contratadas, horas directas, meta 90 %, FOJA promedio), barras por instituto y dona directa/indirecta/NAS.
- **FRONT-3:** módulo de parámetros editable en vivo (minutos estándar, % de meta).
- **FRONT-4:** comparativa SIC contra lo planificado y feed de auditoría del bot.

**Otras tarjetas:**
- **RPA (Vicente):** RPA-1 lectura de BUK, RPA-2 Web API hacia `/buk/sync`, RPA-3 `Excepciones`, RPA-4 Work Queues y normalización, RPA-5 cambios entre versiones.
- **Backend (Andrés):** BACK-1 modelos + Pydantic, BACK-2 motor de 8 pasos, BACK-3 cambio 44 → 42, BACK-4 endpoints, BACK-5 asignaciones y licencias, BACK-6 auditoría, BACK-7 SIC simulado.

**Lo que detecté en el plan** (detalle en `docs/revision_plan_sprints.md`):
- **Faltan dos tarjetas:**
  - Cargar los datos de planificación que no vienen en BUK. Sin ellos no se llega al 95 %.
  - Crear archivos de prueba para los casos que el kit no cubre: CP-006, 007, 011, 014, 015 y los casos E.
- **Hay tres listas distintas de casos críticos** (plan, tablero y matriz de Andrés).
- **La definición de «terminado» exige Git**, pero `CLAUDE.md` lo prohíbe hasta que el equipo lo autorice.
- **Errores en los documentos de Andrés:**
  - el promedio 44 → 42 es 42,67 (truncado 42), no 42,33;
  - en CP-008 quedan 27 h disponibles, no 37, porque falta descontar el NAS;
  - el reparto entre directa e indirecta debe ser proporcional, y faltaba la colación;
  - en CP-005, Coyhaique tiene 8 h solo de enero a marzo y 6 h desde abril;
  - en CP-003, febrero tiene 0 atenciones.

---

## 14. Diagrama AS-IS (Dante)

El proceso actual tiene carriles: GP (BUK), jefaturas, DMN, Planificación Central y SIC.

**Lo que mejoró en la segunda versión:** inicio en GP, documento BUK, carril SIC, simbología y la regla de no agregar decisiones sin evidencia.

**Lo que falta:**
- Nombres de carriles superpuestos (lo más visible).
- La carga manual de licencias, vacaciones y permisos, y el reparto multi-instituto.
- Una nota de que el consolidado no llega a las jefaturas.
- Etiquetas encima de las líneas.

La revisión completa, con la tabla AS-IS → TO-BE, está en `~/Downloads/revision_diagrama_as_is.md`.

---

## 15. Explicación simple del proyecto (para mí)

**La analogía del restaurante:**

| Pieza | En el restaurante |
|---|---|
| Excel de BUK | El proveedor |
| Blue Prism | El encargado de recepción |
| API | La ventanilla de la cocina |
| JSON | La comanda |
| Backend | La cocina |
| Motor de cálculo | La receta |
| SQL Server | La bodega |
| Frontend | El comedor |

El cliente nunca entra a la cocina: **el frontend solo habla con la API.**

**Un dato de punta a punta:**
1. Fila de BUK de 117024.
2. El bot la valida y la envía por JSON.
3. El backend la guarda.
4. El motor calcula: junio, 163 atenciones, meta 146.
5. React pide `/api/v1/dashboard/kpis?it=131&mes=6`.
6. El backend responde un JSON y React lo dibuja.

**Etapas de un proyecto de software y dónde vamos:**
1. Entender el problema.
2. Analizar los datos (hecho).
3. Diseñar: arquitectura, base de datos, parámetros (hecho).
4. Planificar y dividir: sprints y tablero (hecho).
5. **Construir (aquí empezamos).**
6. Probar contra el Excel.
7. Integrar y presentar.

**Para el frontend:** lo clave es acordar con Andrés el **contrato**, es decir, la forma de los JSON de cada endpoint. Con eso se trabaja con datos de ejemplo sin esperar al backend.

**Conceptos de React:**
- **Componente:** una pieza de la página.
- **Props:** los datos que recibe un componente.
- **Estado (`useState`):** datos que cambian en pantalla.
- **`fetch`:** cómo React pide datos a la API.

**Accesibilidad:** buen contraste, uso solo con teclado y un resumen en lenguaje simple (es criterio del jurado).

---

## 15b. Reglas de negocio corregidas (versión de ChatGPT)

Archivo: `~/Downloads/reglas_negocio_cada_hora_cuenta.md` (28 reglas RN-01 a RN-28, estados, orden de cálculo, controles). Lo generó ChatGPT a pedido del usuario a partir de nuestro análisis.

**Revisión (2026-11-07, ajustes ya aplicados al archivo a las 01:10):** es correcto y coincide con la lógica verificada de la sección 9 (fórmulas de AD, X truncado, NAS base sobre X, asignaciones sumadas al NAS, reparto proporcional, `floor` semanal, grupal sin redondeo, `floor` mensual, meta mes a mes). Corrige los errores de los documentos de Andrés. Puede reemplazarlos con estos ajustes:
1. **Jornada partida:** el Excel separa en dos filas algunos cambios de jornada (137356: 20 h → 30 h; 72190: 32 h → 35 h) y calcula el promedio y el tramo **por tramo de jornada**, no con un solo promedio anual como dice RN-07. Esas personas no cuadrarán si no se replica.
2. **Volumen de alertas:** con RN-11 quedarían 401 filas en ALERTA por la «Asignación 4» de 0,25 h sin nombre y 125 en PENDIENTE por las asignaciones «por autorizar». Conviene decidir si se muestran agrupadas para no saturar el dashboard.
3. **RN-09:** los minutos estándar dependen solo del cargo, no del cargo y el tramo.
4. **RN-25 (SIC):** compara contra la meta total (directa + indirecta), pero SIC probablemente registra solo atenciones directas. Definir contra qué meta se compara cuando se conozca el formato de SIC.
5. **Falta un apartado para QA** con las diferencias conocidas del Excel: 9 filas con ajustes manuales, 9 filas cuyo %NAS final no cuadra, 6 con atenciones semanales que no cuadran y 17 con metas mensuales distintas. Así el 95 % se evalúa sabiendo qué se espera que no cuadre.

## 16. En qué quedamos

- Se autorizó reparar las seis fallas confirmadas en la revisión del backend. Correcciones implementadas y verificadas; el usuario pidió explícitamente crear el commit y subirlas a `main` de GitHub.
- No se modificaron los Excel ni la base de trabajo: las pruebas y la comparación usaron bases temporales.
- Antes de usar la reparación en la demo: reiniciar el backend (migración aditiva automática) y adaptar el envío de Blue Prism a `periodos_completos` si se necesita detectar bajas por ausencia. Esta integración real aún no se probó.

**Decisiones pendientes del equipo:**
1. Dónde corren FastAPI y SQL Server, y si la VM llega a esa máquina por HTTP.
2. Quién toma QA y el pitch.
3. Qué lista de casos críticos manda.
4. Cuándo se autoriza Git.
5. Horas de asignaciones: ¿manda el catálogo o las horas de cada persona?
6. Fórmula de las semanas hábiles de julio a diciembre (¿pedir el Excel con fórmulas a los mentores?).
7. Definición de la FOJA (semanas hábiles o calendario; mensual o anual).
8. Meta: ¿redondeo mes a mes (como el Excel) o 90 % del total anual?
9. Multi-instituto: ¿tramo por instituto (como el Excel) o por persona?
10. Qué es la «Asignación 4» de 0,25 h, y si la asignación «por autorizar» cuenta dentro del máximo de 2.
11. SIC: el kit no trae reporte. ¿Se simula?
12. Si el procesamiento debe ir dentro de Blue Prism (pregunta a los mentores).

**Pendientes menores en el repo:**
- `docs/diccionario_datos.md` todavía dice «Tipo SQL Server».
- `solucion_final_demo_sqlite.md` sugiere enviar en partes de 500 filas con el mismo `ejecucion_id`, pero el backend trata un `ejecucion_id` repetido como reintento (no guarda la segunda parte). Si Vicente necesita partir el envío, hay que soportarlo en el backend.
- Antes de la demo: borrar `data/planificacion.db` (tiene datos de prueba) y levantar el backend sin `--reload`.

---

## 17. Registro de cambios de este archivo

Una línea por actualización, la más reciente al final.

- **2026-11-07 00:15** · Creado con todo lo hecho hasta ese momento (secciones 1 a 16).
- **2026-11-07 00:30** · Movido de `~/Downloads` a la raíz del proyecto como `CONTEXTO.md`. Nueva regla: actualizarlo en cada turno en que se haga algo o llegue información nueva.
- **2026-11-07 00:40** · Sección 9: criterio de qué fuente manda al corregir reglas de negocio (desafío → valores del Excel → documentos del equipo → opiniones externas). Motivo: una IA externa sugirió corregir las reglas de negocio.
- **2026-11-07 00:55** · Nueva sección 15b: revisión de las reglas de negocio corregidas por ChatGPT (correctas; 5 ajustes: jornada partida, volumen de alertas, minutos por cargo, meta para SIC, diferencias conocidas para QA).
- **2026-11-07 01:10** · Sección 15b: los 5 ajustes ya se aplicaron al documento de reglas en Descargas (jornada partida RN-07, minutos por cargo RN-09, agrupación de alertas RN-11, meta para SIC RN-25, pendientes 7 y 8, y nueva sección 15 con las 39 filas de diferencias conocidas para QA).
- **2026-11-07 01:25** · Documento de reglas (Descargas) corregido según `~/Downloads/conclusion_revision_reglas_negocio.md`: atenciones semanales separadas en 6 directas (filas 18, 115, 219, 383, 384, 464) y 3 indirectas (219, 332, 384); medición del 95 % definida (estricta por profesional-instituto-mes con 4 resultados, más diagnóstico por resultado; meta interna, no del desafío); RN-06 con condiciones para proyectar; agrupación de alertas marcada como regla de visualización; nuevo caso CP-JP (137356: marzo 96/114, meta 86/102; septiembre 118/141, meta 106/126).
- **2026-11-07 01:35** · Documento de reglas corregido según `~/Downloads/conclusion_revision_reglas_negocio_v2.md`: la jornada partida sale de las diferencias conocidas (se mide y debe coincidir); quedan 35 filas distintas; exclusiones por PersonaId + IT + mes + resultado; 16 de 17 metas distintas son solo la meta directa de marzo (fila 130 tiene más meses).
- **2026-11-07 01:45** · Documento de reglas (Descargas) limpiado para compartir con el equipo: sin referencias a archivos internos (análisis, docs/, entradas_planificacion), sin menciones a versiones anteriores ni al plan de sprints, y sin la tabla de coincidencias verificadas (esa queda en docs/analisis_inicial.md). Quedan las reglas RN-01 a RN-28, el caso CP-JP y la sección 15 de diferencias conocidas para pruebas.
- **2026-11-07 01:50** · El documento de reglas se renombró a `~/Downloads/reglas_negocio_cada_hora_cuenta.md`.
- **2026-11-07 01:55** · Sección 1: nueva regla para los documentos que se entreguen desde ahora (autocontenidos, solo lo pedido, sin referencias internas, listos para compartir). Los documentos existentes no se reescriben.
- **2026-11-07 02:00** · Sección 1: regla nueva: toda corrección a un archivo de un compañero se entrega también como .md descargable en ~/Downloads, para su autor.
- **2026-11-07 02:10** · Entregado `~/Downloads/pasos_previos_y_revision_matriz.md`. Pasos antes de programar: (1) decidir dónde corren backend y SQL Server y probar la red VM → backend; (2) contrato de datos (JSON de /buk/sync y de los endpoints del dashboard); (3) ajustar esquema: falta columna estado en resultados, tabla de períodos de jornada y vacantes; (4) asignar QA. Revisión de la matriz: responsables desactualizados, arquitectura antigua (todo en Blue Prism, CP-020 como Excel), faltan etapas de red, integración frontend y accesibilidad; propuesta de casos críticos = lista de la matriz + CP-005 + CP-JP.
- **2026-11-07 02:20** · Entregado `~/Downloads/correccion_flujo_general.md`: corrección del flujo general (sección 9.1) del documento de requerimientos de Andrés. Flujo de 37 pasos repartido en Blue Prism (1–12), backend (13–32) y dashboard (33–37), con pasos nuevos (Excepciones, envío a la API, NAS base, multi-instituto, proyección, comparación SIC, estados, auditoría) y ajuste de la sección 9.2 (BO_Calculos y BO_Reportes salen de Blue Prism; entran BO_Cambios y BO_API).
- **2026-11-07 02:35** · `~/Downloads/correccion_flujo_general.md` reescrito según `~/Downloads/conclusion_revision_flujo_general.md`: 43 pasos (Blue Prism 1–16, backend 17–38, dashboard 39–43). Decisiones: SQL Server es la fuente oficial de la versión anterior de BUK (Blue Prism la pide con GET /api/v1/buk/ultima-version y conserva la detección de cambios); endpoints separados buk/sync, auditoria/deltas y sic/sync con ejecucion_id compartido; validación definitiva en el backend; reintentos con Work Queue e idempotencia por hash/ejecucion_id; estados en dos momentos; minimización de datos en Blue Prism; paso 22 carga parámetros y entradas de planificación.
- **2026-11-07 02:45** · El flujo corregido en Descargas fue reforzado por otra persona/IA (claves de envío, cobertura, carga_id, sección 6 de cierre y recálculo, estados separados en calidad/origen/indicador). Revisión entregada en `~/Downloads/revision_flujo_general_v3.md`: sólido; 5 ajustes: quitar rutas internas del paso 22, cargar parámetros antes de validar (19/22), llevar los 3 campos de estado a las reglas (sección 11) y a la base, rechazos a revisión manual en Work Queue, y separar mínimo para la demo / sprint 3 / fase 2.
- **2026-11-07 02:55** · Info nueva: Andrés corre el backend en local y Vicente usa Blue Prism en la VM; dicen estar en la misma red. Entregada `~/Downloads/guia_conexion_blueprism_backend.md`: uvicorn con --host 0.0.0.0, firewall, prueba desde la VM (Test-NetConnection / /api/salud), riesgos (VM remota en otra red, aislamiento de clientes en la Wi-Fi, proxy), cómo llamar desde Blue Prism (Web API Services recomendado, Utility - HTTP, Code Stage; Utility - JSON para la colección), URL como variable de entorno, plan B (hotspot, túnel ngrok/Cloudflare, nube). Pendiente: resultado de la prueba de red.
- **2026-11-07 03:05** · Los expertos de Blue Prism sugirieron exportar el proceso desde la VM e importarlo en un Blue Prism local (misma red que el backend o el mismo computador). Agregada la sección 7 a `~/Downloads/guia_conexion_blueprism_backend.md`: File → Export o Release Manager (.bprelease), qué no viaja (variables de entorno, Work Queues, credenciales), requisitos (Windows, licencia, misma versión, Excel, VBO auxiliares) y preguntas para los expertos. Mejor variante: Blue Prism y backend en el mismo computador Windows (localhost).
- **2026-11-07 03:15** · Decisión del equipo: la base de datos es **SQLite** (reemplaza a SQL Server). Actualizados la sección 4 de este archivo y la arquitectura de CLAUDE.md. Pendiente adaptar esquema, backend (config/db), requirements, diccionario y documentos compartidos.
- **2026-11-07 03:25** · `docs/esquema.sql` reescrito para SQLite y probado con sqlite3 (28 tablas; las restricciones rechazan % que no suman 1, períodos que no son día 1, claves foráneas inválidas, envíos repetidos y feriados duplicados). Agrega: tres estados en resultados (estado_calidad, origen_dato, estado_foja) y estado_calidad + motivo en contratos; tablas nuevas periodos_jornada, vacantes, reparto_multi_instituto y semanas_habiles; cargas con ejecucion_id + fuente únicos, cobertura, versión de referencia y estado; versiones_calculo con estado (EN_PROCESO/PUBLICADA/FALLIDA); errores_validacion con campo, valor y detectado_por. Recordatorio: el backend debe ejecutar PRAGMA foreign_keys = ON en cada conexión.
- **2026-11-07 03:40** · Roles: Vicente tiene la VM con Blue Prism; **el backend, la base de datos y el frontend corren en el computador de Gladys**. La prueba de red es VM → computador de Gladys. Guía de conexión en Descargas corregida (Andrés → Gladys). Opinión sobre la base: SQLite para la demo; Supabase solo si la VM no llega al computador de Gladys pero sí a internet; PostgreSQL administrado como camino a producción.
- **2026-11-07 03:50** · Entregado `~/Downloads/solucion_final_demo_sqlite.md`: arquitectura final (Blue Prism en la VM de Vicente → HTTP puerto 8000 → FastAPI + SQLite + React en el computador de Gladys), quién hace qué, prueba de red y plan B en orden (hotspot, túnel, exportar proceso a BP local, Supabase), SQLite (PRAGMA foreign_keys y WAL, carga inicial, respaldo), contrato de datos con endpoints de demo y de sprint 3 y ejemplos JSON, orden del motor, 7 casos con valores esperados, cronograma 03:45–09:00, guion de demo, checklist y escalamiento a PostgreSQL.
- **2026-11-07 03:55** · Estado: Vicente está avanzando con Blue Prism. El usuario no sabe qué sigue; se le propuso: confirmar la prueba de red, acordar con Andrés el contrato de los endpoints del dashboard y empezar FRONT-1 con datos de ejemplo. Simulación ofrecida: A (bot), B (cálculo vs. Excel, recomendada) o C (todo), sin respuesta aún.
- **2026-11-07 04:50** · **Backend completo en SQLite** (a pedido del usuario; base para Andrés): se quitó pyodbc; `config.py` y `db.py` usan SQLite (PRAGMA foreign_keys y WAL en cada conexión; crea la base desde `docs/esquema.sql`); `carga_inicial.py` carga parámetros y entradas al arrancar; `sincronizacion.py` + `POST /api/v1/buk/sync` (validación por fila, idempotente por ejecucion_id, reemplaza contratos de los períodos informados, recalcula); `motor.py` (RN-05 a RN-18); endpoints `GET /api/v1/buk/ultima-version`, `/dashboard/kpis`, `/dashboard/institutos`, `/profesionales`, `/excepciones`, `/parametros` (GET y PUT con recálculo y registro en cambios), `/versiones`. Se eliminó `POST /api/cargas` (subida manual). Esquema: periodos_jornada ahora guarda cada fila de la planificación (cargo, cod_esp, colación). Herramientas nuevas: `simular_bot.py` (hace lo que hará Blue Prism) y `verificar_motor.py`. Resultado: 7/7 casos coinciden; coincidencia estricta 96,3 % (98,2 % sin diferencias conocidas); 94 meses en 25 filas por revisar. 12/12 pruebas pasan. Prueba real con el servidor: 3.123 filas en ~9 s. Pendiente: el frontend aún llama a `/api/cargas` (ya no existe) y no usa los endpoints nuevos.
- **2026-11-07 05:05** · Verificación del backend a pedido del usuario: 12/12 pruebas, 7/7 casos, coincidencia estricta 96,3 % (98,2 % sin conocidas). Las 94 diferencias no explicadas (25 filas) son del Excel, no del motor: (a) ~18 filas con cambio de jornada a mitad de año en una sola fila (Aumento/Disminución), donde el Excel no usa las horas mensuales de BUK en ene–abr; (b) 125129, con reparto en Excepciones que la planificación ignora; (c) multi-instituto 115444 y 129024, donde el Excel usa las horas de abr–dic todo el año; (d) anomalías puntuales (72251 enero, 71575, 109828 en Santiago). El motor sigue la regla del desafío (horas por mes según vigencia). Ajuste en motor: en el reparto multi-instituto, un mes con 0 horas no cuenta para el promedio. Frontend conectado a los endpoints nuevos (compila), sin probar en el navegador: en pausa.
- **2026-11-07 05:25** · **Frontend conectado y probado en el navegador** con el backend real y el bot simulado. Secciones: Resumen nacional (KPI, resumen en lenguaje simple, gráfico por instituto con tabla accesible), Profesionales (tabla con buscador; requiere elegir instituto o mes), Excepciones (alertas agrupadas por motivo y filas rechazadas), Parámetros (edición con motivo y nombre obligatorios, recalcula) e Historial de versiones. Filtros globales de instituto y mes. Se eliminó la página CargaExcel. Verificado: totales anuales cuadran con el Excel (772.301 vs. 772.356 atenciones; 692.649 vs. 692.706 de meta); 117024 en junio muestra 26,2 h directas, 197 atenciones, meta 177 y FOJA 62,4 %; cambiar META_PCT a 0,85 recalcula (meta de Santiago en junio 19.850 → 18.745) y queda en el historial; se restauró 0,9. Correcciones: excepciones agrupadas por motivo (antes mezclaba estados), sin filtro de mes en Excepciones, gráfico con los 15 institutos y botones Editar con nombre accesible. Pendiente: Lucide sin instalar; barra lateral del tablero no hecha (se usa barra de pestañas).
- **2026-11-07 05:40** · Frontend: instalado `lucide-react` (queda en package.json); íconos en el menú, las tarjetas de indicadores y el indicador de conexión (aria-hidden, siempre junto a texto). FRONT-1 completo: barra lateral de navegación a la izquierda (en celular queda como fila deslizable arriba) y barra superior con título, filtros globales de instituto y mes, y estado de conexión (fija solo en pantallas grandes). Probado en escritorio (1280 px) y celular (375 px), sin errores en la consola.
- **2026-11-07 05:50** · Gráfico de dona (FRONT-2): distribución de las horas disponibles en atención directa, indirecta y NAS, con leyenda en texto (%, horas) y tabla accesible. El endpoint /dashboard/kpis ahora entrega también horas_indirectas_mes y horas_nas_mes. Nacional 2026: directa 56,9 % (400.978 h), indirecta 11,6 % (81.952 h), NAS 31,4 % (221.325 h). Se desactivó la animación de los gráficos (se dibujan aunque el navegador esté en segundo plano y respeta a quienes prefieren menos movimiento). 12/12 pruebas pasan.
- **2026-11-07 08:30** · **Detección de cambios en el backend** (según el stack: FastAPI hace reglas, cálculos y detección de cambios; se mantiene SQLite, no se vuelve a SQL Server). Nuevo `backend/app/cambios.py`: al llegar un BUK se compara con la carga anterior y se registran altas, bajas y modificaciones (horas, cargo, tipo de contrato, fecha de término, traslado) en la tabla `cambios`, con la fecha desde la que rigen; la respuesta de `/buk/sync` trae el resumen. Nuevo `GET /api/v1/cambios`. Motor: usa el cargo de BUK de cada mes y planifica profesionales nuevos. Simulador: `simular_bot.py --cambios`. Frontend: Historial muestra los cambios detectados con filtro por tipo. Probado: 13/13 pruebas; en el navegador aparecen 1 alta, 1 baja y 2 modificaciones. Actualizadas las secciones 12 y 16 y el README. Blue Prism ya no necesita comparar versiones: solo envía el BUK.
- **2026-11-07 08:45** · Documentos compartidos (en Descargas) actualizados a la detección de cambios en el backend: `correccion_flujo_general.md` (Blue Prism solo envía BUK y Excepciones; la API compara con la carga anterior antes de calcular; «SQL Server» → «SQLite»), `solucion_final_demo_sqlite.md` (Blue Prism no compara versiones; nuevo `GET /api/v1/cambios`; se quitó `POST /auditoria/deltas`; cronograma y guion de la demo con los cambios) y `guia_conexion_blueprism_backend.md` (sin mención a SQL Server). Detectado: el envío en partes con el mismo `ejecucion_id` no funciona con el backend actual.
- **2026-11-07 08:50** · `frontend/index.html` estaba dañado (quedaban 44 caracteres, con «]]]]]]]]]]]]» en vez del `<head>` y el `<body>`) y el sitio se veía en blanco. Se restauró el contenido original; el sitio vuelve a cargar sin errores. No se encontraron otros archivos dañados.
- **2026-11-07 09:00** · **Proyecto subido a GitHub** (autorizado por el equipo): repositorio público https://github.com/matiberoiza/Botathon2026, rama `main`. Se creó `.gitignore` (excluye data/raw, data/entrada, data/generados, la base `.db`, `.env`, `.venv`, `node_modules`, `dist`, cachés y `.DS_Store`). Se suben 53 archivos con código, documentos, CONTEXTO.md e INICIO.md (decisión del usuario, aunque el repo es público). El repo ya tenía un commit inicial con un README de una línea; se unió conservando el README del proyecto.
- **2026-11-07 09:15** · **Diseño con colores Teletón** en el frontend: paleta roja propia en `index.css` (`teleton-50` a `teleton-900`, rojo de marca #e2001a), franja roja arriba de la barra superior, corazón blanco sobre círculo rojo junto al título (no se usa el logo oficial, que es marca registrada), menú activo, botones, enlaces, íconos y gráficos en rojo; en la dona, directa en rojo, indirecta en azul marino y NAS en gris. El azul queda solo en las insignias «Pendiente» y «Modificación» (información). Contraste AA verificado (rojo 700 sobre blanco 6,9:1; botón blanco sobre rojo 6,9:1). Probado en escritorio y celular, sin errores. Subido a GitHub (commit 8d7ad91).
- **2026-11-07 09:30** · **Logos del evento en el sitio**, a pedido del usuario: se recortaron de la imagen del banner de la Botathon que envió (Duoc UC con su Escuela de Informática y Telecomunicaciones, Teletón y SS&C Blue Prism), con fondo transparente, en `frontend/src/assets/logos/` (blancos y uno de la Teletón en rojo). Franja roja arriba con «Botathon 2026 · Desafío Teletón» y los tres logos (con texto alternativo); el logo rojo de la Teletón reemplaza al corazón junto al título (decorativo, se oculta en celular porque ya está en la franja). Probado en escritorio y celular, sin errores.
- **2026-11-07 09:40** · Menú de secciones siempre lateral (antes, bajo 768 px pasaba a una fila horizontal arriba). En pantallas angostas muestra solo los íconos (el nombre queda para lectores de pantalla y como tooltip); desde 768 px, ícono y texto. Probado a 375, 609 y 1280 px, sin errores.
- **2026-11-07 09:45** · Etiqueta flotante con el nombre de cada sección al pasar el cursor sobre su ícono en la barra lateral angosta (también aparece al llegar con el teclado; se reemplazó el tooltip nativo, que tardaba). Con la barra ancha no aparece, porque el texto ya se ve. Ambos cambios subidos a GitHub.
- **2026-11-07 10:00** · Revisión externa (ChatGPT, sobre el commit 1dd566b) encontró 6 problemas en el backend; los 6 se confirmaron en el código, aunque ninguno ocurre con los datos del kit: (1) una carga parcial borra los demás contratos del mes y genera bajas falsas; (2) se planifican meses después de la fecha de término si BUK trae la fila; (3) las asignaciones se aplican a todo el período aunque empiecen después, y las rechazadas se siguen contando; (4) semanas hábiles faltantes se tratan como 0 VALIDO; (5) un reintento tras un cálculo fallido responde ACEPTADA sin recalcular; (6) un instituto inexistente en el reparto multi-instituto produce error 500. **ChatGPT está haciendo las correcciones**; no tocar `sincronizacion.py` ni `motor.py` en paralelo. Al recibirlas: correr las pruebas, `verificar_motor.py` (7/7 y 96,3 %) y la demo de cambios.
- **2026-11-07 · Reparación posterior a la revisión** · Corregidas las seis fallas en el proyecto local: cargas parciales seguras y cobertura nacional explícita; vigencias mensuales; exclusión de asignaciones/ajustes rechazados; semanas hábiles faltantes visibles como error; carga y publicación atómicas con reintento y detección de contenido incompatible; reparto inválido aislado por fila. Migración aditiva para `hash_payload` y `periodos_completos`, simulador y README actualizados. Verificado: 37/37 pruebas, incluidos envíos concurrentes y fallo forzado seguido de recuperación; 7/7 ejemplos del Excel, 96,3 % estricto y 98,2 % con las exclusiones del verificador. Se mantienen las 94 diferencias no clasificadas por ese verificador (25 filas); no se atribuyen automáticamente al Excel. Sin cambios en los Excel o base real, sin commit/push y sin reiniciar el servidor de trabajo. Pendiente integración real del bot con la cobertura explícita.
- **2026-11-07 · Publicación autorizada** · El usuario pidió «súbelo»: se autoriza el commit y el push de la reparación, las pruebas y la documentación a `main` de `matiberoiza/Botathon2026`. La publicación excluye Excel, bases de datos, configuración local y dependencias. No implica desplegar ni reiniciar el backend; la integración real con Blue Prism sigue pendiente.
- **2026-11-07 10:30** · Revisión del commit 53664d7 (correcciones de ChatGPT) en este computador: 37/37 pruebas; `verificar_motor.py` 7/7 casos, 96,3 % estricto y 98,2 % sin diferencias conocidas; demo `--cambios` en un backend temporal (puerto 8010) detecta 1 alta, 1 baja y 2 modificaciones, y el cambio inverso al reenviar el original. La base de trabajo ya tiene las columnas nuevas. **Avisar a Vicente:** sin `periodos_completos` en el JSON la carga es parcial y no detecta bajas; reutilizar un `ejecucion_id` con otro contenido responde 409. Cambio menor: un ajuste manual sin autorizar ahora deja el mes PENDIENTE (antes ALERTA).
- **2026-11-07 10:40** · Aviso para Vicente en `~/Downloads/aviso_vicente_cambios_envio_bot.md`: agregar `periodos_completos` al JSON (sin él no se detectan bajas), un `ejecucion_id` distinto por envío, y cómo manejar las respuestas 200/400/409/422/503.

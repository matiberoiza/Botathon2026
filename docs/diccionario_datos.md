# Diccionario de datos

Solo las columnas que usa el cálculo (o que sirven para validar la carga). Las columnas mes a mes se describen como patrón. Tablas de destino: ver `docs/esquema.sql`.

**Cómo se verificaron los tipos:** con `herramientas/revisar_tipos.py`, que lee **cada celda** de cada columna con openpyxl (valores, `data_only=True`) y cuenta el tipo real. Para repetir la revisión: `python herramientas/revisar_tipos.py` (kit completo) o `python herramientas/revisar_tipos.py "ruta del Excel" --hoja Dotacion_2026 --csv tipos.csv` (un reporte nuevo). La columna «Tipo en el Excel» dice lo que hay de verdad en el archivo, con cantidades; «Tipo SQL Server» es cómo se guarda en la base (ver `docs/esquema.sql`).

Vocabulario: **entero** (número sin decimales), **decimal** (número que puede tener decimales), **texto**, **fecha**, **duración** (horas guardadas como tiempo de Excel), **fracción** (porcentaje guardado como decimal entre 0 y 1: 0,65 = 65 %).

Archivos de origen (en `data/raw/`, solo lectura):

- **BUK** = `Nac - Base contratos x mes.xlsx`, hoja `Dotacion_2026`. Encabezados en la **fila 2** (la fila 1 está vacía). 3.123 filas de datos (filas 3 a 3.125), 19 columnas, una fila por profesional, instituto y mes. **Solo trae enero a julio de 2026.**
- **PLAN** = `Nac - Planificación Asistencial x mes.xlsx` (el Excel actual, referencia de la lógica).

## Reglas de lectura que salen de la revisión de tipos

1. **Los vacíos vienen de dos formas:** celda vacía y **texto vacío** (`''`). Por ejemplo, `Fecha Término` tiene 3.066 textos vacíos y 0 celdas vacías. El cargador debe tratar ambos como NULL.
2. **Los porcentajes vienen como fracción** (0,65), con formato `0%` en Excel. Se guardan como fracción, nunca como 65.
3. **`Centro de Costo` de BUK es texto** («300513»), no número; en el Excel de planificación la misma información es entero. Se convierte a entero (los 3.123 valores son 6 dígitos).
4. **`H/Sem Disp.Ate` (AX) es una duración** con formato `[h]:mm`: openpyxl la entrega como `timedelta` (30 h aparece como «1 day, 6:00:00»). Horas = segundos ÷ 3.600.
5. **Hay nombres de asignación con un espacio al final** («Investigación », «Desarrollo técnico »): quitar espacios antes de cruzar con el catálogo.
6. Los encabezados de mes de `Excepciones` (`01-01-2026`…) son **texto** en formato DD-MM-AAAA, no fechas.

## Hojas del Excel de planificación

| Hoja | Encabezados | Contenido útil | Uso en el MVP |
|---|---|---|---|
| `Parámetros` | fila 1–2, varias subtablas | calendario, factor grupal, institutos, cargos SIC, especialidades | catálogos |
| `Calendario 2026` | fila 2 | calendario visual | no se usa |
| `Distribucion_NAC` | filas 5–6 (doble encabezado) | % por cargo y tramo (filas 7–92), asignaciones (R:T), cargos de pabellón (filas 97–102) | catálogos |
| `Resumen distribucion NAS`, `Planificacion Total`, `LOP` | — | consolidados con fórmulas | referencia para el dashboard |
| `Excepciones` | fila 2 (tabla `Excepcion`, A2:X19) | 17 filas: horas por instituto y mes de 8 profesionales multi-instituto | `contratos_mes` (origen EXCEPCION) |
| `Dotacion_Asistencial` | **fila 4** (tabla `Dot_Asistencial`, A4:GW476) | 471 filas (5 a 475) + fila de totales, 205 columnas | datos de entrada que no vienen de BUK + valores esperados para los tests |

> `Dotacion_Asistencial` no tiene fórmulas: las celdas y la definición de la tabla vienen como valores. La lógica se reconstruyó a partir de los valores (ver `docs/analisis_inicial.md`).

## Columnas de BUK (`Dotacion_2026`, 3.123 filas)

| # | Columna exacta | Tipo en el Excel (verificado) | Tipo SQL Server | Para qué se usa | Destino |
|---|---|---|---|---|---|
| 1 | `PersonaId` | entero (3.123) | INT | Clave del profesional | `profesionales.persona_id`, `contratos_mes.persona_id` |
| 2 | `IT` | entero (3.123) | INT | Código del instituto del contrato | `contratos_mes.it` |
| 3 | `Periodo` | fecha (3.123), siempre día 1, formato `mmm-yy` | DATE (día 1) | Mes del contrato. Clave del contrato: `PersonaId` + `IT` + `Periodo` | `contratos_mes.periodo` |
| 4 | `Horas Semanales` | decimal: 3.120 enteros + 3 con decimales (7,5) | DECIMAL(5,2) | Horas contratadas del mes; su promedio anual define el tramo | `contratos_mes.horas_semanales` |
| 5 | `Cargo` | texto (3.123), sin espacios sobrantes | NVARCHAR(150) | Cruce con `Distribucion_NAC` | `contratos_mes.cargo` |
| 6 | `Cod_Esp` | texto (3.123): FI, KI, AS, UTAC… | NVARCHAR(10) | Especialidad o área: filtro y factor grupal | `contratos_mes.cod_esp` |
| 7 | `Centro de Costo` | **texto** de 6 dígitos (3.123) | INT (convertido) | Filtro y trazabilidad | `contratos_mes.centro_costo` |
| 8 | `Tipo de Contrato` | texto: «Indefinido» (3.048), «Plazo fijo» (75) | NVARCHAR(20) | Plazo fijo: vigencia limitada | `contratos_mes.tipo_contrato` |
| 9 | `Tipo_Trabajador` | texto: «Titular» (3.121), «Reemplazo» (2) | NVARCHAR(20) | Reemplazos | `contratos_mes.tipo_trabajador` |
| 10 | `Fecha Ingreso Compañía` | fecha (3.123) | DATE | Prorrateo del mes de ingreso; altas | `contratos_mes.fecha_ingreso` |
| 11 | `Fecha Término` | fecha (57) o **texto vacío** (3.066) | DATE o NULL | Prorrateo del mes de término; bajas | `contratos_mes.fecha_termino` |
| 12 | `Ndias` | entero (3.123), de 1 a 6 | TINYINT | Días por semana del contrato | `contratos_mes.dias_semana` |
| 13 | `Fecha de Nacimiento` | fecha (3.123) | TINYINT 1–12 (**solo el mes**) | Día libre de cumpleaños. Se descartan día y año | `profesionales.mes_nacimiento` |
| 14 | `Instituto` | texto (3.123): Ari, San… | no se guarda | Validación contra `institutos.abreviatura` | — |
| 15 | `Área` | texto (3.123): nombre del instituto | no se guarda | Validación (aquí aparece «O´Higgins») | — |
| 16 | `Días de la Jornada` | texto (3.123): letras `l m w j v` | no se guarda | Validación contra `Ndias` | — |

No se usan: `Nombre Sub-área` (texto), `Tipo_Trab_161225` (texto; 63 textos vacíos), `Reg_SIC` (texto, siempre «D - SIC»).

## Columnas de `Dotacion_Asistencial` (471 filas): datos que no trae BUK

| # | Columna exacta (letra) | Tipo en el Excel (verificado) | Tipo SQL Server | Para qué se usa | Destino |
|---|---|---|---|---|---|
| 17 | `Horas Colación en Contrato` (AC) | decimal: 446 enteros + 25 con decimales (2,5) | DECIMAL(5,2) | Horas disponibles = horas semanales − colación | `contratos_mes.horas_colacion` |
| 18 | `Asignación 1` (AL) / `Hrs. Asignación 1` (AM) | AL: texto (256) o vacía (215). AM: decimal (256: 201 enteros + 55 con decimales); vacíos: 202 texto vacío + 13 celdas vacías | NVARCHAR(150) / DECIMAL(5,2) | Asignación especial que se suma al NAS | `asignaciones_profesional` |
| 19 | `Asignación 2` (AN) / `Hrs. Asignación 2` (AO) | AN: texto (119). AO: decimal (118); vacíos: 341 texto vacío + 12 celdas vacías. **1 fila con nombre sin horas** | NVARCHAR(150) / DECIMAL(5,2) | Ídem | `asignaciones_profesional` |
| 20 | `Por Autorizar DMN y VP` (AP) / `Hrs. Asignación 3` (AQ) | AP: texto (119). AQ: decimal (121); vacíos: celda vacía (350). 4 filas con nombre sin horas, 6 con horas sin nombre | NVARCHAR(150) / DECIMAL(5,2) | Asignación que requiere autorización de DMN | `asignaciones_profesional` (estado) |
| 21 | `Hrs. Asignación 4` (AR) | decimal (471): 0,25 (401) o 0 (70); sin nombre | DECIMAL(5,2) | Pregunta abierta: ¿qué asignación es? | `asignaciones_profesional` |
| 22 | `Cambio %Ate. Grupal V°B° DMN y VP` (BD) | vacía en las 471 filas (se espera fracción) | DECIMAL(12,6) | Reemplaza el % grupal estándar | `ajustes_parametro` |
| 23 | `Licencia Extensa` (S) | texto: «Si» (55) o texto vacío (416) | se deriva | Marca de licencia larga | se deriva de `ausencias_mes` |
| 24 | `Vacante/Nuevo` (E) | vacía en las 471 filas (se espera texto) | BIT | Cupos sin persona | `contratos_mes.es_vacante` |
| 25 | `Periodo Inicio Jornada` / `Perido Fin Jornada` (T, U) | fecha (471 cada una) | no se guarda | El Excel parte en dos filas a quien cambia de jornada a mitad de año; en el MVP se calcula mes a mes | — |

**Patrón: ausencias mes a mes** (36 columnas). `Lic1`…`Lic12` (BV:CG), `Vac1`…`Vac12` (CH:CS), `Perm1`…`Perm12` (CT:DE). Tipo: **decimal** en **semanas** (por ejemplo, `Perm3` tiene 203 valores con decimales, como 0,25); sin vacíos (los meses sin ausencia traen 0). `Vac2` = 3 en casi todos por el feriado colectivo de febrero. Destino: `ausencias_mes(persona_id, it, periodo, tipo, semanas)`, DECIMAL(8,4).

**Patrón: días adicionales del año** (DF:DW, unas 18 columnas). Tipo: **decimal** en **días** (por ejemplo, `Visperas Fiestas Patrias` = 0,5), salvo `Mes cumpleaños` (DH), que es **entero** 1–12. `Ajuste por diferencia en días contrato` (DV) está vacía en 468 filas. Columnas: `Mes cumpleaños`, `Días de cumpleaños`, `Visperas Fiestas Patrias`, `Visperas Navidad y Año Nuevo`, `Feriado legal adicional`, `Días administrativos…`, `Plan anual capacitación…`, `HEXA - CTR`, `Jornada nacional`, `Días Progresivos` (factor 0,7), `Días Complementario` (factor 0,8), `Ley 21530` (factor 1), `Vacaciones Legales Pendientes…` (factor 1), `Jornadas Directiva Sindical`, `Lactancia`, `Feriado legal zona extrema ene/feb`. Los factores están en la fila 2 de la hoja. Destino: `dias_adicionales(persona_id, it, anio, tipo, dias)`, DECIMAL(6,2).

**Patrón: valores de referencia (solo tests, no se cargan).**

| Columnas | Tipo en el Excel (verificado) |
|---|---|
| `% NAS`, `%Directo`, `%Indirecto` (AI:AK) | fracción (471), formato `0%` |
| `%NAS + Asig. Especiales`, `%Directo Final`, `%Indirecto Final`, `% Asistencial` (AT:AW) | fracción (456) + 15 textos vacíos (filas sin horas), formato `0.0%` |
| `H/Sem Disp.Ate` (AX) | **duración** (471), formato `[h]:mm` |
| `H/S dic` (W), `Prom_Pond Horas Semanales` (X), minutos estándar (AY, AZ) | entero (471) |
| `H/Sem NAS Total` (AH) | decimal (471) |
| `N° Ate Directas…` (BA), `N° Ate Indirectas…` (BB), `Atención Semanal Indirecta Total` (BG) | entero (471) |
| `Atención Semanal Directa + Grupal` (BF) | decimal: 385 enteros + 86 con decimales (atención grupal) |
| `% Atención Grupal Estándar` (BC), `N° Pacientes por Grupo` (BE) | fracción / decimal (95) + 376 textos vacíos |
| `SemHab1..12` (DZ:EK) | decimal (semanas) |
| `PlanAteDir1..12`, `PlanAteDir+Ind1..12`, `MG_AteDir1..12`, `MG_AteDir+Ind1..12` | entero (471 cada una) |

## Columnas de `Parámetros`

| # | Columna o rango exacto | Tipo en el Excel (verificado) | Tipo SQL Server | Para qué se usa | Destino |
|---|---|---|---|---|---|
| 26 | Factor grupal (F3:I8): `Cod_Esp`, `%`, `N° Pacientes` (San - Con), `N° Pacientes` (Otros IT) | texto (5); fracción (5); entero (5: 3 o 6); decimal (5: 1,5 o 3) | NVARCHAR(10), DECIMAL(9,6), DECIMAL(5,2), DECIMAL(5,2) | % grupal y pacientes por grupo en AS, ED, UEDA, ULAB, UTAC | `factor_grupal` |
| 27 | `Inhábiles 2026` (K2:L138) | K: fecha (129) + 8 vacías; L: texto (137) | DATE, NVARCHAR(150) | Fines de semana, feriados y feriado colectivo de febrero | `feriados` |
| 28 | `Semana` (AD3:AD14) = `ROUND(DiaHabil/5,1)` | decimal (12): 4,2; 4,0; 4,4… | DECIMAL(5,2) | Semanas de planificación por mes | `calendario_mes.semanas` |
| 29 | `Feriado Arica` (S28) | fecha | DATE | Feriado regional | `feriados` (con `it`) |
| 30 | Vacaciones `Staff` / `Coyhaique` (AF26:AG26) | entero: 5 / 10 | DECIMAL(5,2) | Días adicionales de vacaciones | `institutos.dias_vacaciones_adicionales` |
| 31 | `Jornada Nacional` por área (AB35:AC40) | texto / decimal (1,5; 0,5; 1) | DECIMAL(12,6) | Días de jornada nacional por área | `parametros` |
| 32 | Tabla `Institutos` (AM:AO): `IT`, `Inst`, `Area` | entero (25); texto (25); texto (25) | INT, NVARCHAR(10), NVARCHAR(100) | Catálogo de institutos (25 filas para 18 códigos: hay variantes «(G)») | `institutos` |
| 33 | Tabla `Cargo_SIC` (AR:AU): `Cargo`, `Tipo_Trabajador`, `Reg_SIC`, `Cod_Esp` | texto (69; `Tipo_Trabajador` con 5 vacías; `Reg_SIC`: «D - SIC» 60, «F - SIC» 9) | NVARCHAR | Cargo → especialidad | `cargos.cod_esp` |
| 34 | Tabla `Especialidades` (AX:AY): `Cod_Esp`, `Especialidad` | texto (24) | NVARCHAR | Nombres para el dashboard | `especialidades` |

## Columnas de `Distribucion_NAC` (filas 7 a 92: 86 cargos)

| # | Columna exacta | Tipo en el Excel (verificado) | Tipo SQL Server | Para qué se usa | Destino |
|---|---|---|---|---|---|
| 35 | `Cargo` (B) | texto (86), sin espacios sobrantes; coincide con los cargos de BUK | NVARCHAR(150) | Clave del cargo | `cargos.cargo` |
| 36 | `Unidad` (C) | texto (86) | NVARCHAR(100) | Agrupación por área | `cargos.unidad` |
| 37 | `STD Minutos Atención` `Directa` / `Indirecta` (D, E) | entero (86): directa 30/40/45/60; indirecta 30 | SMALLINT | Minutos por atención | `cargos.min_directa`, `cargos.min_indirecta` |
| 38 | `% Dir` / `% Ind` / `% NAS` × 3 tramos (F:H «>=40», I:K «40 <= 22», L:N «< 22») | fracción, formato `0%`. **«MEDICO ODONTOLOGO» no tiene `% Ind` en ningún tramo (celda vacía): tratar como 0** | DECIMAL(9,6) | Distribución por cargo y tramo | `distribucion_cargo` |
| 39 | Asignaciones: `Tipo` (R), `Horas` (S), `Descripcion` (T) | R: texto (33; 3 con espacio al final). S: decimal, **solo 18 de 33 tienen horas** (el resto se define por persona). T: texto (33) | NVARCHAR(150), DECIMAL(5,2) o NULL, NVARCHAR(300) | Catálogo de asignaciones especiales | `asignaciones_catalogo` |

La columna A (`Esp`) de esta hoja no es confiable (por ejemplo, «DIRECTOR INSTITUTO KI» tiene «FO»): la especialidad se toma de `Cargo_SIC`. Los cargos de pabellón (filas 97–102) no aparecen en BUK y quedan fuera del MVP.

## Columnas de `Excepciones` (17 filas)

| # | Columna exacta | Tipo en el Excel (verificado) | Tipo SQL Server | Para qué se usa | Destino |
|---|---|---|---|---|---|
| 40 | `PersonaId`, `IT`, `01-01-2026` … `01-12-2026` (K:V), `D/S` | `PersonaId`, `IT`, `D/S`: entero (17). Horas por mes: entero; de mayo a diciembre, 3 filas vacías (repartos que terminan en abril). Encabezados de mes: texto DD-MM-AAAA | INT, INT, DECIMAL(5,2) | Horas semanales por instituto y mes de los profesionales multi-instituto; reemplazan la fila única de BUK | `contratos_mes` (origen `EXCEPCION`) |

Las columnas `Cargo` y `Ccosto` de esta hoja tienen fórmulas rotas (`#REF!`) en las 17 celdas y devuelven siempre «MEDICO FISIATRA» y 300202; `Fec_Ingreso` las tiene en 15 de 17 celdas (devuelven 02-01-2026). No se usan: esos datos se toman de BUK.

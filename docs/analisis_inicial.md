# Análisis inicial de los Excel del kit

Revisión del 6 de noviembre de 2026 sobre las copias en `data/raw/`. Complementa `docs/diccionario_datos.md` y `docs/esquema.sql`.

## 1. Hallazgo principal: el Excel de referencia no trae fórmulas

La hoja `Dotacion_Asistencial` (tabla `Dot_Asistencial`, 471 filas × 205 columnas) viene **pegada como valores**: no hay fórmulas en las celdas ni en la definición de la tabla. Solo la fila de totales (476) tiene `SUBTOTAL`. Las hojas `Parámetros`, `Distribucion_NAC`, `Excepciones` y los consolidados sí tienen fórmulas.

Por eso la lógica se reconstruyó probando fórmulas contra los valores de las 471 filas. Las cifras «n de N» indican en cuántas filas cuadra cada fórmula. Las diferencias son ajustes manuales que hay que tratar como excepciones autorizadas o como errores.

## 2. Orden confirmado del cálculo (pasos 3 a 5)

Se cuentan solo las filas con horas > 0 (447 de 471; las otras 24 son licencias extensas o filas partidas sin horas en diciembre).

| Paso | Qué se calcula | Fórmula reconstruida (columnas de `Dotacion_Asistencial`) | Coincide |
|---|---|---|---|
| 1 | Horas disponibles antes de NAS | `AD = H/S − Horas Colación en Contrato (AC)` | 447/447 |
| 2 | Promedio ponderado → tramo | `X = TRUNCAR(promedio de las horas de los 12 meses)`; tramo: ≥ 40, 22 a < 40, < 22 | 423/431 con BUK |
| **3** | **% por cargo y tramo** | `AI %NAS, AJ %Directo, AK %Indirecto` = `Distribucion_NAC[cargo, tramo]` | 466/471 |
| 3b | Horas NAS base | `AH = %NAS × X` (**sobre el promedio de horas contratadas, no sobre AD**) | 447/447 |
| **4** | **Se suman las asignaciones al NAS** | `AT %NAS final = (AH + AS horas de asignaciones) ÷ AD` | 438/447 |
| **5** | **Lo que queda se reparte en proporción entre directa e indirecta** | `AW %Asistencial = 1 − AT`; `AU %Directo final = AW × AJ ÷ (AJ + AK)`; `AV %Indirecto final = AW × AK ÷ (AJ + AK)` | 447/447 |
| 5b | Horas semanales disponibles para atención | `AX = AD × AW` | 438/447 |
| 6 | Atenciones por semana | `BA = REDONDEAR.MENOS(AD × AU × 60 ÷ min. directa)`; `BB = REDONDEAR.MENOS(AD × AV × 60 ÷ 30)` | 441/447 y 444/447 |
| 6b | Atención grupal (AS, ED, UEDA, ULAB, UTAC) | `BF = BA × (1 − %grupal) + BA × %grupal × pacientes por grupo` (sin redondeo) | 91/91 |
| 7 | Atenciones del mes | `PlanAteDir_m = REDONDEAR.MENOS(BF_m × SemHab_m)`; `PlanAteDir+Ind_m = REDONDEAR.MENOS((BF_m + BB_m) × SemHab_m)` | ver abajo |
| 8 | Meta de gestión del mes | `MG_m = REDONDEAR.MENOS(PlanAteDir_m × 0,9)` | 454/471 |

**Conclusión sobre el orden:** primero el % de la tabla por cargo y tramo (paso 3), después las asignaciones especiales se suman al NAS como horas (paso 4) y al final el resto se reparte entre directa e indirecta manteniendo la proporción de la tabla (paso 5). Las asignaciones **no** se descuentan de las horas antes de aplicar los %.

**Cambio legal de jornada (44 → 42 h).** El cambio ya viene aplicado en las horas de BUK (134 personas tienen 44 h de enero a abril y 42 h desde mayo). En el Excel, los meses de enero a abril se calculan con las horas de ese período: `AD_m` cambia y `AT` se recalcula con `AD_m`, pero `AH` (horas NAS base) se mantiene. Con esa regla cuadran los 12 meses en 133 de 136 filas con 44 → 42 y en 282 de 285 filas sin cambio de horas. La columna `Cambio jornada` (65 filas: 38 «Disminución» y 27 «Aumento») no marca el cambio legal.

**Semanas hábiles por persona (`SemHab1..12`) — pendiente.** Enero y febrero cuadran con `semanas del mes − Lic − Vac − Perm` en 440 y 436 filas. De julio a diciembre hay descuentos adicionales por persona (feriado legal adicional prorrateado, día de cumpleaños, vísperas de Fiestas Patrias y Navidad, días progresivos × 0,7, etc.) cuya fórmula exacta no se pudo reconstruir. Ver preguntas.

**Datos que no afectan el resultado:** `AE` pausa saludable = 10 % de X en tramo ≥ 40 y 6 % en los otros; `AF` colación de 15 min × días por semana; `AG` = AH − AE − AF. Es solo el desglose de AH.

## 3. Problemas de datos

| # | Problema | Dónde | Filas afectadas | Regla de validación propuesta |
|---|---|---|---|---|
| 1 | Encabezados fuera de la fila 1 | BUK: fila 2 (fila 1 vacía). Plan: `Dotacion_Asistencial` fila 4, `Excepciones` fila 2, `Distribucion_NAC` filas 5–6 | hojas completas | El cargador busca la fila de encabezados por nombre de columna, no por posición |
| 2 | «O'Higgins» escrito de dos formas | BUK `Área`: «O´Higgins» (acento agudo, U+00B4) en 33 filas. Plan `División`: 4 con «O´Higgins» y 2 con «O'Higgins» (apóstrofo). `Excepciones`: 2 con apóstrofo | 33 + 6 + 2 | Identificar el instituto por el código `IT`, nunca por el nombre; variantes en `institutos_alias` y advertencia |
| 3 | Otras variantes de nombre | Plan: «Pmo» en vez de «PMo» (1 fila); «Valparaiso» sin tilde (1 en el plan, 1 en `Excepciones`) | 3 | Igual que #2 |
| 4 | Profesionales «sin pareja» | Por persona: **0** (las 462 personas están en BUK y en el plan). Por `PersonaId` + `IT`: 5 pares del plan sin BUK y 1 par de BUK sin plan, **todos multi-instituto**: BUK registra a la persona en un solo instituto con el total de horas y el reparto viene de `Excepciones` | 6 pares (6 personas) | El reparto multi-instituto reemplaza la fila de BUK; advertir si la suma por instituto ≠ horas de BUK |
| 5 | BUK solo trae enero a julio | `Periodo` | 12 meses planificados, 7 informados | Proyectar agosto–diciembre con el último mes (origen `PROYECCION`) |
| 6 | Altas y bajas durante el año | Personas con menos de 7 meses en BUK | 31 personas | Detectar altas/bajas comparando con el reporte anterior (bot) |
| 7 | Traslados y cambios de cargo | Personas con `IT` distinto entre meses: 3; con `Cargo` distinto: 2; con `Tipo de Contrato` distinto: 4 | 3 / 2 / 4 personas | Registrar en `cambios` con la fecha desde la que rige |
| 8 | `Ndias` no coincide con `Días de la Jornada` | BUK, PersonaId 140845 (`lmwjv` pero 2 días) | 2 filas | Advertencia |
| 9 | Columna vacía | BUK `Tipo_Trab_161225` | 63 filas | No se usa |
| 10 | Duplicados | BUK: **0** por `PersonaId` + `IT` + `Periodo`. Plan: 17 filas con `PersonaId` repetido (13 multi-instituto + 4 de dos personas con la jornada partida en dos filas); la columna `Repetido` marca solo 10 | 0 / 17 | Clave única en `contratos_mes`; error si se repite |
| 11 | Fechas | Sin fechas inválidas: ningún término anterior al ingreso; `Fecha Término` informada en 57 filas (19 personas), entre el 25-01 y el 30-06 | 0 | Error si término < ingreso o ingreso posterior al período |
| 12 | Horas | Ninguna fuera de rango (todas entre 7 y 44); 3 filas con 7,5 h | 0 | Error si horas ≤ 0 o > jornada legal del período (`jornada_legal`) |
| 13 | Catálogos | Todos los cargos, `Cod_Esp` e `IT` de BUK existen en los catálogos. Institutos sin filas en BUK: 102 Castro, 133 Gerencia, 161 Ñuble. La tabla `Institutos` tiene 25 filas para 18 códigos (variantes «(G)») | 0 | Error si un valor no está en el catálogo |
| 14 | Fórmulas rotas en `Excepciones` | `Cargo` y `Ccosto` tienen `#REF!` en las 17 celdas y devuelven siempre «MEDICO FISIATRA» y 300202. `Fec_Ingreso` tiene `#REF!` en 15 celdas (devuelven 02-01-2026); las otras 2 traen fechas escritas a mano. `Excep_Id` funciona en las celdas: solo está rota la fórmula guardada en la definición de la tabla | 17 filas | Tomar cargo, centro de costo y fecha de ingreso de BUK |
| 15 | `Excepciones` y plan no coinciden | 125129 tiene reparto Antofagasta + Calama en `Excepciones`, pero una sola fila (Antofagasta) en el plan; 140845 tiene Santiago + Calama en `Excepciones` y solo Calama en el plan | 2 personas | Advertencia |
| 16 | Valores manuales que no siguen la regla | % distintos de la tabla: 5 filas; 60 min en vez de 40: 4 filas; %NAS final que no cuadra: 9 filas; atenciones semanales que no son `REDONDEAR.MENOS`: 6; metas mensuales que no son `REDONDEAR.MENOS(plan × 0,9)`: 17 | 41 casos (una fila puede estar en más de una categoría) | Pasarlos a `ajustes_parametro` con motivo y autorización |
| 17 | Asignaciones | 41 filas con 3 asignaciones (1, 2 y «por autorizar») y más de 30 h; 17 filas con 2 asignaciones y 30 h o menos; 401 filas con `Hrs. Asignación 4` = 0,25 sin nombre; 6 filas con `Hrs. Asignación 3` sin nombre | 41 / 17 / 401 / 6 | Validar el máximo de asignaciones y exigir autorización (pendiente de confirmar la regla) |
| 18 | `Mes cumpleaños` distinto del mes de la fecha de nacimiento | Plan | 10 filas | Calcular el mes desde BUK |
| 19 | Datos personales de más | Fecha de nacimiento completa en ambos archivos; un nombre de persona en la descripción de dos asignaciones (`Distribucion_NAC` T32:T33) | todas | Guardar solo el mes de nacimiento; no copiar descripciones con nombres |
| 20 | Catálogo de asignaciones con nombres repetidos | «Coordinador docente» y «Mesas Tecnicas SDM» aparecen dos veces | 2 | `nombre` único en `asignaciones_catalogo` |
| 21 | Vacíos guardados como **texto vacío** (`''`) y no como celda vacía | BUK: `Fecha Término` 3.066, `Tipo_Trab_161225` 63. Plan: `Hrs. Asignación 1` 202, `Hrs. Asignación 2` 341, `Licencia Extensa` 416, AT:AW 15, `% Atención Grupal`/`N° Pacientes` 376 | ~4.500 celdas | El cargador convierte `''` en NULL antes de validar tipos |
| 22 | `Centro de Costo` de BUK guardado como texto | BUK («300513» en vez de 300513) | 3.123 | Convertir a entero; error si no son 6 dígitos |
| 23 | Nombres de asignación con espacio al final | Plan: 18 celdas (`Asignación 1` 2, `Asignación 2` 4, `Por Autorizar` 12); catálogo: 3 | 18 + 3 | Quitar espacios antes de cruzar con el catálogo |
| 24 | Asignación con nombre pero sin horas | Plan: `Asignación 2` 1 fila (fila 221, PersonaId 121081); `Por Autorizar` 4 filas | 5 | Error: faltan horas (o tomar las del catálogo, si las tiene) |
| 25 | Cargo sin % indirecto | `Distribucion_NAC`: «MEDICO ODONTOLOGO» tiene vacío el `% Ind` en los 3 tramos | 1 cargo | Vacío = 0; validar que directa + indirecta + NAS = 100 % |

## 4. Casos de prueba propuestos

Valores tomados directamente del Excel (`Dotacion_Asistencial`). Las horas mensuales y la FOJA no existen en el Excel: se calculan con la definición propuesta (ver pregunta 6) y sirven para revisar, no como verdad del Excel.

Definiciones usadas: horas del mes = horas semanales × `SemHab_m`; horas contratadas del mes = H/S × semanas del mes (`Parámetros!AD`); FOJA = horas directas del mes ÷ horas contratadas del mes.

### Caso 1 · Normal — PersonaId 134561 (fila 364)

Kinesiólogo, Santiago (IT 131), 40 h todo el año, sin colación, tramo ≥ 40 (65 % / 10 % / 25 %), asignaciones 1,25 h (Tutor docente 1 h + 0,25 h). **Mes: junio** (`SemHab6` = 4,2).

| Valor | Excel | Valor | Excel |
|---|---|---|---|
| %NAS final (AT) | 0,28125 | Atenciones directas por semana (BA) | 37 |
| %Directo final (AU) | 0,622917 | Atenciones indirectas por semana (BB) | 7 |
| %Indirecto final (AV) | 0,095833 | Atenciones directas del mes (`PlanAteDir6`) | **155** |
| Horas disponibles por semana (AX) | 28,75 | Atenciones totales del mes (`PlanAteDir+Ind6`) | **184** |
| Horas directa / indirecta / NAS por semana | 24,92 / 3,83 / 11,25 | Meta directa / total del mes (`MG_AteDir6`, `MG_AteDir+Ind6`) | **139 / 165** |
| Horas directa / indirecta / NAS del mes | 104,65 / 16,10 / 47,25 | FOJA junio | **0,6229** |

### Caso 2 · Cambio de jornada 44 → 42 h — PersonaId 117024 (fila 352)

Mismo cargo, instituto y asignaciones que el caso 1, para comparar. BUK: 44 h de enero a abril y 42 h desde mayo; promedio = TRUNCAR(42,67) = 42 → tramo ≥ 40. `AH` = 0,25 × 42 = 10,5 h en todos los meses.

| Valor | Enero (44 h) | Junio (42 h) |
|---|---|---|
| %NAS final | 0,267045 (calculado) | 0,279762 (AT) |
| %Directo final | 0,635227 (calculado) | 0,624206 (AU) |
| Atenciones directas / indirectas por semana | 41 / 8 (calculado) | 39 / 8 (BA, BB) |
| `SemHab` | 4,2 | 4,2 |
| Atenciones directas del mes (`PlanAteDir`) | **172** | **163** |
| Atenciones totales del mes (`PlanAteDir+Ind`) | **205** | **197** |
| Meta directa / total (`MG_AteDir`, `MG_AteDir+Ind`) | **154 / 184** | **146 / 177** |
| Horas directa / indirecta / NAS del mes | 117,39 / 18,06 / 49,35 | 110,11 / 16,94 / 49,35 |
| FOJA | **0,6352** | **0,6242** |

Las cifras de enero salen de recalcular el %NAS final con 44 h (`AD` = 44) manteniendo `AH` = 10,5. En este caso usar los % de diciembre da el mismo resultado, pero en el conjunto de las 136 filas con 44 → 42 solo cuadran 29 con los % de diciembre, contra 133 al recalcular: el test debe incluir otro profesional donde se note la diferencia (por ejemplo 71580, fila 7: en enero el Excel tiene 159; recalculando da 159 y con los % de diciembre daría 155).

### Caso 3 · Multi-instituto — PersonaId 134746 (filas 109 y 110)

Médico fisiatra. BUK lo registra con **40 h en Coquimbo** (IT 41) todos los meses; `Excepciones` lo reparte en **34 h Coquimbo + 6 h Copiapó** (IT 31). El Excel calcula cada instituto por separado, con su propio tramo. **Mes: junio** (`SemHab6` = 4,2 en ambas filas).

| Valor | Coquimbo (34 h) | Copiapó (6 h) | Total persona |
|---|---|---|---|
| Asignaciones | 7,25 h (Líder Equipo 2 + por autorizar 5 + 0,25) | 0 | |
| %NAS final (AT) | 0,413235 | 0,20 | |
| %Directo / %Indirecto final | 0,476746 / 0,110018 | 0,65 / 0,15 | |
| Atenciones directas / indirectas por semana | 24 / 7 | 5 / 1 | |
| Atenciones directas del mes (`PlanAteDir6`) | **100** | **21** | 121 |
| Atenciones totales del mes (`PlanAteDir+Ind6`) | **130** | **25** | 155 |
| Meta directa / total | **90 / 117** | **18 / 22** | 108 / 139 |
| Horas directa / indirecta / NAS del mes | 68,08 / 15,71 / 59,01 | 16,38 / 3,78 / 5,04 | |
| FOJA | **0,4767** | **0,65** | 0,5027 |

Extra para un test de cambio de jornada a mitad de año: PersonaId 137356 (filas partidas: 20 h hasta junio, 30 h desde julio).

## 5. Preguntas para el equipo (antes de programar el cálculo)

1. **Semanas hábiles por persona (`SemHab`).** De julio a diciembre no se pudo reconstruir la fórmula (prorrateo del feriado adicional, cumpleaños, vísperas, días progresivos…). ¿Pedimos a los mentores la versión del Excel con fórmulas? Mientras tanto, ¿usamos `semanas del mes − licencias − vacaciones − permisos` y aceptamos diferencias de julio en adelante?
2. **Base del NAS.** El Excel calcula las horas NAS sobre el promedio de horas contratadas (con colación), pero el %NAS final lo divide por las horas sin colación. ¿Replicamos el Excel tal cual (es lo que pide la rúbrica) aunque parezca inconsistente?
3. **Multi-instituto.** ¿El tramo se calcula con las horas de cada instituto (como hace el Excel) o con el total de la persona? ¿Quién mantiene el reparto por instituto en el MVP, si BUK solo trae una fila?
4. **`Hrs. Asignación 4` = 0,25 h** en 401 filas sin nombre: ¿qué es (¿reunión sindical?) y se aplica a todos?
5. **Regla de asignaciones.** ¿La asignación «por autorizar DMN y VP» cuenta dentro del máximo de 2? ¿Qué hacemos con las 41 filas que tienen 3 y con las 17 de 30 h o menos que tienen 2: error o advertencia?
6. **FOJA.** El Excel no la calcula. ¿La medimos con semanas hábiles (descontando vacaciones y licencias) o con semanas calendario? ¿Por mes o anual?
7. **Meta.** El Excel redondea hacia abajo la meta de cada mes (`REDONDEAR.MENOS(plan × 0,9)`) y luego suma. ¿Lo replicamos o calculamos el 90 % del total anual?
8. **Agosto a diciembre.** BUK llega hasta julio. ¿Proyectamos con el último mes informado, como hace el Excel con «H/S dic»?
9. **Ajustes manuales** (41 filas con % o minutos distintos de la tabla): ¿se cargan como excepciones autorizadas o se reportan como errores?
10. **SIC.** El kit no trae un reporte de SIC. ¿Lo entregan en la hackathon y con qué columnas?
11. **Procesamiento en Blue Prism** (ya pendiente en `CLAUDE.md`): si el cálculo debe ir dentro del bot, este análisis sigue sirviendo, pero cambia dónde se implementa.

Desafío Botathon 2026 — Planificación de Capacidad Técnica “Cada hora cuenta”

El desafío

La planificación asistencial está en el corazón del quehacer de Teletón: define cuántas horas de cada profesional llegan a niños, niñas y jóvenes en rehabilitación, en cada instituto del país. Hoy ese proceso depende de un Excel, alimentado a mano y a través de consultas SQL, con reportes de BUK y del Sistema de Información Clínica (SIC).

El desafío es construir, en 16 horas, un MVP que reemplace ese Excel: que incorpore automáticamente los datos de BUK y SIC, aplique reglas parametrizables y calcule, por profesional y por mes, las horas de atención directa, indirecta y no asistencial, disponibles y la meta de atenciones resultante.

**Requisito obligatorio:** la solución debe usar **Blue ****Prism** como parte central de su funcionamiento. El cómo lo decide cada equipo.

**Pregunta desafío:** ¿Cómo podríamos transformar la planificación asistencial de Teletón en un sistema trazable y parametrizable, que recalcule automáticamente las metas de cada profesional cuando cambian sus horas, su cargo, sus asignaciones o cuando se modifica la dotación durante el año?

Contexto

Cada año Teletón planifica las horas de sus profesionales asistenciales (médicos fisiatras, kinesiólogos, terapeutas ocupacionales, psicólogos, fonoaudiólogos, educadores, enfermería, asistentes sociales, profesores de arte y deporte, entre otros) en todos los Institutos Teletón del país.

La planificación define, para cada profesional y cada mes, cómo se reparten sus horas contratadas:

- **Atención directa:** tiempo con pacientes, individual o grupal.

- **Atención indirecta:** registros clínicos, informes y preparación asociada a la atención.

- **No asistencial (NAS):** coordinación, capacitación, docencia, investigación, comités y otras asignaciones especiales.

Con ese reparto se calcula la meta de atenciones de cada profesional, que es la base de su indicador de desempeño. El proceso se alimenta de dos sistemas, que para la Botathon llegarán como reportes Excel simulados (no habrá acceso a sus APIs):

| **Fuente** | **Qué**** ****aporta** |
| --- | --- |
| BUK (RR.HH.) | Dotación: instituto, cargo, tipo de contrato, fechas de inicio y término, horas semanales, reemplazos, licencias y vacantes |
| SIC (Sistema de Información Clínica) | Atenciones realizadas por profesional y mes, para contrastar lo planificado con lo ejecutado |

En 2026 el cálculo se complica porque la jornada baja de 44 a 42 horas a partir de mayo, así que la planificación se divide en dos períodos (enero–abril y mayo–diciembre).

El problema actual

Toda la planificación vive en un único Excel con más de 600 profesionales, decenas de columnas calculadas y fórmulas encadenadas. Sus hojas principales son:

| **Hoja** | **Qué**** ****contiene** |
| --- | --- |
| Parámetros | Días hábiles e inhábiles por mes, feriados (incluidos regionales), vacaciones, % de atención grupal y pacientes por grupo según área |
| Distribución_NAC | % directo / indirecto / NAS por cargo y tramo de jornada; minutos estándar por atención; catálogo de asignaciones especiales y sus horas |
| Dotación_Asistencial | Una fila por profesional: datos contractuales, horas por mes, asignaciones y todos los cálculos resultantes |
| Excepciones | Profesionales que reparten horas entre dos o más institutos, con horas distintas por mes |
| Planificación Total | Consolidado por instituto y área |
| Dotación_Asistencial_09.03.26, Dotacion_2026 | Copias de versiones anteriores, guardadas a mano |

Los dolores principales:

- **Fragilidad:** alta exposición al error manual en el ingreso de la información.

- **Sin trazabilidad:** los cambios (ej: aumento o disminución de jornada, reemplazos, nuevas asignaciones, etc.) quedan con una marca en el archivo (color, nota, cód u observación registrada en una columna); no hay historial de quién autoriza o solicita cambios y su justificación.

- **Versionado manual:** las versiones se guardan como copias de hojas o libros Excel con fecha en el nombre.

- **Carga manual desde BUK:** la dotación se copia y pega desde el archivo Excel enviado por Gerencia de Personas (GP); altas, bajas y cambios de contrato se detectan con una marca generada por una fórmula.

- **Parámetros escondidos:** los porcentajes y estándares están en tablas de parámetros; cambiar una regla exige hacerlo manualmente por quién generó la planilla.

- **Poca visibilidad:** jefaturas y profesionales no tienen una vista simple de su propia planificación ni de cómo se compara con lo realizado en SIC. No tiene respaldo de última versión aprobada.

- **Cambios en las Asignaciones especiales:** no existe un sistema que concentre esta información, lo que es recolectado por una persona a través de correos desde distintas jefaturas del país y que tienen validación de DMN.

Lógica de negocio a modelar

El MVP debe reproducir este cálculo por profesional, por mes, y dejar cada regla como parámetro editable (no como fórmula fija).

- **Horas contratadas por mes.** Se toman de BUK según la vigencia del contrato (fechas de inicio y término). Se calcula el promedio ponderado de horas semanales del año y se marca si hubo aumento o disminución de jornada.

- **Tramo de jornada.** Según el promedio ponderado, el profesional cae en uno de tres tramos: 40 horas o más, entre 22 y 40, o menos de 22.

- **Distribución por cargo.** Para el cargo homologado y el tramo, la tabla de parámetros entrega el % directo, % indirecto y % NAS.

- **Asignaciones especiales.** Se descuentan horas semanales fijas por rol (Líder de equipo 2 h, Tutor docente 1 h, Comité paritario 0,5 h, Reunión sindical 0,25 h, etc.). Regla: máximo 2 asignaciones para profesionales con más de 30 h semanales; algunas requieren autorización de la dirección nacional. Podrían ser modificadas según necesidad institucional.

- **Horas disponibles para atención** y su distribución proporcional entre directa e indirecta.

- **Conversión de horas**** disponibles**** a atenciones****.** Se convierten las horas en número de atenciones según los minutos estándar del cargo (directa: 30, 40, 45 o 60 min; indirecta: 30 min), redondeando hacia abajo. Las áreas con atención grupal (Educación, Asistente Social, Arte, Deporte, Unidad Laboral) aplican un % grupal y un número de pacientes por grupo, distinto para Santiago/Concepción y otros institutos o como defina DMN (Dirección Médica Nacional).

- **Proyección anual.** Se cruza con días hábiles, feriados (incluidos regionales, como los de Arica y Ñuble) y vacaciones de cada mes que en el caso de Aysén es diferente.

- **Meta de gestión:** Se establece como piso mínimo un % de cumplimiento de la proyección anual. Actualmente un 90%.

Casos especiales que el MVP debe soportar:

- **Multi-instituto****:** un profesional con horas en dos o más institutos, distintas por mes (hoja Excepciones).

- **Reemplazos y plazo fijo:** vínculo con el titular reemplazado y fechas de vigencia.

- **Vacantes y cargos nuevos:** cupos sin persona asignada que igual se planifican o se excluyen.

- **Licencias extensas:** marcan meses sin atención.

- **Cambio legal de jornada:** 44 h hasta abril y 42 h desde mayo de 2026.

- **Cambios en asignaciones**

- **Cambios en beneficios**

- **Cambios contractuales de cargo, jornada, IT y vigencia**

- **Zonas geográficas: afectan vacaciones y días hábiles**

Alcance del MVP

De momento lo que se espera como entregable es uno o más dashboard donde se pueda filtrar en diferentes niveles la información para sus resúmenes (nacional, por instituto, por tipo de atención, especialidad o área, cargo, meses, etc.) 

Se debe tener un resumen visual similar a este:

> **Nota del equipo:** en el `.docx` original esto es una imagen (`word/media/image1.emf`) que se perdió al convertirlo a Markdown. La tabla de abajo es su transcripción. Sirve como modelo del **formato**, no de las cifras: los números no salen del kit (el total es de 21.586 h semanales y en la hoja `Planificacion Total` del kit es de 16.165 h). Además, todos los institutos tienen el mismo reparto (60 % directa, 25 % indirecta, 15 % NAS), y aparecen Ñuble y Castro, que no tienen profesionales en el BUK del kit. Para verificar las cifras del dashboard, la referencia es la hoja `Planificacion Total`.

**Médico terapéutico - Socio educativo** (los tiempos están en horas:minutos por semana)

| Instituto | Suma de horas semanales | Tiempo atención directa | Tiempo atención indirecta | Tiempo actividad no asistencial (NAS) | Atención anual directa (grupal e individual) | Atención anual indirecta | Total atenciones en planificación por año | Meta gestión al 90 % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Arica | 540 | 324:00 | 135:00 | 81:00 | 20.558 | 5.202 | 25.760 | 23.184 |
| Iquique | 688 | 412:48 | 172:00 | 103:12 | 27.252 | 6.726 | 33.978 | 30.580 |
| Antofagasta | 845 | 507:00 | 211:15 | 126:45 | 30.386 | 8.514 | 38.900 | 35.010 |
| Calama | 561 | 336:36 | 140:15 | 84:09 | 22.848 | 6.009 | 28.857 | 25.971 |
| Copiapó | 622 | 373:12 | 155:30 | 93:18 | 23.754 | 6.808 | 30.561 | 27.505 |
| Coquimbo | 1.184 | 710:24 | 296:00 | 177:36 | 42.546 | 11.781 | 54.327 | 48.894 |
| Valparaíso | 2.095 | 1257:00 | 523:45 | 314:15 | 73.762 | 20.613 | 94.375 | 84.937 |
| O'Higgins | 592 | 355:12 | 148:00 | 88:48 | 22.927 | 6.845 | 29.772 | 26.795 |
| Talca | 1.408 | 844:48 | 352:00 | 211:12 | 52.351 | 14.389 | 66.740 | 60.066 |
| Concepción | 1.930 | 1158:00 | 482:30 | 289:30 | 75.470 | 19.050 | 94.520 | 85.068 |
| Ñuble | 562 | 337:26 | 140:36 | 84:21 | 21.781 | 6.503 | 28.283 | 25.455 |
| Temuco | 1.329 | 797:24 | 332:15 | 199:21 | 46.696 | 12.945 | 59.642 | 53.677 |
| Puerto Montt | 1.409 | 845:24 | 352:15 | 211:21 | 49.207 | 14.007 | 63.214 | 56.893 |
| Coyhaique | 511 | 306:36 | 127:45 | 76:39 | 19.505 | 5.034 | 24.540 | 22.086 |
| Valdivia | 664 | 398:24 | 166:00 | 99:36 | 24.823 | 6.980 | 31.803 | 28.623 |
| Castro | 132 | 79:20 | 33:03 | 19:50 | 4.618 | 1.270 | 5.888 | 5.299 |
| Santiago | 6.513 | 3907:48 | 1628:15 | 976:57 | 265.496 | 66.209 | 331.705 | 298.535 |
| **Total general** | **21.586** | **12951:22** | **5396:24** | **3237:50** | **823.982** | **218.884** | **1.042.866** | **938.578** |
| **Meta gestión al 90 %** | | | | | **741.584** | **196.995** | **938.579** | |

Generar una vista con indicadores pertinentes del desarrollo:

- #Meta de Gestión Asistencial (90% de la sumatoria de atenciones resultantes del cálculo): Atenciones planificadas * 90%

- % FOJA (Factor de Ocupación de Jornada Asistencial): Horas mensuales disponibles para atención directa/Horas mensuales contratadas

Los requisitos describen **qué** debe lograr el MVP, no **cómo** construirlo: la arquitectura, las herramientas complementarias y el diseño son decisión de cada equipo.

Con 16 horas, el foco es un flujo completo y funcional para todos los institutos del país, no una réplica de todas las hojas. La solución la usará el equipo de planificación central, que gestiona y ve todos los centros de Chile a la vez. El jurado valorará más un núcleo sólido que muchas funciones a medias.

**Obligatorio**** (****mínimo**** para ****competir****):**

- **Blue ****Prism**** en el centro:** la solución usa Blue Prism para automatizar una o más etapas del proceso, de forma que su aporte sea visible en la demo.

- **Incorporación de datos sin copiar y pegar:** los reportes Excel de BUK y SIC entran a la solución sin intervención manual de datos, y los errores del reporte se detectan y se informan.

- **Reglas parametrizables:** porcentajes por cargo y tramo, minutos estándar, asignaciones especiales y calendario se pueden modificar sin tocar código.

- **Cálculo correcto:** la planificación por profesional y mes coincide con el Excel en los casos de prueba entregados.

- **Cambios durante el año:** cuando llega un reporte nuevo con cambios (jornada, cargo, altas, bajas), la solución los identifica y la planificación se ajusta desde la fecha en que rigen.

- **Visibilidad:** el equipo de planificación central ve el consolidado nacional y puede filtrar y profundizar por instituto, área y profesional.

**Deseable**** (****suma**** puntos):**

- Trazabilidad de cambios y versiones: quién cambió qué, cuándo y por qué.

- Comparación entre lo planificado y lo realizado según SIC, con alertas de desviación.

- Soporte de profesionales multi-instituto, reemplazos y vacantes.

- Aprobación de asignaciones que requieren autorización.

- Simulación del impacto de un cambio de parámetro antes de aplicarlo.

- Distribución automática de reportes a las jefaturas de cada instituto.

Pista

No es la única solución posible ni la esperada: es un punto de partida para equipos que quieran orientarse.

Piensen en qué partes del proceso son repetitivas y basadas en archivos, y en cuáles requieren criterio humano. Un bot suele brillar recibiendo, leyendo, validando y comparando reportes; una aplicación suele ser mejor lugar para parametrizar reglas, calcular y que las personas revisen y aprueben. ¿Qué pasa si el bot se encarga de lo primero y le entrega a la aplicación solo lo que cambió?

Datos disponibles y restricciones

Los equipos recibirán un kit de datos **ficticios** (sin nombres ni RUT reales). BUK y SIC se simulan con reportes Excel; no habrá acceso a sus APIs.

| **Archivo** | **Contenido** |
| --- | --- |
| Nac - Base contratos x mes | Información de Dotación de Profesionales Anonimizada |
| Nac - Planificación Asistencial x mes | El Excel actual anonimizado, como referencia de la lógica |

*Estos archivos estarán **disponibles** **al inicio del desafío.*

Restricciones:

- **Blue ****Prism**** obligatorio:** la organización provee el ambiente de Blue Prism. Las demás tecnologías (lenguaje, framework, base de datos, low-code) son libres.

- **Cada equipo tiene acceso a una Máquina Virtual en la ****cuál**** podrán montar su solución y utilizar ****BluePrism**

- **Tiempo:** 16 horas de desarrollo, incluida la preparación de la demo.

- **Datos personales y clínicos:** la solución debe considerar desde su diseño la normativa chilena de protección de datos personales (control de acceso, trazabilidad, mínimo de datos).

- **Uso de IA permitido:** se puede usar IA para programar o como parte de la solución, declarando cómo se usó.

Entregables y evaluación 

Al cierre de las 16 horas cada equipo entrega:

- **MVP funcionando** y demo en vivo de 5 minutos, que incluya procesar el reporte BUK (simulado con archivos que serán provistos por la organización) y mostrar su efecto en la planificación.

- **Presentación Pich**

- **Considerar u****na lámina de arquitectura** que explique qué hace Blue Prism, qué hace el resto de la solución y cómo escalaría a todos los institutos.

**Rúbrica de evaluación ****del pitch**** de semifinales:**

| **N°** | **Dimensión** | **Indicador** | **4 · Destacado** | **3 · Logrado** | **2 · En desarrollo** | **1 · Insuficiente** |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **Problema** | **Problema y usuario** | Identifica con precisión un problema real de la Teletón y a quién afecta (pacientes, familias, voluntarios o donantes), con datos o ejemplos concretos. | Identifica el problema y el usuario con claridad, pero sin datos ni ejemplos que lo respalden. | El problema es general o no queda claro a quién afecta. | No identifica un problema ni un usuario. |
| 2 |  | **Pertinencia de la solución** | La solución responde directamente al problema y justifica por qué un bot es la herramienta adecuada. | La solución responde al problema, con una justificación parcial. | La relación entre el problema y la solución es débil o forzada. | La solución no se relaciona con el problema planteado. |
| 3 | **Solución** | **Innovación y propuesta de valor** | Aporta un enfoque original con una ventaja clara frente a lo que ya existe. | Tiene al menos un elemento diferenciador. | Es similar a soluciones existentes, sin un aporte claro. | No presenta una propuesta de valor. |
| 4 |  | **Funcionamiento del ****bot** | Muestra de principio a fin el flujo de conversación o una demo funcional. | Explica el flujo principal, con algunos vacíos. | Describe el bot de forma general, sin mostrar cómo funciona. | No explica cómo funciona el bot. |
| 5 |  | **Viabilidad técnica** | Define tecnologías, datos e integraciones realistas para implementarlo. | Define las tecnologías, pero deja aspectos importantes sin resolver. | La propuesta técnica es vaga o poco realista. | No aborda cómo se construiría. |
| 6 | **Impacto** | **Accesibilidad e inclusión** | Está diseñado para personas con discapacidad (voz, lectura fácil, lector de pantalla, etc.) y lo demuestra. | Considera la accesibilidad en algunos aspectos del diseño. | Menciona la accesibilidad, pero no la aplica. | No considera la accesibilidad. |
| 7 |  | **Impacto esperado** | Plantea un impacto concreto y medible: a cuántas personas llega y qué mejora. | El impacto es claro, pero no medible. | El impacto se plantea de forma general. | No explica el impacto. |
| 8 | **Pitch** | **Claridad y manejo del tiempo** | Tiene una estructura clara y lenguaje comprensible, y cumple los 3 minutos. | Es claro, con algún desorden menor o un leve exceso de tiempo. | Es desordenado, o excede el tiempo y debe cortarse. | No se entiende la propuesta. |
| 9 |  | **Respuesta a preguntas** | Responde con seguridad y fundamentos; el equipo domina su propuesta. | Responde correctamente la mayoría de las preguntas. | Sus respuestas son imprecisas o evasivas. | No logra responder. |

	**BOTATHON 2026**  ·  Desafío Teletón «Cada hora cuenta»  ·  Duoc UC × Teletón	**1**
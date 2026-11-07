# INICIO: preparar el proyecto y primera tarea

Instrucciones para Claude Code. Antes de empezar, lee `CLAUDE.md` (contexto del desafío y decisiones del equipo). Estamos en plena hackathon: trabaja rápido, sin pasos de más, y avísame apenas algo falle en vez de seguir intentando por tu cuenta.

## 1. Revisar la ubicación

Confirma que la carpeta actual NO esté dentro del Escritorio (Desktop), Documentos ni iCloud Drive. En este Mac, pip se ha colgado varias veces en carpetas sincronizadas con iCloud. Si la carpeta está en una de esas ubicaciones, detente y avísame. La ubicación esperada es `/Users/matiberoiza/Developer/botathon-teleton`.

## 2. Crear la estructura

```
data/raw/       Excel originales (solo lectura)
data/entrada/   archivos de cambios que deja el bot de Blue Prism
docs/           enunciado y documentación
```

## 3. Ordenar los archivos

1. Si `desafio.md` está suelto en la raíz, muévelo a `docs/`.
2. Busca los dos Excel del kit en la carpeta actual: uno contiene "Base contratos" en el nombre y el otro "Planificación Asistencial".
3. Si no están aquí, búscalos en `~/Downloads` y `~/Desktop`. Muéstrame lo que encontraste y espera mi confirmación antes de copiarlos.
4. **Copia** (no muevas) los Excel a `data/raw/` y déjalos de solo lectura (`chmod a-w`), para que nada del proyecto pueda modificarlos.

## 4. Entorno de Python

1. Revisa la versión con `python3 --version`.
2. Crea un entorno virtual en `.venv` con `python3 -m venv .venv`.
3. Instala `pandas`, `openpyxl`, `streamlit` y `pytest` dentro del entorno, y guarda las versiones en `requirements.txt`.
4. Si pip pasa más de 2 minutos sin avanzar, cancélalo y reintenta una vez con `--no-cache-dir --timeout 60`. Si vuelve a fallar, detente y avísame.

## 5. Primera tarea: diccionario de datos y esquema

Todavía no escribas código del cargador ni del cálculo. Esta tarea es solo análisis y propuesta.

1. **Revisa los dos Excel:** nombres de las hojas, fila donde están los encabezados, cantidad de filas y columnas de cada hoja.
2. **Confirma los problemas de datos** que menciona `CLAUDE.md` (encabezados en la fila 2, «O'Higgins» escrito de dos formas, profesionales de la planificación sin pareja en BUK) y anota cualquier otro que aparezca: duplicados, fechas inválidas, horas fuera de rango, valores que no están en los catálogos. Cuenta cuántas filas afecta cada uno.
3. **Lee las fórmulas** de la hoja Dotación_Asistencial (openpyxl con `data_only=False`) y confirma el orden real de los pasos 3 a 5 de la lógica de cálculo: distribución por cargo y tramo, descuento de asignaciones especiales y horas disponibles. Explícalo con las celdas o columnas que lo demuestran.
4. **Escribe `docs/diccionario_datos.md`** solo con las columnas que usa el cálculo (unas 40, no las 205): nombre exacto en el Excel, archivo y hoja de origen, tipo, para qué se usa y la tabla de destino. Las columnas mes a mes (licencias, vacaciones, permisos) descríbelas como patrón, no una por una.
5. **Escribe `docs/esquema.sql`** con el esquema SQLite: `profesionales`, `contratos_mes`, los catálogos de parámetros, `resultados_planificacion` y `cambios`, según `CLAUDE.md`.
6. **Propón 3 casos de prueba** del Excel de referencia: un profesional normal, uno con cambio de jornada y uno multi-instituto. Para cada uno, indica su `PersonaId` y los valores esperados de un mes (horas directas, indirectas y NAS, atenciones y FOJA).

## 6. Detenerte y reportar

Al terminar, detente y muéstrame un resumen corto con:

- Qué quedó hecho de los pasos 1 a 4.
- Los problemas de datos encontrados, con la cantidad de filas de cada uno.
- El orden confirmado de los pasos 3 a 5.
- Las preguntas que necesitas que el equipo resuelva antes de programar el cálculo.

No sigas con el cargador ni con el cálculo hasta que revisemos el diccionario y el esquema con el equipo.

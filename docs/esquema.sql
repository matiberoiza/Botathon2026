-- Esquema SQLite del MVP «Cada hora cuenta» (propuesta para revisar con el equipo).
--
-- Cómo usarlo:
--     sqlite3 planificacion.db < docs/esquema.sql
--
-- Reglas:
--   * Ningún porcentaje, minuto estándar, hora de asignación ni fecha va en el código: todo vive en estas tablas.
--   * Mínimo de datos: no se guardan nombres, RUT ni fecha de nacimiento completa (solo el mes).
--   * Fechas como texto ISO: 'AAAA-MM-DD'. Los períodos son el día 1 del mes ('2026-05-01').
--   * Sí/no como INTEGER 0/1. Números con decimales como REAL.
--   * SQLite trae las claves foráneas DESACTIVADAS: el backend debe ejecutar
--     «PRAGMA foreign_keys = ON» en CADA conexión (esta línea solo aplica a la sesión que carga el archivo).

PRAGMA foreign_keys = ON;

-- =====================================================================
-- 1. CATÁLOGOS DE PARÁMETROS (se cargan desde el archivo de parámetros; se editan en el frontend)
-- =====================================================================

-- Institutos (un código IT por instituto)
CREATE TABLE institutos (
    it                          INTEGER PRIMARY KEY,           -- 11, 12, 21 … 161
    abreviatura                 TEXT NOT NULL UNIQUE,          -- 'Ari', 'San' (como en BUK)
    nombre                      TEXT NOT NULL,                 -- 'O''Higgins', 'Valparaíso'
    grupo_factor_grupal         TEXT NOT NULL DEFAULT 'OTROS'
        CHECK (grupo_factor_grupal IN ('SAN_CON', 'OTROS')),   -- Santiago/Concepción vs. otros
    dias_vacaciones_adicionales REAL NOT NULL DEFAULT 5        -- 5 general, 10 en Coyhaique (Aysén)
);

-- Todas las formas en que aparece un instituto en los reportes (O´Higgins, Pmo, Valparaiso…)
CREATE TABLE institutos_alias (
    alias TEXT PRIMARY KEY,
    it    INTEGER NOT NULL REFERENCES institutos (it)
);

CREATE TABLE especialidades (
    cod_esp      TEXT PRIMARY KEY,                             -- 'FI', 'KI', 'AS', 'UTAC'…
    especialidad TEXT NOT NULL
);

-- Cargos y minutos estándar (dependen solo del cargo, no del tramo)
CREATE TABLE cargos (
    cargo         TEXT PRIMARY KEY,                            -- nombre exacto como viene en BUK
    cod_esp       TEXT REFERENCES especialidades (cod_esp),
    unidad        TEXT,
    min_directa   INTEGER NOT NULL CHECK (min_directa > 0),    -- 30, 40, 45 o 60
    min_indirecta INTEGER NOT NULL CHECK (min_indirecta > 0)   -- 30
);

-- Tramos según el promedio truncado de horas (40 exactas → >= 40; 22 exactas → 22 a 40)
CREATE TABLE tramos (
    tramo       TEXT PRIMARY KEY,                              -- 'MAYOR_IGUAL_40', 'ENTRE_22_40', 'MENOR_22'
    horas_desde REAL NOT NULL,                                 -- incluida
    horas_hasta REAL                                           -- excluida; NULL = sin tope
);

-- % directa / indirecta / NAS por cargo y tramo (un % vacío en el Excel se carga como 0)
CREATE TABLE distribucion_cargo (
    cargo         TEXT NOT NULL REFERENCES cargos (cargo),
    tramo         TEXT NOT NULL REFERENCES tramos (tramo),
    pct_directa   REAL NOT NULL CHECK (pct_directa BETWEEN 0 AND 1),
    pct_indirecta REAL NOT NULL CHECK (pct_indirecta BETWEEN 0 AND 1),
    pct_nas       REAL NOT NULL CHECK (pct_nas BETWEEN 0 AND 1),
    vigente_desde TEXT NOT NULL DEFAULT '2026-01-01',
    PRIMARY KEY (cargo, tramo, vigente_desde),
    CHECK (abs(pct_directa + pct_indirecta + pct_nas - 1) < 0.0001)
);

-- Catálogo de asignaciones especiales (nombres sin espacios al final)
CREATE TABLE asignaciones_catalogo (
    asignacion_id         INTEGER PRIMARY KEY,
    nombre                TEXT NOT NULL UNIQUE,                -- 'Líder Equipo', 'Tutor docente'…
    horas_semanales       REAL,                                -- NULL = se define por persona
    requiere_autorizacion INTEGER NOT NULL DEFAULT 0 CHECK (requiere_autorizacion IN (0, 1)),
    descripcion           TEXT
);

-- Factor grupal por especialidad y grupo de instituto
CREATE TABLE factor_grupal (
    cod_esp             TEXT NOT NULL REFERENCES especialidades (cod_esp),
    grupo_instituto     TEXT NOT NULL CHECK (grupo_instituto IN ('SAN_CON', 'OTROS')),
    pct_grupal          REAL NOT NULL CHECK (pct_grupal BETWEEN 0 AND 1),
    pacientes_por_grupo REAL NOT NULL CHECK (pacientes_por_grupo > 0),
    PRIMARY KEY (cod_esp, grupo_instituto)
);

-- Semanas de planificación por mes (= ROUND(días hábiles / 5, 1))
CREATE TABLE calendario_mes (
    periodo      TEXT PRIMARY KEY CHECK (periodo = date(periodo, 'start of month')),
    dias_habiles INTEGER NOT NULL,
    semanas      REAL NOT NULL
);

-- Feriados nacionales (it NULL), regionales y feriado colectivo de febrero
CREATE TABLE feriados (
    feriado_id  INTEGER PRIMARY KEY,
    fecha       TEXT NOT NULL CHECK (date(fecha) IS NOT NULL),
    it          INTEGER REFERENCES institutos (it),            -- NULL = todo el país
    tipo        TEXT NOT NULL CHECK (tipo IN ('NACIONAL', 'REGIONAL', 'COLECTIVO')),
    descripcion TEXT
);
-- En SQLite, UNIQUE trata cada NULL como distinto: por eso se usa ifnull para los feriados nacionales
CREATE UNIQUE INDEX ux_feriados ON feriados (fecha, ifnull(it, 0));

-- Jornada legal máxima (44 h hasta abril de 2026, 42 h desde mayo): para validar BUK
CREATE TABLE jornada_legal (
    vigente_desde TEXT PRIMARY KEY,
    horas_maximas REAL NOT NULL
);

-- Parámetros sueltos: meta 0.9, máximo de asignaciones, umbral de 30 h, reintentos, meta usada para SIC…
CREATE TABLE parametros (
    clave       TEXT PRIMARY KEY,
    valor       TEXT NOT NULL,                                 -- texto para admitir números y opciones ('DIRECTA')
    descripcion TEXT NOT NULL
);

-- =====================================================================
-- 2. EJECUCIONES Y CARGAS (lo que envía Blue Prism)
-- =====================================================================

-- Una carga por fuente dentro de una ejecución del bot.
-- (ejecucion_id, fuente) es la clave estable: repetir el mismo envío devuelve la carga existente.
CREATE TABLE cargas (
    carga_id             INTEGER PRIMARY KEY,
    ejecucion_id         TEXT NOT NULL,                        -- lo genera Blue Prism al iniciar
    fuente               TEXT NOT NULL CHECK (fuente IN ('BUK', 'SIC', 'DELTAS', 'PARAMETROS', 'ENTRADAS')),
    archivo              TEXT,
    hash_archivo         TEXT,                                 -- SHA-256: verifica el contenido
    cobertura_desde      TEXT,                                 -- primer período informado
    cobertura_hasta      TEXT,                                 -- último período informado
    version_referencia   INTEGER REFERENCES cargas (carga_id), -- carga BUK aceptada contra la que se comparó
    estado               TEXT NOT NULL DEFAULT 'RECIBIDA'
        CHECK (estado IN ('RECIBIDA', 'VALIDADA', 'ACEPTADA', 'RECHAZADA', 'PENDIENTE')),
    filas_leidas         INTEGER NOT NULL DEFAULT 0,
    filas_validas        INTEGER NOT NULL DEFAULT 0,
    filas_excluidas      INTEGER NOT NULL DEFAULT 0,
    filas_alerta         INTEGER NOT NULL DEFAULT 0,
    enviado_por          TEXT NOT NULL,                        -- 'bot' o usuario
    recibido_en          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (ejecucion_id, fuente)
);
-- La «última versión aceptada» de BUK = la carga BUK con estado ACEPTADA más reciente
CREATE INDEX ix_cargas_buk ON cargas (fuente, estado, carga_id);

-- =====================================================================
-- 3. PROFESIONALES, VACANTES Y CONTRATOS
-- =====================================================================

CREATE TABLE profesionales (
    persona_id     INTEGER PRIMARY KEY,                        -- PersonaId de BUK
    mes_nacimiento INTEGER CHECK (mes_nacimiento BETWEEN 1 AND 12)  -- solo el mes
);

-- Cupos sin persona asignada (RN-22)
CREATE TABLE vacantes (
    vacante_id      INTEGER PRIMARY KEY,
    it              INTEGER NOT NULL REFERENCES institutos (it),
    cargo           TEXT NOT NULL REFERENCES cargos (cargo),
    horas_semanales REAL NOT NULL CHECK (horas_semanales >= 0),
    vigente_desde   TEXT NOT NULL,
    vigente_hasta   TEXT,
    planificable    INTEGER NOT NULL DEFAULT 0 CHECK (planificable IN (0, 1)),
    persona_id      INTEGER REFERENCES profesionales (persona_id)  -- cuando se asigna una persona
);

-- Contrato del mes: una fila por PersonaId + IT + Periodo (o por vacante + IT + Periodo)
CREATE TABLE contratos_mes (
    contrato_id     INTEGER PRIMARY KEY,
    persona_id      INTEGER REFERENCES profesionales (persona_id),
    vacante_id      INTEGER REFERENCES vacantes (vacante_id),
    it              INTEGER NOT NULL REFERENCES institutos (it),
    periodo         TEXT NOT NULL CHECK (periodo = date(periodo, 'start of month')),
    cargo           TEXT NOT NULL REFERENCES cargos (cargo),
    cod_esp         TEXT REFERENCES especialidades (cod_esp),
    centro_costo    INTEGER,                                   -- en BUK viene como texto de 6 dígitos
    tipo_contrato   TEXT,                                      -- 'Indefinido' / 'Plazo fijo'
    tipo_trabajador TEXT,                                      -- 'Titular' / 'Reemplazo'
    reemplaza_a     INTEGER REFERENCES profesionales (persona_id),
    fecha_ingreso   TEXT,
    fecha_termino   TEXT,                                      -- en BUK, el vacío viene como texto ''
    horas_semanales REAL NOT NULL CHECK (horas_semanales >= 0),
    dias_semana     INTEGER CHECK (dias_semana BETWEEN 0 AND 7),
    horas_colacion  REAL NOT NULL DEFAULT 0,                   -- de las entradas de planificación
    origen          TEXT NOT NULL DEFAULT 'BUK'
        CHECK (origen IN ('BUK', 'EXCEPCION', 'MANUAL', 'PROYECCION')),
    estado_calidad  TEXT NOT NULL DEFAULT 'VALIDO'
        CHECK (estado_calidad IN ('VALIDO', 'ALERTA', 'PENDIENTE', 'EXCLUIDO')),
    motivo          TEXT,                                      -- por qué ALERTA, PENDIENTE o EXCLUIDO
    carga_id        INTEGER REFERENCES cargas (carga_id),
    CHECK ((persona_id IS NULL) <> (vacante_id IS NULL)),      -- o persona o vacante, no ambas
    UNIQUE (persona_id, it, periodo),
    UNIQUE (vacante_id, it, periodo)
);
CREATE INDEX ix_contratos_periodo ON contratos_mes (periodo, it);

-- Períodos de jornada: una fila por cada fila de la planificación (profesional + instituto + período).
-- Cada período tiene su propio promedio, tramo y NAS base. Si un profesional tiene dos períodos en el
-- mismo instituto, es una jornada partida (RN-07). También guarda la colación, que BUK no trae.
CREATE TABLE periodos_jornada (
    persona_id     INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it             INTEGER NOT NULL REFERENCES institutos (it),
    desde          TEXT NOT NULL,                              -- '2026-01-01'
    hasta          TEXT NOT NULL,                              -- '2026-06-30'
    cargo          TEXT NOT NULL REFERENCES cargos (cargo),
    cod_esp        TEXT REFERENCES especialidades (cod_esp),
    horas_colacion REAL NOT NULL DEFAULT 0,
    dias_semana    INTEGER,
    fila_excel     INTEGER,                                    -- fila de origen en Dotacion_Asistencial
    fuente         TEXT NOT NULL DEFAULT 'PLANIFICACION',
    PRIMARY KEY (persona_id, it, desde),
    CHECK (hasta >= desde)
);

-- Reparto multi-instituto por mes (hoja Excepciones); reemplaza la fila agregada de BUK
CREATE TABLE reparto_multi_instituto (
    persona_id      INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it              INTEGER NOT NULL REFERENCES institutos (it),
    periodo         TEXT NOT NULL,
    horas_semanales REAL NOT NULL CHECK (horas_semanales >= 0),
    carga_id        INTEGER REFERENCES cargas (carga_id),
    PRIMARY KEY (persona_id, it, periodo)
);

-- =====================================================================
-- 4. ENTRADAS DE PLANIFICACIÓN (datos que BUK no trae)
-- =====================================================================

-- Asignaciones especiales de cada profesional, con vigencia y autorización
CREATE TABLE asignaciones_profesional (
    id              INTEGER PRIMARY KEY,
    persona_id      INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it              INTEGER NOT NULL REFERENCES institutos (it),
    asignacion_id   INTEGER REFERENCES asignaciones_catalogo (asignacion_id),  -- NULL = sin nombre
    horas_semanales REAL NOT NULL CHECK (horas_semanales >= 0),  -- horas de la persona: prevalecen sobre el catálogo
    vigente_desde   TEXT NOT NULL,
    vigente_hasta   TEXT,
    estado          TEXT NOT NULL DEFAULT 'NO_REQUIERE'
        CHECK (estado IN ('NO_REQUIERE', 'PENDIENTE', 'APROBADA', 'RECHAZADA')),
    autorizado_por  TEXT,
    autorizado_en   TEXT
);

-- Licencias, vacaciones y permisos en SEMANAS por mes
CREATE TABLE ausencias_mes (
    persona_id INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it         INTEGER NOT NULL REFERENCES institutos (it),
    periodo    TEXT NOT NULL,
    tipo       TEXT NOT NULL CHECK (tipo IN ('LICENCIA', 'VACACIONES', 'PERMISO')),
    semanas    REAL NOT NULL CHECK (semanas >= 0),
    PRIMARY KEY (persona_id, it, periodo, tipo)
);

-- Días adicionales del año (cumpleaños, vísperas, feriado adicional, progresivos…)
CREATE TABLE dias_adicionales (
    persona_id INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it         INTEGER NOT NULL REFERENCES institutos (it),
    anio       INTEGER NOT NULL,
    tipo       TEXT NOT NULL,
    dias       REAL NOT NULL CHECK (dias >= 0),
    PRIMARY KEY (persona_id, it, anio, tipo)
);

-- Semanas hábiles por profesional y mes (RN-15). En el MVP se importan del Excel de planificación,
-- porque su fórmula de julio a diciembre está pendiente. Ya incluyen las ausencias: no descontarlas otra vez.
CREATE TABLE semanas_habiles (
    persona_id INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it         INTEGER NOT NULL REFERENCES institutos (it),
    periodo    TEXT NOT NULL,
    semanas    REAL NOT NULL CHECK (semanas >= 0),
    fuente     TEXT NOT NULL DEFAULT 'EXCEL_PLANIFICACION',
    carga_id   INTEGER REFERENCES cargas (carga_id),
    PRIMARY KEY (persona_id, it, periodo)
);

-- Ajustes individuales autorizados (% o minutos distintos del catálogo, % grupal con V°B° DMN…)
CREATE TABLE ajustes_parametro (
    id             INTEGER PRIMARY KEY,
    persona_id     INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it             INTEGER NOT NULL REFERENCES institutos (it),
    campo          TEXT NOT NULL CHECK (campo IN ('PCT_DIRECTA', 'PCT_INDIRECTA', 'PCT_NAS', 'MIN_DIRECTA',
                                                  'MIN_INDIRECTA', 'PCT_GRUPAL', 'PACIENTES_GRUPO')),
    valor_estandar REAL,
    valor          REAL NOT NULL,
    vigente_desde  TEXT NOT NULL,
    vigente_hasta  TEXT,
    motivo         TEXT NOT NULL,
    autorizado_por TEXT,                                       -- NULL = sin autorización: genera ALERTA
    estado         TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE', 'APROBADO', 'RECHAZADO'))
);

-- Atenciones realizadas según SIC (para comparar; no modifican la planificación)
CREATE TABLE atenciones_sic (
    persona_id INTEGER NOT NULL REFERENCES profesionales (persona_id),
    it         INTEGER NOT NULL REFERENCES institutos (it),
    periodo    TEXT NOT NULL,
    atenciones INTEGER NOT NULL CHECK (atenciones >= 0),
    es_simulado INTEGER NOT NULL DEFAULT 0 CHECK (es_simulado IN (0, 1)),
    carga_id   INTEGER REFERENCES cargas (carga_id),
    PRIMARY KEY (persona_id, it, periodo)
);

-- =====================================================================
-- 5. RESULTADOS DEL CÁLCULO (por versión)
-- =====================================================================

CREATE TABLE versiones_calculo (
    version_id    INTEGER PRIMARY KEY,
    creada_en     TEXT NOT NULL DEFAULT (datetime('now')),
    motivo        TEXT NOT NULL,                               -- 'Carga BUK julio', 'Cambio de meta a 85 %'…
    usuario       TEXT NOT NULL,
    carga_buk_id  INTEGER REFERENCES cargas (carga_id),        -- carga BUK usada
    es_simulacion INTEGER NOT NULL DEFAULT 0 CHECK (es_simulacion IN (0, 1)),
    estado        TEXT NOT NULL DEFAULT 'EN_PROCESO'
        CHECK (estado IN ('EN_PROCESO', 'PUBLICADA', 'FALLIDA')),  -- si falla, sigue vigente la última PUBLICADA
    aprobada      INTEGER NOT NULL DEFAULT 0 CHECK (aprobada IN (0, 1))
);

-- Una fila por profesional (o vacante), instituto y mes, por versión.
-- Tres campos de estado separados: calidad del registro, origen del dato y disponibilidad del indicador.
CREATE TABLE resultados_planificacion (
    version_id               INTEGER NOT NULL REFERENCES versiones_calculo (version_id),
    persona_id               INTEGER REFERENCES profesionales (persona_id),
    vacante_id               INTEGER REFERENCES vacantes (vacante_id),
    it                       INTEGER NOT NULL REFERENCES institutos (it),
    periodo                  TEXT NOT NULL,
    -- Entradas usadas (para explicar cada número)
    cargo                    TEXT NOT NULL,
    horas_semanales          REAL NOT NULL,
    promedio_horas           REAL NOT NULL,                    -- TRUNCAR(promedio); por período si hay jornada partida
    tramo                    TEXT NOT NULL REFERENCES tramos (tramo),
    horas_disponibles_sem    REAL NOT NULL,                    -- horas semanales − colación
    nas_base_sem             REAL NOT NULL,
    horas_asignaciones_sem   REAL NOT NULL,
    -- Distribución semanal
    pct_nas_final            REAL,
    pct_directa_final        REAL,
    pct_indirecta_final      REAL,
    horas_directa_sem        REAL,
    horas_indirecta_sem      REAL,
    horas_nas_sem            REAL,
    atenciones_directa_sem   REAL,                             -- incluye el factor grupal (puede tener decimales)
    atenciones_indirecta_sem INTEGER,
    -- Mes
    semanas_habiles          REAL NOT NULL,
    horas_contratadas_mes    REAL,
    horas_directa_mes        REAL,
    atenciones_directas_mes  INTEGER,                          -- floor(atenciones_directa_sem × semanas_habiles)
    atenciones_total_mes     INTEGER,                          -- floor((directa + indirecta) × semanas_habiles)
    meta_directa_mes         INTEGER,                          -- floor(atenciones_directas_mes × meta)
    meta_total_mes           INTEGER,
    foja                     REAL,                             -- NULL cuando estado_foja = 'NO_APLICA'
    -- Estados
    estado_calidad           TEXT NOT NULL
        CHECK (estado_calidad IN ('VALIDO', 'ALERTA', 'PENDIENTE', 'EXCLUIDO')),
    origen_dato              TEXT NOT NULL DEFAULT 'REAL'
        CHECK (origen_dato IN ('REAL', 'PROYECCION')),
    estado_foja              TEXT NOT NULL DEFAULT 'CALCULADO'
        CHECK (estado_foja IN ('CALCULADO', 'NO_APLICA')),
    motivos                  TEXT,                             -- alertas y motivos acumulados en el proceso
    CHECK ((persona_id IS NULL) <> (vacante_id IS NULL)),
    UNIQUE (version_id, persona_id, it, periodo),
    UNIQUE (version_id, vacante_id, it, periodo)
);
CREATE INDEX ix_resultados_filtros ON resultados_planificacion (version_id, periodo, it, cargo);

-- =====================================================================
-- 6. TRAZABILIDAD
-- =====================================================================

-- Errores y alertas de cada carga (los que detecta Blue Prism y los que detecta el backend)
CREATE TABLE errores_validacion (
    id         INTEGER PRIMARY KEY,
    carga_id   INTEGER NOT NULL REFERENCES cargas (carga_id),
    fila       INTEGER,                                        -- fila del Excel de origen
    persona_id INTEGER,                                        -- sin clave foránea: puede venir inválido
    it         INTEGER,
    campo      TEXT,
    valor      TEXT,
    regla      TEXT NOT NULL,                                  -- 'INSTITUTO_ALIAS', 'CARGO_SIN_CATALOGO'…
    severidad  TEXT NOT NULL CHECK (severidad IN ('CRITICO', 'ERROR', 'ALERTA')),
    detectado_por TEXT NOT NULL CHECK (detectado_por IN ('BOT', 'BACKEND')),
    detalle    TEXT NOT NULL
);

-- Qué cambió, valor anterior y nuevo, desde cuándo rige, quién y por qué
CREATE TABLE cambios (
    cambio_id      INTEGER PRIMARY KEY,
    tabla          TEXT NOT NULL,                              -- 'contratos_mes', 'distribucion_cargo'…
    persona_id     INTEGER REFERENCES profesionales (persona_id),
    it             INTEGER REFERENCES institutos (it),
    tipo_cambio    TEXT NOT NULL CHECK (tipo_cambio IN ('ALTA', 'BAJA', 'MODIFICACION', 'PARAMETRO')),
    campo          TEXT,
    valor_anterior TEXT,
    valor_nuevo    TEXT,
    vigente_desde  TEXT NOT NULL,                              -- el recálculo parte desde aquí
    origen         TEXT NOT NULL CHECK (origen IN ('BOT', 'APP')),
    carga_id       INTEGER REFERENCES cargas (carga_id),
    usuario        TEXT NOT NULL,
    motivo         TEXT,
    registrado_en  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX ix_cambios_persona ON cambios (persona_id, vigente_desde);

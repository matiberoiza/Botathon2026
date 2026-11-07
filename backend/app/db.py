"""
Conexión a la base SQLite con SQLAlchemy.

SQLite trae las claves foráneas desactivadas: aquí se activan en CADA conexión, junto con el
modo WAL (permite leer mientras se escribe, así el dashboard no se bloquea durante una carga).
"""

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from . import config

_engine: Engine | None = None


def obtener_engine() -> Engine:
    """Devuelve el motor de conexión, creándolo la primera vez."""
    global _engine
    if _engine is None:
        config.DB_RUTA.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{config.DB_RUTA}",
            connect_args={"check_same_thread": False, "timeout": 30},  # espera cargas concurrentes breves
        )

        @event.listens_for(_engine, "connect")
        def _activar_pragmas(conexion_dbapi, _registro):
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.close()

    return _engine


def reiniciar_engine() -> None:
    """Cierra la conexión actual (lo usan las pruebas al cambiar de archivo de base)."""
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


def crear_tablas_si_no_existen() -> bool:
    """Crea las tablas desde docs/esquema.sql si la base está vacía. Devuelve True si las creó."""
    engine = obtener_engine()
    if inspect(engine).has_table("institutos"):
        # Migración aditiva: conserva todas las filas de las bases ya creadas.
        with engine.begin() as c:
            columnas = {f[1] for f in c.execute(text("PRAGMA table_info(cargas)"))}
            if "hash_payload" not in columnas:
                c.execute(text("ALTER TABLE cargas ADD COLUMN hash_payload TEXT"))
            if "periodos_completos" not in columnas:
                c.execute(text("ALTER TABLE cargas ADD COLUMN periodos_completos TEXT NOT NULL DEFAULT '[]'"))
        return False
    conexion = engine.raw_connection()
    try:
        conexion.executescript(config.ESQUEMA.read_text(encoding="utf-8"))
        conexion.commit()
    finally:
        conexion.close()
    return True


def probar_conexion() -> tuple[bool, str]:
    """Consulta mínima a la base. Devuelve (conectada, detalle) sin lanzar errores."""
    try:
        with obtener_engine().connect() as conexion:
            version = conexion.execute(text("SELECT sqlite_version()")).scalar()
            tablas = conexion.execute(text("SELECT count(*) FROM sqlite_master WHERE type = 'table'")).scalar()
        return True, f"SQLite {version} · {tablas} tablas · {config.DB_RUTA.name}"
    except Exception as error:
        return False, f"{type(error).__name__}: {error}"[:300]

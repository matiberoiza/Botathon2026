"""
Configuración del backend.

Lo que puede cambiar entre computadores se lee del archivo backend/.env (no se sube a git).
Para crearlo, copia backend/.env.example. Si no existe, se usan los valores por defecto.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carpeta raíz del proyecto (sirve igual en Mac y en Windows)
RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / "backend" / ".env")


def _ruta(variable: str, por_defecto: Path) -> Path:
    """Lee una ruta del .env; si es relativa, se toma desde la raíz del proyecto."""
    valor = os.getenv(variable)
    if not valor:
        return por_defecto
    ruta = Path(valor)
    return ruta if ruta.is_absolute() else RAIZ / ruta


# Base de datos SQLite: un solo archivo (no se sube a git)
DB_RUTA = _ruta("DB_RUTA", RAIZ / "data" / "planificacion.db")

# Esquema de la base y archivos de la carga inicial (parámetros y entradas de planificación)
ESQUEMA = RAIZ / "docs" / "esquema.sql"
CARPETA_GENERADOS = _ruta("CARPETA_GENERADOS", RAIZ / "data" / "generados")

# Direcciones desde las que el frontend puede llamar a la API
ORIGENES_FRONTEND = os.getenv("ORIGENES_FRONTEND", "http://localhost:5173").split(",")

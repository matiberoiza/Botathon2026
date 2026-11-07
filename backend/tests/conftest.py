"""Las pruebas usan una base SQLite temporal, nunca la base real del proyecto."""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
os.environ["DB_RUTA"] = str(Path(tempfile.mkdtemp()) / "pruebas.db")
sys.path.insert(0, str(RAIZ / "herramientas"))  # para usar el simulador del bot

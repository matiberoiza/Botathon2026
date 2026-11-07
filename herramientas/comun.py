"""Rutas y lectura de los Excel del kit, compartidas por las herramientas."""

import datetime as dt
import warnings
from pathlib import Path

import openpyxl
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RAW = RAIZ / "data" / "raw"
GENERADOS = RAIZ / "data" / "generados"   # salidas de las herramientas (no se suben a git)
BUK = RAW / "Nac - Base contratos x mes.xlsx"
PLAN = RAW / "Nac - Planificación Asistencial x mes.xlsx"

# Columnas de la hoja Dotacion_Asistencial que usan las herramientas (nombre exacto en el Excel)
COL_HORAS_DISP = "H/Sem Disponible antes NAS\ndic"


def abrir_plan():
    """Libro de planificación con valores (no fórmulas). Silencia un aviso inofensivo de openpyxl."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return openpyxl.load_workbook(PLAN, data_only=True)


def leer_buk() -> pd.DataFrame:
    """Dotación BUK: encabezados en la fila 2. Los vacíos que vienen como texto '' se dejan como nulos."""
    df = pd.read_excel(BUK, sheet_name="Dotacion_2026", header=1)
    df["Fecha Término"] = pd.to_datetime(df["Fecha Término"].replace("", None))
    df["Centro de Costo"] = pd.to_numeric(df["Centro de Costo"])
    df["Mes"] = df["Periodo"].dt.month
    return df


def leer_dotacion() -> pd.DataFrame:
    """Hoja Dotacion_Asistencial: encabezados en la fila 4; se quita la fila de totales.
    Agrega FilaExcel (número de fila en el Excel) para poder rastrear cada dato."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = pd.read_excel(PLAN, sheet_name="Dotacion_Asistencial", header=3)
    df = df.copy()  # la hoja tiene 205 columnas: copiar evita un aviso de rendimiento de pandas
    df["FilaExcel"] = df.index + 5
    df = df[df["IT"].astype(str) != "Total"].copy()
    df["IT"] = df["IT"].astype(int)
    df["PersonaId"] = df["PersonaId"].astype(int)
    df = df.replace("", None)
    return df


def horas(valor) -> float:
    """La columna H/Sem Disp.Ate viene como duración de Excel: se convierte a horas."""
    if isinstance(valor, (dt.timedelta, pd.Timedelta)):
        return valor.total_seconds() / 3600
    return float(valor) if valor is not None and valor == valor else 0.0

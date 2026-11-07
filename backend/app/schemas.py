"""Modelos Pydantic: definen y validan la forma de los JSON que entran y salen de la API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EstadoCalidad = Literal["VALIDO", "ALERTA", "PENDIENTE", "EXCLUIDO"]


class EstadoSalud(BaseModel):
    """Respuesta de /api/salud."""
    api: str = "ok"
    base_datos_conectada: bool
    detalle_base_datos: str


# ---------- Lo que envía Blue Prism a POST /api/v1/buk/sync ----------

class ContratoBUK(BaseModel):
    """Una fila de BUK ya normalizada por el bot (sin nombres ni RUT; del nacimiento, solo el mes)."""
    PersonaId: int
    IT: int
    Periodo: date
    Cargo: str
    CodEsp: str | None = None
    HorasSemanales: float = Field(ge=0)
    TipoContrato: str | None = None
    TipoTrabajador: str | None = None
    FechaIngreso: date | None = None
    FechaTermino: date | None = None
    DiasSemana: int | None = Field(default=None, ge=0, le=7)
    CentroCosto: int | None = None
    MesNacimiento: int | None = Field(default=None, ge=1, le=12)
    estado: EstadoCalidad = "VALIDO"     # clasificación preliminar del bot
    motivo: str | None = None

    @field_validator("Periodo")
    @classmethod
    def periodo_dia_uno(cls, valor: date) -> date:
        if valor.day != 1:
            raise ValueError("Periodo debe ser el día 1 del mes")
        return valor

    @field_validator("Cargo")
    @classmethod
    def sin_espacios(cls, valor: str) -> str:
        return valor.strip()


class RegistroExcluido(BaseModel):
    """Fila que el bot no pudo leer o validar; se guarda para la auditoría."""
    fila: int | None = None
    PersonaId: int | None = None
    IT: int | None = None
    campo: str | None = None
    valor: str | None = None
    motivo: str


class RepartoMultiInstituto(BaseModel):
    """Horas de un profesional en un instituto y mes (hoja Excepciones)."""
    PersonaId: int
    IT: int
    Periodo: date
    HorasSemanales: float = Field(ge=0)


class Conteos(BaseModel):
    leidas: int = 0
    validas: int = 0
    excluidas: int = 0
    alertas: int = 0


class CargaBUK(BaseModel):
    """Cuerpo de POST /api/v1/buk/sync. Los contratos llegan como lista libre y el backend valida
    cada uno por separado: una fila inválida no rechaza a las demás."""
    ejecucion_id: str = Field(min_length=1)
    archivo: str | None = None
    hash_archivo: str | None = None
    conteos: Conteos = Conteos()
    contratos: list[dict]
    excluidos: list[RegistroExcluido] = []
    multi_instituto: list[RepartoMultiInstituto] = []


class RespuestaCarga(BaseModel):
    carga_id: int
    estado: str
    repetida: bool = False               # True si ese ejecucion_id ya se había recibido
    conteos: dict
    version_id: int | None = None        # versión del cálculo generada con esta carga
    cambios: dict | None = None          # altas, bajas y modificaciones detectadas respecto de la carga anterior


# ---------- Parámetros ----------

class CambioParametro(BaseModel):
    valor: str
    motivo: str = Field(min_length=1)
    usuario: str = Field(min_length=1)

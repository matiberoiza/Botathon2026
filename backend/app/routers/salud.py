"""Estado de la API y de la conexión a SQL Server (lo muestra el frontend en la cabecera)."""

from fastapi import APIRouter

from ..db import probar_conexion
from ..schemas import EstadoSalud

router = APIRouter(prefix="/api", tags=["salud"])


@router.get("/salud", response_model=EstadoSalud)
def salud() -> EstadoSalud:
    conectada, detalle = probar_conexion()
    return EstadoSalud(base_datos_conectada=conectada, detalle_base_datos=detalle)

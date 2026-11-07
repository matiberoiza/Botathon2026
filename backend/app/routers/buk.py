"""Endpoints que usa Blue Prism: enviar la carga de BUK y consultar la última versión aceptada."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..db import obtener_engine
from ..schemas import CargaBUK, RespuestaCarga
from ..sincronizacion import procesar_carga_buk

router = APIRouter(prefix="/api/v1/buk", tags=["Blue Prism"])


@router.post("/sync", response_model=RespuestaCarga)
def sincronizar_buk(carga: CargaBUK) -> dict:
    """Recibe la carga de BUK del bot, la valida, la guarda y recalcula la planificación."""
    if not carga.contratos and not carga.excluidos:
        raise HTTPException(status_code=400, detail="La carga no trae contratos.")
    return procesar_carga_buk(carga)


@router.get("/ultima-version")
def ultima_version() -> dict:
    """Última carga BUK aceptada: el bot la usa como referencia para detectar cambios."""
    with obtener_engine().connect() as c:
        fila = c.execute(text("SELECT carga_id, ejecucion_id, archivo, hash_archivo, cobertura_desde, cobertura_hasta, "
                              "recibido_en FROM cargas WHERE fuente = 'BUK' AND estado = 'ACEPTADA' "
                              "ORDER BY carga_id DESC LIMIT 1")).mappings().first()
        if not fila:
            return {"existe": False}
        contratos = c.execute(text("SELECT persona_id, it, periodo, cargo, horas_semanales, tipo_contrato, fecha_termino "
                                   "FROM contratos_mes WHERE carga_id = :c"), {"c": fila["carga_id"]}).mappings().all()
    return {"existe": True, **fila, "contratos": [dict(x) for x in contratos]}

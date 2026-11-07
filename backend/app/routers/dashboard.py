"""
Endpoints que usa el frontend. Todos leen la última versión PUBLICADA del cálculo.
Filtros opcionales: it (instituto) y mes (1 a 12).
"""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from ..db import obtener_engine
from ..motor import calcular
from ..schemas import CambioParametro

router = APIRouter(prefix="/api/v1", tags=["Dashboard"])


def _version(c) -> int:
    version = c.execute(text("SELECT max(version_id) FROM versiones_calculo WHERE estado = 'PUBLICADA'")).scalar()
    if version is None:
        raise HTTPException(status_code=404, detail="Todavía no hay una planificación calculada: falta la carga de BUK.")
    return version


def _filtros(it: int | None, mes: int | None) -> tuple[str, dict]:
    condiciones, valores = [], {}
    if it is not None:
        condiciones.append("r.it = :it")
        valores["it"] = it
    if mes is not None:
        condiciones.append("r.periodo = :periodo")
        valores["periodo"] = f"2026-{mes:02d}-01"
    return ("AND " + " AND ".join(condiciones)) if condiciones else "", valores


@router.get("/dashboard/kpis")
def kpis(it: int | None = None, mes: int | None = Query(default=None, ge=1, le=12)) -> dict:
    """Indicadores: profesionales, horas, atenciones, meta y FOJA (ponderada por horas)."""
    with obtener_engine().connect() as c:
        version = _version(c)
        filtro, valores = _filtros(it, mes)
        fila = c.execute(text(f"""
            SELECT count(DISTINCT r.persona_id) AS profesionales,
                   round(sum(r.horas_contratadas_mes), 1) AS horas_contratadas_mes,
                   round(sum(r.horas_directa_mes), 1) AS horas_directas_mes,
                   round(sum(r.horas_indirecta_sem * r.semanas_habiles), 1) AS horas_indirectas_mes,
                   round(sum(r.horas_nas_sem * r.semanas_habiles), 1) AS horas_nas_mes,
                   sum(r.atenciones_directas_mes) AS atenciones_directas,
                   sum(r.atenciones_total_mes) AS atenciones_planificadas,
                   sum(r.meta_directa_mes) AS meta_directa,
                   sum(r.meta_total_mes) AS meta_gestion,
                   sum(r.estado_calidad <> 'VALIDO') AS registros_con_observaciones
            FROM resultados_planificacion r WHERE r.version_id = :v {filtro}"""), {"v": version, **valores}).mappings().first()
        actualizado = c.execute(text("SELECT creada_en FROM versiones_calculo WHERE version_id = :v"), {"v": version}).scalar()
    datos = dict(fila)
    horas = datos["horas_contratadas_mes"] or 0
    datos["foja_promedio"] = round(datos["horas_directas_mes"] / horas, 4) if horas else None
    return {"version_id": version, "it": it, "mes": mes, "actualizado_en": actualizado, **datos}


@router.get("/dashboard/institutos")
def por_instituto(mes: int | None = Query(default=None, ge=1, le=12)) -> list[dict]:
    """Totales por instituto (para el gráfico de barras)."""
    with obtener_engine().connect() as c:
        version = _version(c)
        filtro, valores = _filtros(None, mes)
        filas = c.execute(text(f"""
            SELECT r.it, i.nombre AS instituto, count(DISTINCT r.persona_id) AS profesionales,
                   sum(r.atenciones_directas_mes) AS atenciones_directas, sum(r.atenciones_total_mes) AS atenciones_planificadas,
                   sum(r.meta_total_mes) AS meta_gestion,
                   round(sum(r.horas_directa_mes) / nullif(sum(r.horas_contratadas_mes), 0), 4) AS foja
            FROM resultados_planificacion r JOIN institutos i ON i.it = r.it
            WHERE r.version_id = :v {filtro} GROUP BY r.it, i.nombre ORDER BY r.it"""), {"v": version, **valores}).mappings().all()
    return [dict(f) for f in filas]


@router.get("/profesionales")
def profesionales(it: int | None = None, mes: int | None = Query(default=None, ge=1, le=12),
                  limite: int = Query(default=500, le=10000)) -> list[dict]:
    """Detalle por profesional, instituto y mes, con sus estados."""
    with obtener_engine().connect() as c:
        version = _version(c)
        filtro, valores = _filtros(it, mes)
        filas = c.execute(text(f"""
            SELECT r.persona_id, r.it, r.periodo, r.cargo, r.tramo, r.horas_semanales, r.promedio_horas,
                   round(r.horas_directa_sem, 2) AS horas_directa_sem, round(r.horas_indirecta_sem, 2) AS horas_indirecta_sem,
                   round(r.horas_nas_sem, 2) AS horas_nas_sem, r.semanas_habiles,
                   r.atenciones_directas_mes, r.atenciones_total_mes, r.meta_directa_mes, r.meta_total_mes,
                   round(r.foja, 4) AS foja, r.estado_calidad, r.origen_dato, r.estado_foja, r.motivos
            FROM resultados_planificacion r WHERE r.version_id = :v {filtro}
            ORDER BY r.it, r.persona_id, r.periodo LIMIT :limite"""), {"v": version, "limite": limite, **valores}).mappings().all()
    return [dict(f) for f in filas]


@router.get("/excepciones")
def excepciones(it: int | None = None) -> dict:
    """Alertas agrupadas por tipo (regla de visualización) y errores de la última carga."""
    with obtener_engine().connect() as c:
        version = _version(c)
        filtro, valores = _filtros(it, None)
        filas = c.execute(text(f"SELECT persona_id, it, estado_calidad, motivos FROM resultados_planificacion r "
                               f"WHERE r.version_id = :v AND r.estado_calidad <> 'VALIDO' {filtro}"),
                          {"v": version, **valores}).all()
        carga = c.execute(text("SELECT max(carga_id) FROM cargas WHERE fuente = 'BUK'")).scalar()
        errores = c.execute(text("SELECT fila, persona_id, it, campo, valor, regla, severidad, detectado_por, detalle "
                                 "FROM errores_validacion WHERE carga_id = :c"), {"c": carga}).mappings().all()
    # Se agrupa por motivo (no por el estado final del registro, que mezcla varios motivos).
    # Un motivo «por autorizar» deja el registro PENDIENTE; los demás son ALERTA.
    grupos: dict[str, set] = {}
    for persona, instituto, _estado, motivos in filas:
        for motivo in (motivos or "Sin detalle").split("; "):
            grupos.setdefault(motivo, set()).add((persona, instituto))
    agrupadas = [{"estado": "PENDIENTE" if "por autorizar" in m.lower() else "ALERTA", "motivo": m, "profesionales": len(p)}
                 for m, p in grupos.items()]
    agrupadas.sort(key=lambda x: -x["profesionales"])
    return {"version_id": version, "alertas_agrupadas": agrupadas, "errores_carga": [dict(e) for e in errores]}


@router.get("/parametros")
def ver_parametros() -> list[dict]:
    with obtener_engine().connect() as c:
        return [dict(f) for f in c.execute(text("SELECT clave, valor, descripcion FROM parametros ORDER BY clave")).mappings()]


@router.put("/parametros/{clave}")
def cambiar_parametro(clave: str, cambio: CambioParametro) -> dict:
    """Cambia un parámetro (por ejemplo META_PCT de 0.9 a 0.85), deja trazabilidad y recalcula."""
    with obtener_engine().begin() as c:
        anterior = c.execute(text("SELECT valor FROM parametros WHERE clave = :k"), {"k": clave}).scalar()
        if anterior is None:
            raise HTTPException(status_code=404, detail=f"No existe el parámetro {clave}.")
        if clave == "META_PCT":
            try:
                if not 0 < float(cambio.valor) <= 1:
                    raise ValueError
            except ValueError:
                raise HTTPException(status_code=400, detail="META_PCT debe ser un número entre 0 y 1 (por ejemplo 0.85).")
        c.execute(text("UPDATE parametros SET valor = :v WHERE clave = :k"), {"v": cambio.valor, "k": clave})
        c.execute(text("INSERT INTO cambios (tabla, tipo_cambio, campo, valor_anterior, valor_nuevo, vigente_desde, origen, "
                       "usuario, motivo) VALUES ('parametros', 'PARAMETRO', :k, :a, :n, '2026-01-01', 'APP', :u, :m)"),
                  {"k": clave, "a": anterior, "n": cambio.valor, "u": cambio.usuario, "m": cambio.motivo})
    version = calcular(motivo=f"Cambio de {clave}: {anterior} → {cambio.valor}", usuario=cambio.usuario)
    return {"clave": clave, "valor_anterior": anterior, "valor_nuevo": cambio.valor, "version_id": version}


@router.get("/versiones")
def versiones() -> list[dict]:
    """Historial de versiones del cálculo (auditoría)."""
    with obtener_engine().connect() as c:
        return [dict(f) for f in c.execute(text("SELECT version_id, creada_en, motivo, usuario, estado, carga_buk_id "
                                                 "FROM versiones_calculo ORDER BY version_id DESC")).mappings()]


@router.get("/cambios")
def cambios(it: int | None = None, tipo: str | None = None, limite: int = Query(default=500, le=5000)) -> dict:
    """Cambios detectados entre cargas de BUK y cambios de parámetros (trazabilidad: qué, desde cuándo, quién)."""
    condiciones, valores = [], {"limite": limite}
    if it is not None:
        condiciones.append("c.it = :it")
        valores["it"] = it
    if tipo:
        condiciones.append("c.tipo_cambio = :tipo")
        valores["tipo"] = tipo.upper()
    filtro = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    with obtener_engine().connect() as c:
        filas = c.execute(text(f"""
            SELECT c.cambio_id, c.registrado_en, c.tipo_cambio, c.persona_id, c.it, i.nombre AS instituto, c.campo,
                   c.valor_anterior, c.valor_nuevo, c.vigente_desde, c.origen, c.usuario, c.motivo, c.carga_id
            FROM cambios c LEFT JOIN institutos i ON i.it = c.it {filtro}
            ORDER BY c.cambio_id DESC LIMIT :limite"""), valores).mappings().all()
        resumen = dict(c.execute(text(f"SELECT tipo_cambio, count(*) FROM cambios c {filtro} GROUP BY tipo_cambio"),
                                 {k: v for k, v in valores.items() if k != "limite"}).all())
    return {"resumen": resumen, "cambios": [dict(f) for f in filas]}

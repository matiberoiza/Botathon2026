"""
Carga inicial de la base SQLite: catálogos de parámetros y entradas de planificación.

Lee los dos archivos que se generan desde el Excel de planificación:
  - parametros.xlsx: institutos, cargos, % por tramo, asignaciones, factor grupal, calendario…
  - entradas_planificacion.xlsx: datos por profesional que BUK no trae (colación, asignaciones,
    ausencias, semanas hábiles, reparto multi-instituto y ajustes manuales).

Solo se ejecuta si la base está vacía. Para volver a cargar desde cero, borrar el archivo .db.

Uso (desde la carpeta del proyecto):
    python -m backend.app.carga_inicial
"""

import pandas as pd
from sqlalchemy import text

from . import config
from .db import crear_tablas_si_no_existen, obtener_engine

CAMPOS_AJUSTE = {"PCT_DIRECTO": "PCT_DIRECTA", "PCT_INDIRECTO": "PCT_INDIRECTA", "PCT_NAS": "PCT_NAS",
                 "MIN_DIRECTA": "MIN_DIRECTA", "MIN_INDIRECTA": "MIN_INDIRECTA"}


def _nulo(valor):
    """pandas usa NaN para las celdas vacías; SQLite necesita None."""
    return None if valor is None or (isinstance(valor, float) and valor != valor) else valor


def _filas(df: pd.DataFrame) -> list[dict]:
    return [{k: _nulo(v) for k, v in fila.items()} for fila in df.to_dict("records")]


def _periodo(mes: int) -> str:
    return f"2026-{int(mes):02d}-01"


def base_tiene_catalogos() -> bool:
    with obtener_engine().connect() as c:
        return c.execute(text("SELECT count(*) FROM institutos")).scalar() > 0


def cargar(forzar_mensaje: bool = True) -> dict:
    """Carga catálogos y entradas. Devuelve cuántas filas quedaron en cada tabla."""
    crear_tablas_si_no_existen()
    if base_tiene_catalogos():
        return {"mensaje": "La base ya tenía la carga inicial; no se cargó de nuevo."}

    ruta_p = config.CARPETA_GENERADOS / "parametros.xlsx"
    ruta_e = config.CARPETA_GENERADOS / "entradas_planificacion.xlsx"
    if not ruta_p.exists() or not ruta_e.exists():
        raise FileNotFoundError(f"Faltan {ruta_p.name} o {ruta_e.name} en {config.CARPETA_GENERADOS}. "
                                "Genéralos con: python herramientas/generar_parametros.py")
    P = pd.read_excel(ruta_p, sheet_name=None)
    E = pd.read_excel(ruta_e, sheet_name=None)
    conteo = {}

    with obtener_engine().begin() as c:
        def insertar(tabla: str, filas: list[dict]):
            if filas:
                columnas = list(filas[0])
                c.execute(text(f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES "
                               f"({', '.join(':' + x for x in columnas)})"), filas)
            conteo[tabla] = len(filas)

        # --- Catálogos ---
        insertar("institutos", [{"it": f["IT"], "abreviatura": f["Abreviatura"], "nombre": f["Nombre"],
                                  "grupo_factor_grupal": f["GrupoFactorGrupal"],
                                  "dias_vacaciones_adicionales": f["DiasVacacionesAdicionales"]}
                                 for f in _filas(P["Institutos"])])
        insertar("institutos_alias", [{"alias": str(f["Alias"]), "it": f["IT"]} for f in _filas(P["AliasInstitutos"])])
        insertar("especialidades", [{"cod_esp": f["CodEsp"], "especialidad": f["Especialidad"]}
                                     for f in _filas(P["Especialidades"])])
        insertar("cargos", [{"cargo": f["Cargo"], "cod_esp": f["CodEsp"], "unidad": f["Unidad"],
                             "min_directa": int(f["MinDirecta"]), "min_indirecta": int(f["MinIndirecta"])}
                            for f in _filas(P["Cargos"])])
        insertar("tramos", [{"tramo": f["Tramo"], "horas_desde": f["HorasDesde"], "horas_hasta": f["HorasHasta"]}
                            for f in _filas(P["Tramos"])])
        insertar("distribucion_cargo", [{"cargo": f["Cargo"], "tramo": f["Tramo"], "pct_directa": f["PctDirecto"],
                                         "pct_indirecta": f["PctIndirecto"], "pct_nas": f["PctNAS"]}
                                        for f in _filas(P["Distribucion"])])
        insertar("asignaciones_catalogo", [{"nombre": f["Asignacion"], "horas_semanales": f["HorasSemanales"],
                                            "requiere_autorizacion": 1 if f["RequiereAutorizacionDMN"] == "SI" else 0,
                                            "descripcion": f["Descripcion"]}
                                           for f in _filas(P["Asignaciones"])])
        insertar("factor_grupal", [{"cod_esp": f["CodEsp"], "grupo_instituto": f["GrupoInstituto"],
                                    "pct_grupal": f["PctGrupal"], "pacientes_por_grupo": f["PacientesPorGrupo"]}
                                   for f in _filas(P["FactorGrupal"])])
        insertar("calendario_mes", [{"periodo": str(f["Periodo"])[:10], "dias_habiles": int(f["DiasHabiles"]),
                                     "semanas": f["Semanas"]} for f in _filas(P["Calendario"])])
        insertar("feriados", [{"fecha": str(f["Fecha"])[:10], "it": f["IT"], "tipo": f["Tipo"]}
                              for f in _filas(P["Feriados"])])
        insertar("jornada_legal", [{"vigente_desde": f["VigenteDesde"], "horas_maximas": f["HorasMaximas"]}
                                   for f in _filas(P["JornadaLegal"])])
        parametros = [{"clave": f["Clave"], "valor": str(f["Valor"]), "descripcion": f["Descripcion"]}
                      for f in _filas(P["Parametros"])]
        parametros.append({"clave": "META_SIC", "valor": "DIRECTA",
                           "descripcion": "Meta contra la que se compara SIC: DIRECTA o TOTAL (pendiente de confirmar)"})
        insertar("parametros", parametros)

        # --- Profesionales (los de la planificación; BUK agrega o completa los suyos al sincronizar) ---
        filas_plan = _filas(E["FilasPlanificacion"])
        personas = sorted({f["PersonaId"] for f in filas_plan} | set(E["MultiInstituto"]["PersonaId"]))
        insertar("profesionales", [{"persona_id": int(p)} for p in personas])

        # --- Períodos de jornada: una fila por fila de la planificación ---
        insertar("periodos_jornada", [{"persona_id": f["PersonaId"], "it": f["IT"],
                                       "desde": str(f["PeriodoInicio"])[:10], "hasta": str(f["PeriodoFin"])[:10],
                                       "cargo": f["Cargo"], "cod_esp": f["CodEsp"],
                                       "horas_colacion": f["HorasColacion"] or 0,
                                       "dias_semana": None if f["DiasSemana"] is None else int(f["DiasSemana"]),
                                       "fila_excel": f["FilaExcel"]} for f in filas_plan])
        periodo_de_fila = {f["FilaExcel"]: (str(f["PeriodoInicio"])[:10], str(f["PeriodoFin"])[:10]) for f in filas_plan}

        # --- Asignaciones por profesional ---
        id_asig = {n: i for n, i in c.execute(text("SELECT nombre, asignacion_id FROM asignaciones_catalogo"))}
        asignaciones = []
        for f in _filas(E["Asignaciones"]):
            desde, hasta = periodo_de_fila[f["FilaExcel"]]
            asignaciones.append({
                "persona_id": f["PersonaId"], "it": f["IT"],
                "asignacion_id": id_asig.get(f["Asignacion"]),   # «(sin nombre)» queda sin catálogo
                "horas_semanales": f["Horas"] or 0,              # sin horas en el Excel = 0 (así calcula el Excel)
                "vigente_desde": desde, "vigente_hasta": hasta,
                "estado": "PENDIENTE" if f["Columna"] == "POR_AUTORIZAR" else "NO_REQUIERE",
            })
        insertar("asignaciones_profesional", asignaciones)

        # --- Ausencias en semanas por mes ---
        insertar("ausencias_mes", [{"persona_id": persona, "it": it, "periodo": _periodo(mes), "tipo": tipo,
                                    "semanas": semanas}
                                   for (persona, it, mes, tipo), semanas in
                                   E["Ausencias"].groupby(["PersonaId", "IT", "Mes", "Tipo"])["Semanas"].sum().items()])

        # --- Días adicionales del año ---
        insertar("dias_adicionales", [{"persona_id": persona, "it": it, "anio": 2026, "tipo": tipo[:60], "dias": dias}
                                      for (persona, it, tipo), dias in
                                      E["DiasAdicionales"].groupby(["PersonaId", "IT", "Tipo"])["Dias"].sum().items()])

        # --- Semanas hábiles (una jornada partida tiene dos filas: se suman, solo una es distinta de 0) ---
        insertar("semanas_habiles", [{"persona_id": persona, "it": it, "periodo": _periodo(mes), "semanas": semanas}
                                     for (persona, it, mes), semanas in
                                     E["SemanasHabiles"].groupby(["PersonaId", "IT", "Mes"])["SemanasHabiles"].sum().items()])

        # --- Reparto multi-instituto ---
        insertar("reparto_multi_instituto", [{"persona_id": f["PersonaId"], "it": f["IT"], "periodo": _periodo(f["Mes"]),
                                              "horas_semanales": f["HorasSemanales"]}
                                             for f in _filas(E["MultiInstituto"])])

        # --- Ajustes manuales del Excel (sin autorización conocida: quedan PENDIENTE y generan alerta) ---
        insertar("ajustes_parametro", [{"persona_id": f["PersonaId"], "it": f["IT"], "campo": CAMPOS_AJUSTE[f["Campo"]],
                                        "valor_estandar": f["ValorTabla"], "valor": f["ValorExcel"],
                                        "vigente_desde": periodo_de_fila[f["FilaExcel"]][0],
                                        "vigente_hasta": periodo_de_fila[f["FilaExcel"]][1],
                                        "motivo": "Ajuste del Excel de planificación sin explicación",
                                        "estado": "PENDIENTE"} for f in _filas(E["AjustesManuales"])])
    return conteo


if __name__ == "__main__":
    resultado = cargar()
    for tabla, n in resultado.items():
        print(f"{tabla:<28} {n}")

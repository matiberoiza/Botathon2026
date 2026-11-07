"""
Motor de cálculo de la planificación (reglas de negocio RN-05 a RN-18).

Para cada período de jornada (profesional + instituto + período) y cada mes:

  1. Horas del mes: del reparto multi-instituto si existe (RN-19); si no, de BUK.
     Los meses sin reporte se proyectan con el último mes conocido, dentro de la vigencia (RN-06).
  2. Promedio truncado de las horas de los meses vigentes del período → tramo (RN-07).
  3. % directo, indirecto y NAS por cargo y tramo; minutos por cargo (RN-09). Ajustes manuales encima.
  4. Horas disponibles = horas − colación (RN-08).
  5. NAS base = % NAS × promedio truncado (RN-10); se le suman las asignaciones (RN-11).
  6. Lo que queda se reparte entre directa e indirecta en proporción (RN-12).
  7. Atenciones semanales con redondeo hacia abajo (RN-13) y atención grupal (RN-14).
  8. × semanas hábiles del mes, redondeo hacia abajo (RN-15, RN-16) → meta mensual (RN-17) → FOJA (RN-18).

Ningún porcentaje, minuto ni hora está escrito aquí: todo sale de las tablas de parámetros.
Uso por línea de comandos:  python -m backend.app.motor
"""

import math
from collections import defaultdict

import pandas as pd
from sqlalchemy import text

from .db import obtener_engine

EPS = 1e-9  # tolerancia para que 151,99999 no se redondee a 151 por la aritmética de decimales


def piso(x: float) -> int:
    """Redondeo hacia abajo, como REDONDEAR.MENOS del Excel."""
    return math.floor(x + EPS)


def _periodo(mes: int) -> str:
    return f"2026-{mes:02d}-01"


def _leer(c, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), c)


def calcular(motivo: str, usuario: str, carga_buk_id: int | None = None, es_simulacion: bool = False) -> int:
    """Calcula todos los profesionales y meses, y guarda una versión nueva. Devuelve su version_id."""
    engine = obtener_engine()
    with engine.begin() as c:
        version_id = c.execute(text(
            "INSERT INTO versiones_calculo (motivo, usuario, carga_buk_id, es_simulacion) "
            "VALUES (:m, :u, :c, :s) RETURNING version_id"),
            {"m": motivo, "u": usuario, "c": carga_buk_id, "s": int(es_simulacion)}).scalar()

    try:
        with engine.connect() as c:
            filas = _calcular_filas(c, version_id)
        with engine.begin() as c:
            if filas:
                columnas = list(filas[0])
                c.execute(text(f"INSERT INTO resultados_planificacion ({', '.join(columnas)}) VALUES "
                               f"({', '.join(':' + x for x in columnas)})"), filas)
            c.execute(text("UPDATE versiones_calculo SET estado = 'PUBLICADA' WHERE version_id = :v"), {"v": version_id})
    except Exception:
        # Si falla, la versión queda FALLIDA y sigue vigente la última PUBLICADA
        with engine.begin() as c:
            c.execute(text("UPDATE versiones_calculo SET estado = 'FALLIDA' WHERE version_id = :v"), {"v": version_id})
        raise
    return version_id


def _calcular_filas(c, version_id: int) -> list[dict]:
    # ---------- Parámetros ----------
    parametros = dict(c.execute(text("SELECT clave, valor FROM parametros")).all())
    meta_pct = float(parametros["META_PCT"])
    tramos = _leer(c, "SELECT tramo, horas_desde, horas_hasta FROM tramos ORDER BY horas_desde DESC")
    distribucion = {(r.cargo, r.tramo): (r.pct_directa, r.pct_indirecta, r.pct_nas)
                    for r in _leer(c, "SELECT * FROM distribucion_cargo ORDER BY vigente_desde").itertuples()}
    minutos = {r.cargo: (r.min_directa, r.min_indirecta) for r in _leer(c, "SELECT * FROM cargos").itertuples()}
    grupo_it = dict(c.execute(text("SELECT it, grupo_factor_grupal FROM institutos")).all())
    grupal = {(r.cod_esp, r.grupo_instituto): (r.pct_grupal, r.pacientes_por_grupo)
              for r in _leer(c, "SELECT * FROM factor_grupal").itertuples()}
    semanas_mes = dict(c.execute(text("SELECT periodo, semanas FROM calendario_mes")).all())

    # ---------- Datos ----------
    contratos = _leer(c, "SELECT persona_id, it, periodo, cargo, horas_semanales, fecha_termino, estado_calidad, motivo "
                         "FROM contratos_mes WHERE persona_id IS NOT NULL")
    horas_buk = {(r.persona_id, r.it, r.periodo): r for r in contratos.itertuples()}
    ultimo_buk = contratos.sort_values("periodo").groupby(["persona_id", "it"]).last()
    reparto = {(r.persona_id, r.it, r.periodo): r.horas_semanales
               for r in _leer(c, "SELECT * FROM reparto_multi_instituto").itertuples()}
    con_reparto = {(p, i) for p, i, _ in reparto}
    semhab = {(r.persona_id, r.it, r.periodo): r.semanas for r in _leer(c, "SELECT * FROM semanas_habiles").itertuples()}
    asignaciones = defaultdict(list)
    for r in _leer(c, "SELECT * FROM asignaciones_profesional").itertuples():
        asignaciones[(r.persona_id, r.it)].append(r)
    ajustes = defaultdict(list)
    for r in _leer(c, "SELECT * FROM ajustes_parametro").itertuples():
        ajustes[(r.persona_id, r.it)].append(r)
    periodos = _leer(c, "SELECT * FROM periodos_jornada ORDER BY persona_id, it, desde")
    periodos["estimado"] = False
    # Profesionales nuevos (altas) que no están en la planificación: se planifican desde su primer contrato,
    # con el cargo de BUK, sin colación ni asignaciones, y con las semanas del calendario (queda en ALERTA).
    con_periodo = set(zip(periodos.persona_id, periodos.it))
    cod_de_cargo = {r.cargo: r.cod_esp for r in _leer(c, "SELECT cargo, cod_esp FROM cargos").itertuples()}
    nuevos = [{"persona_id": p, "it": i, "desde": g.periodo.min(), "hasta": "2026-12-31",
               "cargo": g.sort_values("periodo").cargo.iloc[0], "cod_esp": cod_de_cargo.get(g.sort_values("periodo").cargo.iloc[0]),
               "horas_colacion": 0.0, "estimado": True}
              for (p, i), g in contratos.groupby(["persona_id", "it"]) if (p, i) not in con_periodo]
    if nuevos:
        periodos = pd.concat([periodos, pd.DataFrame(nuevos)], ignore_index=True)

    def tramo_de(x: float) -> str:
        for t in tramos.itertuples():
            if x >= t.horas_desde and (t.horas_hasta is None or pd.isna(t.horas_hasta) or x < t.horas_hasta):
                return t.tramo
        return tramos.iloc[-1].tramo

    resultados = []
    for pj in periodos.itertuples():
        clave = (pj.persona_id, pj.it)
        meses = [m for m in range(1, 13) if pj.desde[:7] <= _periodo(m)[:7] <= pj.hasta[:7]]

        # 1. Horas de cada mes y su origen
        horas, origen, alertas_contrato, cargo_mes = {}, {}, [], {}
        for m in meses:
            per = _periodo(m)
            if clave in con_reparto:
                # 0 horas en el reparto = ese mes no trabaja en este instituto (no cuenta para el promedio)
                if reparto.get((pj.persona_id, pj.it, per), 0) > 0:
                    horas[m], origen[m] = reparto[(pj.persona_id, pj.it, per)], "REAL"
            elif (pj.persona_id, pj.it, per) in horas_buk:
                ct = horas_buk[(pj.persona_id, pj.it, per)]
                horas[m], origen[m], cargo_mes[m] = ct.horas_semanales, "REAL", ct.cargo
                if ct.estado_calidad in ("ALERTA", "PENDIENTE") and ct.motivo:
                    alertas_contrato.append(ct.motivo)
            elif clave in ultimo_buk.index:
                ultimo = ultimo_buk.loc[clave]
                termino = ultimo.fecha_termino
                if per > ultimo.periodo and (termino is None or pd.isna(termino) or termino >= per):
                    horas[m], origen[m], cargo_mes[m] = ultimo.horas_semanales, "PROYECCION", ultimo.cargo
        if not horas:
            continue

        # 2. Promedio truncado y tramo (solo los meses vigentes de este período)
        promedio = math.trunc(sum(horas.values()) / len(horas) + EPS)
        tramo = tramo_de(promedio)

        # 3. Ajustes manuales vigentes en el período (se aplican encima de la tabla de cada mes)
        motivos = list(dict.fromkeys(alertas_contrato))
        estado = "ALERTA" if motivos else "VALIDO"
        if pj.estimado:
            motivos.append("Profesional nuevo: semanas hábiles estimadas con el calendario")
            estado = "ALERTA"
        ajustes_vigentes = {}
        for aj in ajustes.get(clave, []):
            if aj.vigente_desde <= pj.hasta and (aj.vigente_hasta is None or aj.vigente_hasta >= pj.desde):
                ajustes_vigentes[aj.campo] = aj.valor
                if aj.estado != "APROBADO":
                    motivos.append(f"Ajuste manual sin autorización ({aj.campo})")
                    estado = "ALERTA"

        # 5. Asignaciones del período
        horas_asig = 0.0
        for a in asignaciones.get(clave, []):
            if a.vigente_desde <= pj.hasta and (a.vigente_hasta is None or a.vigente_hasta >= pj.desde):
                horas_asig += a.horas_semanales
                if a.asignacion_id is None or pd.isna(a.asignacion_id):
                    motivos.append("Asignación sin nombre")
                    estado = "ALERTA" if estado == "VALIDO" else estado
                if a.estado == "PENDIENTE":
                    motivos.append("Asignación por autorizar (DMN)")
                    estado = "PENDIENTE"
        grupo = grupal.get((pj.cod_esp, grupo_it.get(pj.it, "OTROS")))

        for m in meses:
            if m not in horas:
                continue
            per = _periodo(m)
            hs = horas[m]
            cargo = cargo_mes.get(m, pj.cargo)                          # el cargo que informa BUK ese mes
            if (cargo, tramo) not in distribucion:
                continue  # cargo sin parámetros: ya quedó EXCLUIDO al recibir la carga
            p_dir, p_ind, p_nas = distribucion[(cargo, tramo)]          # 3. % por cargo y tramo
            min_dir, min_ind = minutos[cargo]
            p_dir = ajustes_vigentes.get("PCT_DIRECTA", p_dir)
            p_ind = ajustes_vigentes.get("PCT_INDIRECTA", p_ind)
            p_nas = ajustes_vigentes.get("PCT_NAS", p_nas)
            min_dir = ajustes_vigentes.get("MIN_DIRECTA", min_dir)
            min_ind = ajustes_vigentes.get("MIN_INDIRECTA", min_ind)
            nas_base = p_nas * promedio                                 # 5. NAS base
            ad = hs - (pj.horas_colacion or 0)                          # 4. horas disponibles
            if pj.estimado:
                sem = semanas_mes.get(per, 0.0)
            else:
                sem = semhab.get((pj.persona_id, pj.it, per), 0.0)
            motivos_mes = list(motivos)
            estado_mes = estado
            if ad <= 0 or nas_base + horas_asig > ad:
                f_nas = f_dir = f_ind = None
                h_dir = h_ind = 0.0
                ate_dir = ate_ind = 0
                if ad < 0 or nas_base + horas_asig > ad > 0:
                    motivos_mes.append("Horas insuficientes para el NAS y las asignaciones")
                    estado_mes = "ALERTA" if estado_mes == "VALIDO" else estado_mes
            else:
                f_nas = (nas_base + horas_asig) / ad                    # 5. % NAS final
                asistencial = 1 - f_nas
                f_dir = asistencial * p_dir / (p_dir + p_ind) if p_dir + p_ind else 0.0   # 6. reparto proporcional
                f_ind = asistencial * p_ind / (p_dir + p_ind) if p_dir + p_ind else 0.0
                h_dir, h_ind = ad * f_dir, ad * f_ind
                ate_dir = piso(h_dir * 60 / min_dir)                     # 7. atenciones semanales
                ate_ind = piso(h_ind * 60 / min_ind)
            ate_dir_grupo = ate_dir * (1 - grupo[0]) + ate_dir * grupo[0] * grupo[1] if grupo else float(ate_dir)

            plan_dir = piso(ate_dir_grupo * sem)                         # 8. atenciones del mes
            plan_tot = piso((ate_dir_grupo + ate_ind) * sem)
            horas_contratadas = hs * semanas_mes.get(per, 0)
            horas_dir_mes = h_dir * sem
            foja = horas_dir_mes / horas_contratadas if horas_contratadas > 0 else None

            resultados.append({
                "version_id": version_id, "persona_id": int(pj.persona_id), "vacante_id": None, "it": int(pj.it),
                "periodo": per, "cargo": cargo, "horas_semanales": hs, "promedio_horas": promedio, "tramo": tramo,
                "horas_disponibles_sem": ad, "nas_base_sem": nas_base, "horas_asignaciones_sem": horas_asig,
                "pct_nas_final": f_nas, "pct_directa_final": f_dir, "pct_indirecta_final": f_ind,
                "horas_directa_sem": h_dir, "horas_indirecta_sem": h_ind,
                "horas_nas_sem": (nas_base + horas_asig) if f_nas is not None else None,
                "atenciones_directa_sem": ate_dir_grupo, "atenciones_indirecta_sem": ate_ind,
                "semanas_habiles": sem, "horas_contratadas_mes": horas_contratadas, "horas_directa_mes": horas_dir_mes,
                "atenciones_directas_mes": plan_dir, "atenciones_total_mes": plan_tot,
                "meta_directa_mes": piso(plan_dir * meta_pct), "meta_total_mes": piso(plan_tot * meta_pct),
                "foja": foja,
                "estado_calidad": estado_mes, "origen_dato": origen[m],
                "estado_foja": "CALCULADO" if foja is not None else "NO_APLICA",
                "motivos": "; ".join(dict.fromkeys(motivos_mes)) or None,
            })
    return resultados


if __name__ == "__main__":
    print("Versión generada:", calcular(motivo="Cálculo manual", usuario="consola"))

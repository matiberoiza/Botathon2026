"""
Verifica que el motor reproduce el Excel de planificación.

En una base SQLite temporal: carga inicial → carga BUK simulada (como la enviaría Blue Prism) →
motor de cálculo → compara cada profesional, instituto y mes con la hoja Dotacion_Asistencial.

Informa:
  - los casos de prueba (deben coincidir exactamente);
  - la coincidencia estricta: meses en que coinciden los 4 resultados
    (atenciones directas, atenciones totales, meta directa y meta total);
  - la coincidencia por resultado y las diferencias que no estén entre las conocidas.

Uso (desde la carpeta del proyecto):
    python herramientas/verificar_motor.py
"""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "herramientas"))

# Casos de prueba con los valores del Excel: (persona, IT, mes) → (directas, totales, meta directa, meta total)
CASOS = {
    "Normal · 134561 · junio": ((134561, 131, 6), (155, 184, 139, 165)),
    "44 → 42 h · 117024 · enero": ((117024, 131, 1), (172, 205, 154, 184)),
    "44 → 42 h · 117024 · junio": ((117024, 131, 6), (163, 197, 146, 177)),
    "Multi-instituto · 134746 Coquimbo · junio": ((134746, 41, 6), (100, 130, 90, 117)),
    "Multi-instituto · 134746 Copiapó · junio": ((134746, 31, 6), (21, 25, 18, 22)),
    "Jornada partida · 137356 · marzo": ((137356, 22, 3), (96, 114, 86, 102)),
    "Jornada partida · 137356 · septiembre": ((137356, 22, 9), (118, 141, 106, 126)),
}
# Diferencias conocidas del Excel (ajustes manuales sin explicación), por fila de Dotacion_Asistencial
FILAS_CONOCIDAS = {130, 308, 318, 322, 382, 410, 411, 421, 422, 115, 140, 219, 257, 332, 359, 383, 384, 464, 18}
METAS_CONOCIDAS = {20: [3], 24: [3], 31: [3], 57: [3], 65: [3], 84: [3], 116: [3], 231: [3], 232: [3], 234: [3],
                   296: [3], 344: [3], 372: [3], 401: [3], 440: [3], 459: [3, 7], 130: list(range(1, 13))}


def esperado_del_excel() -> pd.DataFrame:
    from comun import leer_dotacion
    d = leer_dotacion()
    filas = []
    for r in d.itertuples():
        for m in range(1, 13):
            filas.append({"persona_id": r.PersonaId, "it": r.IT, "mes": m, "fila": r.FilaExcel,
                          "semhab": getattr(r, f"SemHab{m}"),
                          "dir": d.at[r.Index, f"PlanAteDir{m}"], "tot": d.at[r.Index, f"PlanAteDir+Ind{m}"],
                          "mdir": d.at[r.Index, f"MG_AteDir{m}"], "mtot": d.at[r.Index, f"MG_AteDir+Ind{m}"]})
    e = pd.DataFrame(filas)
    # Una jornada partida tiene dos filas: en cada mes solo una tiene semanas hábiles
    e = e.sort_values("semhab", ascending=False).groupby(["persona_id", "it", "mes"], as_index=False).first()
    return e[e.semhab > 0]


def main():
    temporal = Path(tempfile.mkdtemp()) / "verificacion.db"
    os.environ["DB_RUTA"] = str(temporal)
    from backend.app import carga_inicial
    from backend.app.schemas import CargaBUK
    from backend.app.sincronizacion import procesar_carga_buk
    from backend.app.db import obtener_engine
    from simular_bot import construir_payload

    carga_inicial.cargar()
    respuesta = procesar_carga_buk(CargaBUK.model_validate(construir_payload("VERIFICACION")), usuario="verificador")
    print("Carga:", respuesta)

    res = pd.read_sql(f"SELECT persona_id, it, periodo, atenciones_directas_mes AS dir, atenciones_total_mes AS tot, "
                      f"meta_directa_mes AS mdir, meta_total_mes AS mtot, estado_calidad FROM resultados_planificacion "
                      f"WHERE version_id = {respuesta['version_id']}", obtener_engine())
    res["mes"] = res.periodo.str[5:7].astype(int)
    res = res.groupby(["persona_id", "it", "mes"], as_index=False)[["dir", "tot", "mdir", "mtot"]].sum()

    esp = esperado_del_excel()
    cmp = esp.merge(res, on=["persona_id", "it", "mes"], how="left", suffixes=("_x", "_m")).fillna(-1)
    for k in ("dir", "tot", "mdir", "mtot"):
        cmp[f"ok_{k}"] = cmp[f"{k}_x"] == cmp[f"{k}_m"]
    cmp["ok"] = cmp[[f"ok_{k}" for k in ("dir", "tot", "mdir", "mtot")]].all(axis=1)

    print("\n=== Casos de prueba ===")
    todos = True
    for nombre, (clave, valores) in CASOS.items():
        f = cmp[(cmp.persona_id == clave[0]) & (cmp.it == clave[1]) & (cmp.mes == clave[2])]
        obtenido = tuple(int(f[f"{k}_m"].iloc[0]) for k in ("dir", "tot", "mdir", "mtot")) if len(f) else None
        ok = obtenido == valores
        todos &= ok
        print(f"{'OK   ' if ok else 'FALLA'} {nombre}: esperado {valores}, obtenido {obtenido}")

    conocida = cmp.fila.isin(FILAS_CONOCIDAS) | cmp.apply(lambda r: r.mes in METAS_CONOCIDAS.get(r.fila, []), axis=1)
    print("\n=== Coincidencia con el Excel (meses con semanas hábiles) ===")
    print(f"Meses comparados: {len(cmp)}")
    print(f"Estricta total: {cmp.ok.mean():.1%}")
    print(f"Estricta sin diferencias conocidas: {cmp[~conocida].ok.mean():.1%}  ({(~conocida).sum()} meses)")
    for k, nombre in (("dir", "atenciones directas"), ("tot", "atenciones totales"), ("mdir", "meta directa"), ("mtot", "meta total")):
        print(f"  {nombre:<20} {cmp[f'ok_{k}'].mean():.1%}")
    nuevas = cmp[~cmp.ok & ~conocida]
    print(f"\nDiferencias no conocidas: {len(nuevas)} meses en {nuevas.fila.nunique()} filas del Excel")
    if len(nuevas):
        print(nuevas.groupby("fila").size().sort_values(ascending=False).head(15).to_string())
    return todos


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

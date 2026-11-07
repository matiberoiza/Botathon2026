"""
Pruebas del backend de punta a punta, con una base SQLite temporal (ver conftest.py):
carga inicial → carga BUK simulada (como la enviaría Blue Prism) → cálculo → dashboard.

Ejecutar desde la carpeta del proyecto:
    python -m pytest backend/tests -v
Se saltan si faltan los Excel del kit o los archivos generados (los datos no se suben a git).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

RAIZ = Path(__file__).resolve().parents[2]
HAY_DATOS = (RAIZ / "data" / "raw" / "Nac - Base contratos x mes.xlsx").exists() and \
            (RAIZ / "data" / "generados" / "parametros.xlsx").exists()
requiere_datos = pytest.mark.skipif(not HAY_DATOS, reason="faltan los Excel del kit o los archivos generados")


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:  # al entrar se ejecuta el arranque: crea la base y la carga inicial
        yield c


@pytest.fixture(scope="module")
def carga(cliente):
    from simular_bot import construir_payload
    payload = construir_payload("PRUEBA-1")
    # Dos filas con problemas: una con cargo desconocido y otra con horas negativas
    payload["contratos"].append({**payload["contratos"][0], "Cargo": "CARGO INVENTADO"})
    payload["contratos"].append({**payload["contratos"][1], "HorasSemanales": -10})
    respuesta = cliente.post("/api/v1/buk/sync", json=payload)
    assert respuesta.status_code == 200, respuesta.text
    return payload, respuesta.json()


def test_salud(cliente):
    datos = cliente.get("/api/salud").json()
    assert datos["api"] == "ok" and datos["base_datos_conectada"] is True


@requiere_datos
def test_carga_aisla_las_filas_invalidas(carga):
    _, r = carga
    assert r["estado"] == "ACEPTADA"
    assert r["conteos"]["validas"] == 3123      # las 3.123 filas reales del BUK
    assert r["conteos"]["excluidas"] == 2       # las dos filas con problemas, sin rechazar el resto


@requiere_datos
def test_reintento_no_duplica(cliente, carga):
    payload, primera = carga
    segunda = cliente.post("/api/v1/buk/sync", json=payload).json()
    assert segunda["repetida"] is True and segunda["carga_id"] == primera["carga_id"]


@requiere_datos
@pytest.mark.parametrize("persona, it, mes, esperado", [
    (134561, 131, 6, (155, 184, 139, 165)),    # normal
    (117024, 131, 1, (172, 205, 154, 184)),    # 44 h en enero
    (117024, 131, 6, (163, 197, 146, 177)),    # 42 h en junio
    (134746, 41, 6, (100, 130, 90, 117)),      # multi-instituto: Coquimbo
    (134746, 31, 6, (21, 25, 18, 22)),         # multi-instituto: Copiapó
    (137356, 22, 3, (96, 114, 86, 102)),       # jornada partida: período de 20 h
    (137356, 22, 9, (118, 141, 106, 126)),     # jornada partida: período de 30 h
])
def test_casos_coinciden_con_el_excel(cliente, carga, persona, it, mes, esperado):
    filas = [f for f in cliente.get(f"/api/v1/profesionales?it={it}&mes={mes}").json() if f["persona_id"] == persona]
    assert len(filas) == 1
    f = filas[0]
    assert (f["atenciones_directas_mes"], f["atenciones_total_mes"], f["meta_directa_mes"], f["meta_total_mes"]) == esperado


@requiere_datos
def test_dashboard(cliente, carga):
    k = cliente.get("/api/v1/dashboard/kpis?it=131&mes=6").json()
    assert k["profesionales"] > 0 and k["atenciones_planificadas"] > 0 and 0 < k["foja_promedio"] < 1
    institutos = cliente.get("/api/v1/dashboard/institutos?mes=6").json()
    assert {i["it"] for i in institutos} >= {11, 131}
    excepciones = cliente.get("/api/v1/excepciones").json()
    assert len(excepciones["errores_carga"]) == 2 and excepciones["alertas_agrupadas"]


@requiere_datos
def test_cambiar_meta_recalcula(cliente, carga):
    antes = cliente.get("/api/v1/dashboard/kpis").json()
    r = cliente.put("/api/v1/parametros/META_PCT", json={"valor": "0.85", "motivo": "prueba", "usuario": "qa"})
    assert r.status_code == 200 and r.json()["version_id"] > antes["version_id"]
    despues = cliente.get("/api/v1/dashboard/kpis").json()
    assert despues["meta_gestion"] < antes["meta_gestion"]
    assert despues["atenciones_planificadas"] == antes["atenciones_planificadas"]
    assert cliente.put("/api/v1/parametros/META_PCT", json={"valor": "1.5", "motivo": "x", "usuario": "qa"}).status_code == 400


@requiere_datos
def test_detecta_cambios_y_ajusta_la_planificacion(cliente, carga):
    """Un BUK nuevo con cambios: se identifican y la planificación se ajusta desde que rigen."""
    from simular_bot import aplicar_cambios_demo
    payload, _ = carga
    r = cliente.post("/api/v1/buk/sync", json=aplicar_cambios_demo(payload)).json()
    assert r["cambios"]["ALTA"] >= 1 and r["cambios"]["BAJA"] >= 1 and r["cambios"]["MODIFICACION"] >= 2

    cambios = cliente.get("/api/v1/cambios").json()["cambios"]
    def hay(persona, tipo, campo=None, desde=None):
        return any(c["persona_id"] == persona and c["tipo_cambio"] == tipo and (campo is None or c["campo"] == campo)
                   and (desde is None or c["vigente_desde"] == desde) for c in cambios)
    assert hay(999001, "ALTA", desde="2026-07-01")                               # alta en julio
    assert hay(71027, "BAJA")                                                     # deja de aparecer
    assert hay(134561, "MODIFICACION", "Horas semanales", "2026-07-01")           # 40 → 30 h desde julio
    assert hay(117024, "MODIFICACION", "Cargo", "2026-07-01")                     # cambio de cargo desde julio

    julio = {(f["persona_id"]): f for f in cliente.get("/api/v1/profesionales?it=131&mes=7").json()}
    assert 999001 in julio and julio[999001]["atenciones_total_mes"] > 0         # el nuevo ya se planifica
    assert julio[134561]["horas_semanales"] == 30                                 # la nueva jornada rige en julio
    assert julio[117024]["cargo"] == "TERAPEUTA OCUPACIONAL"
    junio = {(f["persona_id"]): f for f in cliente.get("/api/v1/profesionales?it=131&mes=6").json()}
    assert junio[117024]["cargo"] == "KINESIOLOGO"                                # antes de julio no cambia
    pmo = {f["persona_id"] for f in cliente.get("/api/v1/profesionales?it=101").json()}
    assert 71027 not in pmo                                                       # la baja ya no se planifica

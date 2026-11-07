"""Regresiones con datos sintéticos y SQLite temporal; no requieren los Excel privados."""

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app import config, db, motor
from backend.app.main import app


def consultar(sql, valores=None):
    with db.obtener_engine().connect() as c:
        return [dict(f) for f in c.execute(text(sql), valores or {}).mappings()]


def ejecutar(sql, valores=None):
    with db.obtener_engine().begin() as c:
        c.execute(text(sql), valores or {})


def resultados(persona=900001, mes=1):
    return consultar("SELECT * FROM resultados_planificacion WHERE version_id = "
                     "(SELECT max(version_id) FROM versiones_calculo WHERE estado='PUBLICADA') "
                     "AND persona_id=:p AND periodo=:m", {"p": persona, "m": f"2026-{mes:02d}-01"})


@pytest.fixture
def sistema(tmp_path, monkeypatch):
    db.reiniciar_engine()
    monkeypatch.setattr(config, "DB_RUTA", tmp_path / "regresion.db")
    db.crear_tablas_si_no_existen()
    ejecutar("INSERT INTO institutos (it, abreviatura, nombre) VALUES (131, 'TEST', 'Prueba')")
    ejecutar("INSERT INTO cargos (cargo, min_directa, min_indirecta) VALUES ('A', 30, 30), ('B', 60, 30)")
    ejecutar("INSERT INTO tramos (tramo, horas_desde) VALUES ('TEST', 0)")
    ejecutar("INSERT INTO distribucion_cargo (cargo, tramo, pct_directa, pct_indirecta, pct_nas) "
             "VALUES ('A', 'TEST', .7, .1, .2), ('B', 'TEST', .5, .3, .2)")
    ejecutar("INSERT INTO parametros (clave, valor, descripcion) VALUES ('META_PCT', '.9', 'Prueba')")
    ejecutar("INSERT INTO asignaciones_catalogo (asignacion_id, nombre) VALUES (1, 'Rol')")
    for p in (900001, 900002):
        ejecutar("INSERT INTO profesionales (persona_id) VALUES (:p)", {"p": p})
        ejecutar("INSERT INTO periodos_jornada (persona_id, it, desde, hasta, cargo) "
                 "VALUES (:p, 131, '2026-01-01', '2026-12-31', 'A')", {"p": p})
        for m in range(1, 13):
            ejecutar("INSERT INTO semanas_habiles (persona_id, it, periodo, semanas) VALUES (:p, 131, :m, 4)",
                     {"p": p, "m": f"2026-{m:02d}-01"})
    for m in range(1, 13):
        ejecutar("INSERT INTO calendario_mes (periodo, dias_habiles, semanas) VALUES (:m, 20, 4)",
                 {"m": f"2026-{m:02d}-01"})
    payload = {"ejecucion_id": "BASE", "contratos": [
        {"PersonaId": p, "IT": 131, "Periodo": f"2026-{m:02d}-01", "Cargo": "A",
         "HorasSemanales": 20 if p == 900002 and m == 1 else 40, "FechaIngreso": "2025-01-01"}
        for p in (900001, 900002) for m in (1, 7)]}
    # Sin lifespan: el fixture ya creó los catálogos; nunca importa archivos locales.
    cliente = TestClient(app)
    r = cliente.post("/api/v1/buk/sync", json=payload)
    assert r.status_code == 200, r.text
    try:
        yield cliente, payload
    finally:
        cliente.close()
        db.reiniciar_engine()


def enviar(sistema, **cambios):
    cliente, base = sistema
    payload = {**copy.deepcopy(base), "ejecucion_id": "CAMBIO", **cambios}
    r = cliente.post("/api/v1/buk/sync", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_parcial_conserva_contratos_y_no_inventa_bajas(sistema):
    r = enviar(sistema, contratos=[{**sistema[1]["contratos"][1], "HorasSemanales": 30}])
    assert resultados(900002, 7)[0]["horas_semanales"] == 40
    assert resultados(900002, 7)[0]["origen_dato"] == "REAL"
    assert len(consultar("SELECT * FROM contratos_mes WHERE periodo='2026-07-01'")) == 2
    assert r["cambios"]["BAJA"] == 0
    assert r["cambios"]["MODIFICACION"] == 1


@pytest.mark.parametrize("vacio", [False, True])
def test_cobertura_completa_da_baja_sin_resucitar_por_proyeccion(sistema, vacio):
    contratos = [] if vacio else [sistema[1]["contratos"][1]]
    r = enviar(sistema, contratos=contratos, periodos_completos=["2026-07-01"])
    assert r["cambios"]["BAJA"] == (2 if vacio else 1)
    assert resultados(900002, 1)
    assert not resultados(900002, 7)
    assert not resultados(900002, 8)


def test_fila_rechazada_en_completa_conserva_contrato_anterior(sistema):
    filas = [sistema[1]["contratos"][1], {**sistema[1]["contratos"][3], "HorasSemanales": -1}]
    r = enviar(sistema, contratos=filas, periodos_completos=["2026-07-01"])
    assert r["conteos"]["excluidas"] == 1 and r["cambios"]["BAJA"] == 0
    assert resultados(900002, 7)[0]["horas_semanales"] == 40


def test_completa_no_admite_exclusiones_sin_identificar(sistema):
    cliente, _ = sistema
    r = cliente.post("/api/v1/buk/sync", json={"ejecucion_id": "INSEGURA", "contratos": [],
                     "periodos_completos": ["2026-07-01"], "excluidos": [{"motivo": "Fila ilegible"}]})
    assert r.status_code == 422
    assert resultados(900002, 7)


@pytest.mark.parametrize("fechas,mes,existe", [
    ({"FechaTermino": "2026-06-30"}, 7, False),
    ({"FechaTermino": "2026-07-01"}, 7, True),
    ({"FechaTermino": "2026-07-01"}, 8, False),
    ({"FechaIngreso": "2026-08-01"}, 7, False),
    ({"FechaIngreso": "2026-07-31"}, 7, True),
])
def test_vigencia_en_filas_directas_y_proyeccion(sistema, fechas, mes, existe):
    enviar(sistema, contratos=[{**sistema[1]["contratos"][1], **fechas}])
    assert bool(resultados(mes=mes)) is existe


def test_vigencia_tambien_limita_reparto(sistema):
    enviar(sistema, contratos=[{**sistema[1]["contratos"][1], "FechaTermino": "2026-06-30"}],
           multi_instituto=[{"PersonaId": 900001, "IT": 131, "Periodo": "2026-07-01", "HorasSemanales": 20}])
    assert not resultados(mes=7)


@pytest.mark.parametrize("estado,horas", [("APROBADA", 2), ("PENDIENTE", 2), ("RECHAZADA", 0)])
def test_asignaciones_solo_durante_vigencia_y_no_rechazadas(sistema, estado, horas):
    ejecutar("INSERT INTO asignaciones_profesional (persona_id, it, asignacion_id, horas_semanales, "
             "vigente_desde, vigente_hasta, estado) VALUES (900001, 131, 1, 2, '2026-07-01', '2026-09-30', :e)",
             {"e": estado})
    motor.calcular("Asignación", "qa")
    assert resultados()[0]["horas_asignaciones_sem"] == 0
    assert resultados(mes=7)[0]["horas_asignaciones_sem"] == horas
    assert resultados(mes=10)[0]["horas_asignaciones_sem"] == 0
    if estado == "PENDIENTE":
        assert resultados(mes=7)[0]["estado_calidad"] == "PENDIENTE"
        assert resultados()[0]["estado_calidad"] == "VALIDO"


@pytest.mark.parametrize("estado,aplica", [("APROBADO", True), ("RECHAZADO", False)])
def test_ajustes_solo_en_mes_vigente(sistema, estado, aplica):
    enero, julio = resultados()[0], resultados(mes=7)[0]
    ejecutar("INSERT INTO ajustes_parametro (persona_id, it, campo, valor, vigente_desde, vigente_hasta, motivo, estado) "
             "VALUES (900001, 131, 'MIN_DIRECTA', 60, '2026-07-01', '2026-07-31', 'Prueba', :e)", {"e": estado})
    motor.calcular("Ajuste", "qa")
    assert resultados()[0]["atenciones_directas_mes"] == enero["atenciones_directas_mes"]
    assert (resultados(mes=7)[0]["atenciones_directas_mes"] < julio["atenciones_directas_mes"]) is aplica
    assert resultados(mes=8)[0]["atenciones_directas_mes"] == julio["atenciones_directas_mes"]


def test_semhab_ausente_se_excluye_y_se_informa(sistema):
    ejecutar("DELETE FROM semanas_habiles WHERE persona_id=900001 AND periodo='2026-01-01'")
    enviar(sistema)
    assert not resultados()
    assert resultados(mes=7)
    errores = sistema[0].get("/api/v1/excepciones").json()["errores_carga"]
    assert any(e["regla"] == "RN-15" and "2026-01-01" in e["detalle"] for e in errores)


def test_semhab_cero_explicito_es_valido(sistema):
    ejecutar("UPDATE semanas_habiles SET semanas=0 WHERE persona_id=900001 AND periodo='2026-01-01'")
    enviar(sistema)
    assert resultados()[0]["atenciones_total_mes"] == 0
    assert resultados()[0]["estado_calidad"] == "VALIDO"


def test_reparto_invalido_se_aisla_y_no_borra_otros_meses(sistema):
    valido = {"PersonaId": 900001, "IT": 131, "Periodo": "2026-07-01", "HorasSemanales": 20}
    enviar(sistema, ejecucion_id="REPARTO", multi_instituto=[valido])
    r = enviar(sistema, multi_instituto=[
        {**valido, "Periodo": "2026-08-01", "HorasSemanales": 10},
        {**valido, "IT": 999999}, {**valido, "HorasSemanales": "malo"},
        {**valido, "Periodo": "2026-07-02"}, {**valido, "PersonaId": []}])
    assert r["conteos"]["reparto_excluidas"] == 4
    assert r["conteos"]["validas"] == 4
    assert resultados(mes=7)[0]["horas_semanales"] == 20
    assert resultados(mes=8)[0]["horas_semanales"] == 10


def test_reintento_identico_y_conflicto_por_contenido(sistema):
    cliente, payload = sistema
    r = cliente.post("/api/v1/buk/sync", json=payload)
    assert r.status_code == 200 and r.json()["repetida"]
    diferente = copy.deepcopy(payload)
    diferente["contratos"][0]["HorasSemanales"] = 10
    r = cliente.post("/api/v1/buk/sync", json=diferente)
    assert r.status_code == 409
    assert resultados()[0]["horas_semanales"] == 40


def test_envios_concurrentes_no_duplican_version(sistema):
    cliente, base = sistema
    payload = {**base, "ejecucion_id": "CONCURRENTE"}
    with ThreadPoolExecutor(max_workers=2) as grupo:
        respuestas = list(grupo.map(lambda _: cliente.post("/api/v1/buk/sync", json=payload), range(2)))
    assert all(r.status_code == 200 for r in respuestas)
    assert sorted(r.json()["repetida"] for r in respuestas) == [False, True]
    assert len({r.json()["version_id"] for r in respuestas}) == 1
    assert len(consultar("SELECT * FROM cargas WHERE ejecucion_id='CONCURRENTE'")) == 1


def test_falla_revierte_carga_y_reintento_publica(sistema, monkeypatch):
    cliente, base = sistema
    antes = resultados()[0]
    payload = {**base, "ejecucion_id": "FALLA", "contratos": [{**base["contratos"][0], "HorasSemanales": 10}]}
    original = motor._calcular_filas

    def fallar(*_):
        raise RuntimeError("Falla forzada por la prueba")

    monkeypatch.setattr(motor, "_calcular_filas", fallar)
    r = cliente.post("/api/v1/buk/sync", json=payload)
    assert r.status_code == 503
    assert resultados()[0] == antes
    assert consultar("SELECT horas_semanales FROM contratos_mes WHERE persona_id=900001 AND periodo='2026-01-01'")[0]["horas_semanales"] == 40
    assert not consultar("SELECT * FROM cambios")
    assert consultar("SELECT estado FROM cargas WHERE ejecucion_id='FALLA'")[0]["estado"] == "RECHAZADA"
    assert cliente.get("/api/v1/buk/ultima-version").json()["ejecucion_id"] == "BASE"
    monkeypatch.setattr(motor, "_calcular_filas", original)
    r = cliente.post("/api/v1/buk/sync", json=payload)
    assert r.status_code == 200 and not r.json()["repetida"]
    assert resultados()[0]["horas_semanales"] == 10
    assert consultar("SELECT estado FROM versiones_calculo WHERE version_id=:v", {"v": r.json()["version_id"]})[0]["estado"] == "PUBLICADA"
    assert cliente.post("/api/v1/buk/sync", json=payload).json()["repetida"]


def test_migracion_conserva_datos_y_es_repetible(sistema):
    ejecutar("ALTER TABLE cargas DROP COLUMN hash_payload")
    ejecutar("ALTER TABLE cargas DROP COLUMN periodos_completos")
    assert db.crear_tablas_si_no_existen() is False
    assert db.crear_tablas_si_no_existen() is False
    assert len(consultar("SELECT * FROM contratos_mes")) == 4
    assert consultar("SELECT periodos_completos FROM cargas")[0]["periodos_completos"] == "[]"
    assert sistema[0].post("/api/v1/buk/sync", json=sistema[1]).status_code == 409


def test_reintento_fallido_no_pisa_carga_posterior(sistema, monkeypatch):
    cliente, base = sistema
    payload = {**base, "ejecucion_id": "ANTIGUA"}
    original = motor._calcular_filas

    def fallar(*_):
        raise RuntimeError("Falla forzada")

    monkeypatch.setattr(motor, "_calcular_filas", fallar)
    assert cliente.post("/api/v1/buk/sync", json=payload).status_code == 503
    monkeypatch.setattr(motor, "_calcular_filas", original)
    enviar(sistema, contratos=[{**base["contratos"][0], "HorasSemanales": 30}])
    assert cliente.post("/api/v1/buk/sync", json=payload).status_code == 409
    assert resultados()[0]["horas_semanales"] == 30

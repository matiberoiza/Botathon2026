"""
Recepción de la carga de BUK que envía Blue Prism (paso 17 a 21 del flujo general).

1. Si el ejecucion_id ya llegó, devuelve la carga existente (un reintento no duplica datos).
2. Valida cada contrato por separado (validación definitiva): forma, instituto, cargo, duplicados.
3. Compara con los contratos guardados y registra altas, bajas y modificaciones (RN-23).
4. Guarda contratos, reparto multi-instituto y errores, y deja la carga como ACEPTADA.
5. Ejecuta el motor de cálculo y devuelve la versión generada.
"""

from pydantic import ValidationError
from sqlalchemy import text

from .cambios import detectar
from .db import obtener_engine
from .motor import calcular
from .schemas import CargaBUK, ContratoBUK


def procesar_carga_buk(carga: CargaBUK, usuario: str = "bot") -> dict:
    engine = obtener_engine()
    with engine.begin() as c:
        existente = c.execute(text("SELECT carga_id, estado, filas_leidas, filas_validas, filas_excluidas, filas_alerta "
                                   "FROM cargas WHERE ejecucion_id = :e AND fuente = 'BUK'"),
                              {"e": carga.ejecucion_id}).first()
        if existente:
            version = c.execute(text("SELECT max(version_id) FROM versiones_calculo WHERE carga_buk_id = :c"),
                                {"c": existente.carga_id}).scalar()
            return {"carga_id": existente.carga_id, "estado": existente.estado, "repetida": True, "version_id": version,
                    "conteos": {"recibidas": existente.filas_leidas, "validas": existente.filas_validas,
                                "excluidas": existente.filas_excluidas, "alertas": existente.filas_alerta}}

        # Versión de referencia: la última carga BUK aceptada (para la trazabilidad de cambios)
        referencia = c.execute(text("SELECT max(carga_id) FROM cargas WHERE fuente = 'BUK' AND estado = 'ACEPTADA'")).scalar()
        carga_id = c.execute(text(
            "INSERT INTO cargas (ejecucion_id, fuente, archivo, hash_archivo, version_referencia, estado, enviado_por) "
            "VALUES (:e, 'BUK', :a, :h, :r, 'RECIBIDA', :u) RETURNING carga_id"),
            {"e": carga.ejecucion_id, "a": carga.archivo, "h": carga.hash_archivo, "r": referencia, "u": usuario}).scalar()

        institutos = {fila[0] for fila in c.execute(text("SELECT it FROM institutos"))}
        cargos = {fila[0] for fila in c.execute(text("SELECT cargo FROM cargos"))}
        especialidades = {fila[0] for fila in c.execute(text("SELECT cod_esp FROM especialidades"))}
        jornada = c.execute(text("SELECT vigente_desde, horas_maximas FROM jornada_legal ORDER BY vigente_desde")).all()

        def error(fila, persona, it, campo, valor, regla, severidad, detalle):
            c.execute(text("INSERT INTO errores_validacion (carga_id, fila, persona_id, it, campo, valor, regla, severidad, "
                           "detectado_por, detalle) VALUES (:c, :f, :p, :i, :ca, :v, :r, :s, 'BACKEND', :d)"),
                      {"c": carga_id, "f": fila, "p": persona, "i": it, "ca": campo, "v": None if valor is None else str(valor),
                       "r": regla, "s": severidad, "d": detalle})

        # Errores que ya detectó el bot
        for x in carga.excluidos:
            c.execute(text("INSERT INTO errores_validacion (carga_id, fila, persona_id, it, campo, valor, regla, severidad, "
                           "detectado_por, detalle) VALUES (:c, :f, :p, :i, :ca, :v, 'BOT', 'ERROR', 'BOT', :d)"),
                      {"c": carga_id, "f": x.fila, "p": x.PersonaId, "i": x.IT, "ca": x.campo, "v": x.valor, "d": x.motivo})

        validos, vistos, n_alertas, n_excluidos = [], set(), 0, len(carga.excluidos)
        rechazados = {(x.PersonaId, x.IT) for x in carga.excluidos}  # una fila rechazada no es una baja
        for numero, bruto in enumerate(carga.contratos, start=1):
            try:
                ct = ContratoBUK.model_validate(bruto)
            except ValidationError as e:
                n_excluidos += 1
                rechazados.add((bruto.get("PersonaId"), bruto.get("IT")))
                primer = e.errors()[0]
                error(numero, bruto.get("PersonaId"), bruto.get("IT"), ".".join(map(str, primer["loc"])),
                      primer.get("input"), "FORMATO", "ERROR", primer["msg"])
                continue
            clave = (ct.PersonaId, ct.IT, ct.Periodo)
            motivo = None
            if ct.IT not in institutos:
                motivo = ("IT", ct.IT, "INSTITUTO_DESCONOCIDO", "Instituto no está en el catálogo")
            elif ct.Cargo not in cargos:
                motivo = ("Cargo", ct.Cargo, "CARGO_SIN_PARAMETROS", "Cargo sin distribución por tramo")
            elif clave in vistos:
                motivo = ("PersonaId", ct.PersonaId, "DUPLICADO", "Registro repetido para PersonaId + IT + Periodo")
            elif ct.FechaTermino and ct.FechaIngreso and ct.FechaTermino < ct.FechaIngreso:
                motivo = ("FechaTermino", ct.FechaTermino, "FECHAS", "Fecha de término anterior a la de ingreso")
            if motivo or ct.estado == "EXCLUIDO":
                n_excluidos += 1
                rechazados.add((ct.PersonaId, ct.IT))
                campo, valor, regla, detalle = motivo or ("estado", "EXCLUIDO", "BOT", ct.motivo or "Excluido por el bot")
                error(numero, ct.PersonaId, ct.IT, campo, valor, regla, "ERROR", detalle)
                continue
            vistos.add(clave)
            estado, detalle = ct.estado, ct.motivo
            maximo = [h for desde, h in jornada if desde <= ct.Periodo.isoformat()]
            if maximo and ct.HorasSemanales > maximo[-1]:
                estado, detalle = "ALERTA", f"Horas sobre la jornada legal ({maximo[-1]:g} h)"
            if estado == "ALERTA":
                n_alertas += 1
            validos.append((ct, estado, detalle))

        # Profesionales: crear los nuevos y guardar el mes de nacimiento
        for ct, _, _ in validos:
            c.execute(text("INSERT INTO profesionales (persona_id, mes_nacimiento) VALUES (:p, :m) "
                           "ON CONFLICT (persona_id) DO UPDATE SET mes_nacimiento = coalesce(excluded.mes_nacimiento, mes_nacimiento)"),
                      {"p": ct.PersonaId, "m": ct.MesNacimiento})

        # Contratos: la carga nueva reemplaza los contratos BUK de los períodos que informa
        periodos = sorted({ct.Periodo.isoformat() for ct, _, _ in validos})
        anteriores = [dict(f) for f in c.execute(text(
            "SELECT persona_id, it, periodo, horas_semanales, cargo, tipo_contrato, fecha_termino FROM contratos_mes "
            "WHERE origen = 'BUK' AND persona_id IS NOT NULL")).mappings()]
        if periodos:
            c.execute(text(f"DELETE FROM contratos_mes WHERE origen = 'BUK' AND periodo IN ({', '.join(':p' + str(i) for i in range(len(periodos)))})"),
                      {f"p{i}": p for i, p in enumerate(periodos)})
        for ct, estado, detalle in validos:
            c.execute(text(
                "INSERT INTO contratos_mes (persona_id, it, periodo, cargo, cod_esp, centro_costo, tipo_contrato, tipo_trabajador, "
                "fecha_ingreso, fecha_termino, horas_semanales, dias_semana, origen, estado_calidad, motivo, carga_id) VALUES "
                "(:p, :i, :pe, :ca, :ce, :cc, :tc, :tt, :fi, :ft, :h, :d, 'BUK', :es, :mo, :c)"),
                {"p": ct.PersonaId, "i": ct.IT, "pe": ct.Periodo.isoformat(), "ca": ct.Cargo,
                 "ce": ct.CodEsp if ct.CodEsp in especialidades else None, "cc": ct.CentroCosto,
                 "tc": ct.TipoContrato, "tt": ct.TipoTrabajador,
                 "fi": ct.FechaIngreso.isoformat() if ct.FechaIngreso else None,
                 "ft": ct.FechaTermino.isoformat() if ct.FechaTermino else None,
                 "h": ct.HorasSemanales, "d": ct.DiasSemana, "es": estado, "mo": detalle, "c": carga_id})

        # Cambios respecto de la carga anterior (en la primera carga no hay con qué comparar)
        nuevos = [{"persona_id": ct.PersonaId, "it": ct.IT, "periodo": ct.Periodo.isoformat(),
                   "horas_semanales": ct.HorasSemanales, "cargo": ct.Cargo, "tipo_contrato": ct.TipoContrato,
                   "fecha_termino": ct.FechaTermino.isoformat() if ct.FechaTermino else None} for ct, _, _ in validos]
        cambios = detectar(anteriores, nuevos, rechazados)
        for cb in cambios:
            c.execute(text("INSERT OR IGNORE INTO profesionales (persona_id) VALUES (:p)"), {"p": cb["persona_id"]})
            c.execute(text("INSERT INTO cambios (tabla, persona_id, it, tipo_cambio, campo, valor_anterior, valor_nuevo, "
                           "vigente_desde, origen, carga_id, usuario, motivo) VALUES ('contratos_mes', :p, :i, :t, :ca, :a, :n, :v, "
                           "'BOT', :c, :u, 'Detectado al comparar con la carga BUK anterior')"),
                      {"p": cb["persona_id"], "i": cb["it"], "t": cb["tipo_cambio"], "ca": cb["campo"],
                       "a": cb["valor_anterior"], "n": cb["valor_nuevo"], "v": cb["vigente_desde"], "c": carga_id, "u": usuario})
        resumen_cambios = {t: sum(1 for cb in cambios if cb["tipo_cambio"] == t) for t in ("ALTA", "BAJA", "MODIFICACION")}

        # Reparto multi-instituto: reemplaza el de las personas informadas
        for persona in {r.PersonaId for r in carga.multi_instituto}:
            c.execute(text("DELETE FROM reparto_multi_instituto WHERE persona_id = :p"), {"p": persona})
            c.execute(text("INSERT OR IGNORE INTO profesionales (persona_id) VALUES (:p)"), {"p": persona})
        for r in carga.multi_instituto:
            c.execute(text("INSERT OR REPLACE INTO reparto_multi_instituto (persona_id, it, periodo, horas_semanales, carga_id) "
                           "VALUES (:p, :i, :pe, :h, :c)"),
                      {"p": r.PersonaId, "i": r.IT, "pe": r.Periodo.isoformat(), "h": r.HorasSemanales, "c": carga_id})

        conteos = {"recibidas": len(carga.contratos) + len(carga.excluidos), "validas": len(validos),
                   "excluidas": n_excluidos, "alertas": n_alertas}
        c.execute(text("UPDATE cargas SET estado = 'ACEPTADA', filas_leidas = :l, filas_validas = :v, filas_excluidas = :x, "
                       "filas_alerta = :a, cobertura_desde = :d, cobertura_hasta = :h WHERE carga_id = :c"),
                  {"l": conteos["recibidas"], "v": conteos["validas"], "x": n_excluidos, "a": n_alertas,
                   "d": periodos[0] if periodos else None, "h": periodos[-1] if periodos else None, "c": carga_id})

    version_id = calcular(motivo=f"Carga BUK {carga.ejecucion_id}", usuario=usuario, carga_buk_id=carga_id)
    return {"carga_id": carga_id, "estado": "ACEPTADA", "repetida": False, "conteos": conteos, "version_id": version_id,
            "cambios": resumen_cambios}

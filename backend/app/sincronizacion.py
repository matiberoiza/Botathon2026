"""
Recepción de la carga de BUK que envía Blue Prism (paso 17 a 21 del flujo general).

1. Verifica ejecucion_id y contenido: solo repite respuestas de cálculos publicados.
2. Valida cada contrato por separado (validación definitiva): forma, instituto, cargo, duplicados.
3. Compara con los contratos guardados y registra altas, bajas y modificaciones (RN-23).
4. Actualiza las claves recibidas; solo infiere bajas en meses declarados completos.
5. Guarda y calcula en una transacción: acepta la carga únicamente si publica su versión.
"""

import hashlib
import json
import logging

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text

from .cambios import detectar
from .db import obtener_engine
from .motor import calcular
from .schemas import CargaBUK, ContratoBUK, RepartoMultiInstituto

logger = logging.getLogger(__name__)


def _identificador(valor):
    """Un dato mal formado no debe romper el registro del error de esa misma fila."""
    try:
        return int(valor) if not isinstance(valor, (bool, float)) else None
    except (TypeError, ValueError, OverflowError):
        return None


def procesar_carga_buk(carga: CargaBUK, usuario: str = "bot") -> dict:
    huella = hashlib.sha256(json.dumps(carga.model_dump(mode="json"), sort_keys=True,
                                      separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    try:
        return _procesar(carga, usuario, huella)
    except HTTPException:
        raise
    except Exception:
        # La transacción ya se revirtió: ni contratos ni cambios ni resultados parciales quedan vigentes.
        logger.exception("Carga BUK revertida: %s", carga.ejecucion_id)
        with obtener_engine().begin() as c:
            c.execute(text("INSERT OR IGNORE INTO cargas (ejecucion_id, fuente, hash_payload, estado, enviado_por) "
                           "VALUES (:e, 'BUK', :h, 'RECHAZADA', :u)"),
                      {"e": carga.ejecucion_id, "h": huella, "u": usuario})
            carga_id = c.execute(text("SELECT carga_id FROM cargas WHERE ejecucion_id=:e AND fuente='BUK'"),
                                 {"e": carga.ejecucion_id}).scalar()
            c.execute(text("INSERT INTO versiones_calculo (motivo, usuario, carga_buk_id, estado) "
                           "VALUES ('Carga revertida; se puede reintentar', :u, :c, 'FALLIDA')"),
                      {"u": usuario, "c": carga_id})
        raise HTTPException(status_code=503, detail="No se pudo publicar el cálculo. La carga fue revertida; "
                            "reintente el mismo envío con el mismo ejecucion_id.") from None


def _procesar(carga: CargaBUK, usuario: str, huella: str) -> dict:
    engine = obtener_engine()
    with engine.begin() as c:
        # Serializa la comprobación de idempotencia y la escritura entre solicitudes concurrentes.
        c.exec_driver_sql("BEGIN IMMEDIATE")
        existente = c.execute(text("SELECT carga_id, estado, hash_payload, filas_leidas, filas_validas, filas_excluidas, filas_alerta "
                                   "FROM cargas WHERE ejecucion_id = :e AND fuente = 'BUK'"),
                              {"e": carga.ejecucion_id}).first()
        if existente:
            if existente.hash_payload is None:
                raise HTTPException(status_code=409, detail="Ejecución anterior sin huella verificable; use un ejecucion_id nuevo.")
            if existente.hash_payload != huella:
                raise HTTPException(status_code=409, detail="Ese ejecucion_id ya corresponde a otro contenido.")
            version = c.execute(text("SELECT max(version_id) FROM versiones_calculo WHERE carga_buk_id = :c AND estado = 'PUBLICADA'"),
                                {"c": existente.carga_id}).scalar()
            if existente.estado == "ACEPTADA" and version is not None:
                return {"carga_id": existente.carga_id, "estado": existente.estado, "repetida": True, "version_id": version,
                        "conteos": {"recibidas": existente.filas_leidas, "validas": existente.filas_validas,
                                    "excluidas": existente.filas_excluidas, "alertas": existente.filas_alerta}}
            posterior = c.execute(text("SELECT 1 FROM cargas WHERE fuente='BUK' AND estado='ACEPTADA' "
                                       "AND carga_id>:c LIMIT 1"), {"c": existente.carga_id}).scalar()
            if posterior:
                raise HTTPException(status_code=409, detail="Hay una carga aceptada posterior al intento fallido. "
                                    "Revise los datos actuales y use un ejecucion_id nuevo.")

        # Versión de referencia: la última carga BUK aceptada (para la trazabilidad de cambios)
        referencia = c.execute(text("SELECT max(carga_id) FROM cargas WHERE fuente = 'BUK' AND estado = 'ACEPTADA'")).scalar()
        carga_id = c.execute(text(
            "INSERT INTO cargas (ejecucion_id, fuente, archivo, hash_archivo, hash_payload, periodos_completos, version_referencia, estado, enviado_por) "
            "VALUES (:e, 'BUK', :a, :h, :hp, :pc, :r, 'RECIBIDA', :u) "
            "ON CONFLICT(ejecucion_id, fuente) DO UPDATE SET archivo=:a, hash_archivo=:h, periodos_completos=:pc, "
            "version_referencia=:r, estado='RECIBIDA' RETURNING carga_id"),
            {"e": carga.ejecucion_id, "a": carga.archivo, "h": carga.hash_archivo, "hp": huella,
             "pc": json.dumps([p.isoformat() for p in carga.periodos_completos]), "r": referencia, "u": usuario}).scalar()
        c.execute(text("DELETE FROM errores_validacion WHERE carga_id=:c"), {"c": carga_id})

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
                rechazados.add((_identificador(bruto.get("PersonaId")), _identificador(bruto.get("IT"))))
                primer = e.errors()[0]
                error(numero, _identificador(bruto.get("PersonaId")), _identificador(bruto.get("IT")), ".".join(map(str, primer["loc"])),
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

        # Sin cobertura explícita solo se reemplazan las claves recibidas.
        completos = {p.isoformat() for p in carga.periodos_completos}
        periodos = sorted({ct.Periodo.isoformat() for ct, _, _ in validos} | completos)
        anteriores = [dict(f) for f in c.execute(text(
            "SELECT persona_id, it, periodo, horas_semanales, cargo, tipo_contrato, fecha_ingreso, fecha_termino FROM contratos_mes "
            "WHERE origen = 'BUK' AND persona_id IS NOT NULL")).mappings()]
        # Si una exclusión no identifica a la persona/instituto, no es seguro inferir ninguna baja.
        if completos and any(p is None or i is None for p, i in rechazados):
            raise HTTPException(status_code=422, detail="Cobertura completa con exclusiones sin identificar: "
                                "corrija las filas o envíe la carga como parcial.")
        claves_validas = {(ct.PersonaId, ct.IT, ct.Periodo.isoformat()) for ct, _, _ in validos}
        for anterior in anteriores:
            p, i, per = anterior["persona_id"], anterior["it"], anterior["periodo"]
            if (p, i, per) in claves_validas or (per in completos and (p, i) not in rechazados):
                c.execute(text("DELETE FROM contratos_mes WHERE origen='BUK' AND persona_id=:p AND it=:i AND periodo=:pe"),
                          {"p": p, "i": i, "pe": per})
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
        nuevos = [dict(f) for f in c.execute(text(
            "SELECT persona_id, it, periodo, horas_semanales, cargo, tipo_contrato, fecha_ingreso, fecha_termino "
            "FROM contratos_mes WHERE origen='BUK' AND persona_id IS NOT NULL")).mappings() if f["periodo"] in periodos]
        cambios = detectar(anteriores, nuevos, rechazados, set(periodos))
        for cb in cambios:
            c.execute(text("INSERT OR IGNORE INTO profesionales (persona_id) VALUES (:p)"), {"p": cb["persona_id"]})
            c.execute(text("INSERT INTO cambios (tabla, persona_id, it, tipo_cambio, campo, valor_anterior, valor_nuevo, "
                           "vigente_desde, origen, carga_id, usuario, motivo) VALUES ('contratos_mes', :p, :i, :t, :ca, :a, :n, :v, "
                           "'BOT', :c, :u, 'Detectado al comparar con la carga BUK anterior')"),
                      {"p": cb["persona_id"], "i": cb["it"], "t": cb["tipo_cambio"], "ca": cb["campo"],
                       "a": cb["valor_anterior"], "n": cb["valor_nuevo"], "v": cb["vigente_desde"], "c": carga_id, "u": usuario})
        resumen_cambios = {t: sum(1 for cb in cambios if cb["tipo_cambio"] == t) for t in ("ALTA", "BAJA", "MODIFICACION")}

        # Reparto: valida y actualiza cada clave; una fila mala no elimina el reparto anterior.
        vistos_reparto, excluidos_reparto = set(), 0
        for numero, bruto in enumerate(carga.multi_instituto, start=1):
            try:
                r = RepartoMultiInstituto.model_validate(bruto)
                clave = (r.PersonaId, r.IT, r.Periodo)
                if r.IT not in institutos:
                    raise ValueError("Instituto no está en el catálogo")
                if clave in vistos_reparto:
                    raise ValueError("Registro multi-instituto duplicado")
            except (ValidationError, ValueError) as exc:
                excluidos_reparto += 1
                detalle = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
                error(numero, _identificador(bruto.get("PersonaId")), _identificador(bruto.get("IT")),
                      "multi_instituto", bruto.get("Periodo"), "REPARTO_INVALIDO", "ERROR", detalle)
                continue
            vistos_reparto.add(clave)
            c.execute(text("INSERT OR IGNORE INTO profesionales (persona_id) VALUES (:p)"), {"p": r.PersonaId})
            c.execute(text("INSERT OR REPLACE INTO reparto_multi_instituto (persona_id, it, periodo, horas_semanales, carga_id) "
                           "VALUES (:p, :i, :pe, :h, :c)"),
                      {"p": r.PersonaId, "i": r.IT, "pe": r.Periodo.isoformat(), "h": r.HorasSemanales, "c": carga_id})

        conteos = {"recibidas": len(carga.contratos) + len(carga.excluidos), "validas": len(validos),
                   "excluidas": n_excluidos, "alertas": n_alertas,
                   "reparto_validas": len(vistos_reparto), "reparto_excluidas": excluidos_reparto}
        c.execute(text("UPDATE cargas SET estado = 'ACEPTADA', filas_leidas = :l, filas_validas = :v, filas_excluidas = :x, "
                       "filas_alerta = :a, cobertura_desde = :d, cobertura_hasta = :h WHERE carga_id = :c"),
                  {"l": conteos["recibidas"], "v": conteos["validas"], "x": n_excluidos, "a": n_alertas,
                   "d": periodos[0] if periodos else None, "h": periodos[-1] if periodos else None, "c": carga_id})

        version_id = calcular(motivo=f"Carga BUK {carga.ejecucion_id}", usuario=usuario, carga_buk_id=carga_id, conexion=c)
    return {"carga_id": carga_id, "estado": "ACEPTADA", "repetida": False, "conteos": conteos, "version_id": version_id,
            "cambios": resumen_cambios}

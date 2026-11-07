"""
Detección de cambios entre dos cargas de BUK (RN-23).

Compara los contratos de la carga nueva con los que estaban guardados (la última carga aceptada)
y devuelve la lista de cambios, cada uno con la fecha desde la que rige:

  - ALTA: un profesional aparece en un instituto en el que no estaba.
  - BAJA: un profesional deja de aparecer en un instituto, o se le informa una fecha de término.
  - MODIFICACION: cambian las horas, el cargo, el tipo de contrato o la fecha de término en un mismo mes.
    Un traslado (baja en un instituto y alta en otro) se registra además como cambio de instituto.

Precauciones (para no inventar bajas):
  - Solo se comparan los meses que informa la carga nueva.
  - Una fila rechazada en la carga nueva no se interpreta como baja.
  - En la primera carga no hay nada con qué comparar: no se registran cambios.
"""

CAMPOS = {"horas_semanales": "Horas semanales", "cargo": "Cargo", "tipo_contrato": "Tipo de contrato",
          "fecha_termino": "Fecha de término", "fecha_ingreso": "Fecha de ingreso"}


def detectar(anteriores: list[dict], nuevos: list[dict], rechazados: set[tuple],
             periodos_comparados: set[str] | None = None) -> list[dict]:
    """anteriores / nuevos: contratos con persona_id, it, periodo y los campos de CAMPOS.
    rechazados: (persona_id, it) que vinieron con error en la carga nueva."""
    if not anteriores:
        return []
    periodos_nuevos = periodos_comparados if periodos_comparados is not None else {c["periodo"] for c in nuevos}
    ant = {(c["persona_id"], c["it"], c["periodo"]): c for c in anteriores if c["periodo"] in periodos_nuevos}
    nue = {(c["persona_id"], c["it"], c["periodo"]): c for c in nuevos}
    pares_ant = {(p, i) for p, i, _ in ant}
    pares_nue = {(p, i) for p, i, _ in nue}
    cambios = []

    def primer_mes(par, origen):
        return min(per for p, i, per in origen if (p, i) == par)

    # Altas y bajas por profesional + instituto
    altas = pares_nue - pares_ant
    bajas = {par for par in pares_ant - pares_nue if par not in rechazados}
    for persona, it in sorted(altas):
        cambios.append({"persona_id": persona, "it": it, "tipo_cambio": "ALTA", "campo": None,
                        "valor_anterior": None, "valor_nuevo": "Ingresa al instituto",
                        "vigente_desde": primer_mes((persona, it), nue)})
    for persona, it in sorted(bajas):
        cambios.append({"persona_id": persona, "it": it, "tipo_cambio": "BAJA", "campo": None,
                        "valor_anterior": "En el instituto", "valor_nuevo": "No aparece en el reporte nuevo",
                        "vigente_desde": primer_mes((persona, it), ant)})

    # Traslados: la misma persona sale de un instituto y entra a otro
    for persona in sorted({p for p, _ in altas} & {p for p, _ in bajas}):
        desde_it = sorted(i for p, i in bajas if p == persona)
        hacia_it = sorted(i for p, i in altas if p == persona)
        cambios.append({"persona_id": persona, "it": hacia_it[0], "tipo_cambio": "MODIFICACION", "campo": "Instituto",
                        "valor_anterior": ", ".join(map(str, desde_it)), "valor_nuevo": ", ".join(map(str, hacia_it)),
                        "vigente_desde": primer_mes((persona, hacia_it[0]), nue)})

    # Modificaciones en un mismo mes: se registra una vez por campo, desde el primer mes en que cambia
    vistos = set()
    for clave in sorted(ant.keys() & nue.keys(), key=lambda k: (k[0], k[1], k[2])):
        a, n = ant[clave], nue[clave]
        for campo, nombre in CAMPOS.items():
            va, vn = a.get(campo), n.get(campo)
            if campo == "horas_semanales" and va is not None and vn is not None:
                distinto = abs(float(va) - float(vn)) > 1e-9
            else:
                distinto = (va or None) != (vn or None)
            if not distinto or (clave[0], clave[1], campo, str(va), str(vn)) in vistos:
                continue
            vistos.add((clave[0], clave[1], campo, str(va), str(vn)))
            # Una fecha de término nueva es una baja programada
            tipo = "BAJA" if campo == "fecha_termino" and vn and not va else "MODIFICACION"
            cambios.append({"persona_id": clave[0], "it": clave[1], "tipo_cambio": tipo, "campo": nombre,
                            "valor_anterior": None if va is None else str(va),
                            "valor_nuevo": None if vn is None else str(vn),
                            "vigente_desde": vn if tipo == "BAJA" else clave[2]})
    return cambios

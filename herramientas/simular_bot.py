"""
Simula lo que hará Blue Prism: lee el Excel de BUK y la hoja Excepciones, normaliza y minimiza los
datos, arma el JSON del contrato de datos y lo envía a POST /api/v1/buk/sync.

Sirve para probar el backend sin la VM, y como referencia para Vicente de qué debe enviar el bot.

Uso (desde la carpeta del proyecto, con el backend levantado):
    python herramientas/simular_bot.py                       # envía a http://localhost:8000
    python herramientas/simular_bot.py http://IP:8000        # envía a otro computador
    python herramientas/simular_bot.py --guardar carga.json  # solo guarda el JSON, sin enviar
    python herramientas/simular_bot.py --cambios             # envía un BUK «nuevo» con altas, bajas y cambios
"""

import hashlib
import json
import sys
import urllib.request
from datetime import datetime

import pandas as pd

from comun import BUK, PLAN, abrir_plan


def _nulo(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):  # NaN o NaT de pandas
        return None
    if isinstance(v, str) and not v.strip():
        return None  # en BUK los vacíos vienen como texto ''
    return v


def _fecha(v):
    v = _nulo(v)
    return None if v is None else pd.Timestamp(v).date().isoformat()


def construir_payload(ejecucion_id: str | None = None) -> dict:
    """Arma el cuerpo de POST /api/v1/buk/sync a partir de los Excel del kit."""
    buk = pd.read_excel(BUK, sheet_name="Dotacion_2026", header=1, dtype={"Centro de Costo": str})
    contratos, excluidos = [], []
    for numero, f in enumerate(buk.to_dict("records"), start=3):  # los datos parten en la fila 3
        if _nulo(f["PersonaId"]) is None or _nulo(f["Cargo"]) is None:
            excluidos.append({"fila": numero, "PersonaId": _nulo(f["PersonaId"]), "campo": "PersonaId/Cargo",
                              "valor": "", "motivo": "PersonaId o Cargo vacío"})
            continue
        nacimiento = _nulo(f["Fecha de Nacimiento"])
        contratos.append({
            "PersonaId": int(f["PersonaId"]), "IT": int(f["IT"]), "Periodo": _fecha(f["Periodo"]),
            "Cargo": str(f["Cargo"]).strip(), "CodEsp": _nulo(f["Cod_Esp"]),
            "HorasSemanales": float(f["Horas Semanales"]),
            "TipoContrato": _nulo(f["Tipo de Contrato"]), "TipoTrabajador": _nulo(f["Tipo_Trabajador"]),
            "FechaIngreso": _fecha(f["Fecha Ingreso Compañía"]), "FechaTermino": _fecha(f["Fecha Término"]),
            "DiasSemana": int(f["Ndias"]) if _nulo(f["Ndias"]) is not None else None,
            "CentroCosto": int(f["Centro de Costo"]) if str(f["Centro de Costo"]).isdigit() else None,
            # Mínimo de datos: de la fecha de nacimiento solo se envía el mes
            "MesNacimiento": pd.Timestamp(nacimiento).month if nacimiento is not None else None,
            "estado": "VALIDO", "motivo": None,
        })

    # Hoja Excepciones: horas por instituto y mes (columnas K a V = enero a diciembre)
    hoja = abrir_plan()["Excepciones"]
    multi = [{"PersonaId": hoja.cell(r, 5).value, "IT": hoja.cell(r, 3).value, "Periodo": f"2026-{m:02d}-01",
              "HorasSemanales": hoja.cell(r, 10 + m).value}
             for r in range(3, 20) for m in range(1, 13) if hoja.cell(r, 10 + m).value is not None]

    return {
        "ejecucion_id": ejecucion_id or "SIM-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
        "archivo": BUK.name,
        "hash_archivo": hashlib.sha256(BUK.read_bytes()).hexdigest(),
        "conteos": {"leidas": len(buk), "validas": len(contratos), "excluidas": len(excluidos), "alertas": 0},
        "contratos": contratos, "excluidos": excluidos, "multi_instituto": multi,
        "periodos_completos": sorted({c["Periodo"] for c in contratos}),
    }


def aplicar_cambios_demo(payload: dict) -> dict:
    """Simula un reporte BUK nuevo con cambios, para la demo de detección de cambios:
       - 134561 baja de 40 a 30 horas desde julio (cambio de jornada);
       - 117024 pasa de kinesiólogo a terapeuta ocupacional desde julio (cambio de cargo);
       - 71027 deja de aparecer en el reporte (baja);
       - 999001 ingresa en julio a Santiago como kinesiólogo de 40 horas (alta)."""
    contratos = []
    for c in payload["contratos"]:
        c = dict(c)
        if c["PersonaId"] == 71027:
            continue
        if c["PersonaId"] == 134561 and c["Periodo"] >= "2026-07-01":
            c["HorasSemanales"] = 30.0
        if c["PersonaId"] == 117024 and c["Periodo"] >= "2026-07-01":
            c["Cargo"] = "TERAPEUTA OCUPACIONAL"
        contratos.append(c)
    contratos.append({"PersonaId": 999001, "IT": 131, "Periodo": "2026-07-01", "Cargo": "KINESIOLOGO", "CodEsp": "KI",
                      "HorasSemanales": 40.0, "TipoContrato": "Plazo fijo", "TipoTrabajador": "Titular",
                      "FechaIngreso": "2026-07-01", "FechaTermino": None, "DiasSemana": 5, "CentroCosto": None,
                      "MesNacimiento": None, "estado": "VALIDO", "motivo": None})
    nuevo = dict(payload, contratos=contratos, ejecucion_id=payload["ejecucion_id"] + "-CAMBIOS",
                 archivo="BUK con cambios (simulado)")
    nuevo["conteos"] = dict(payload["conteos"], leidas=len(contratos), validas=len(contratos))
    return nuevo


def enviar(url_base: str, payload: dict) -> dict:
    peticion = urllib.request.Request(url_base.rstrip("/") + "/api/v1/buk/sync", method="POST",
                                      data=json.dumps(payload).encode("utf-8"),
                                      headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=300) as respuesta:
        return json.loads(respuesta.read())


if __name__ == "__main__":
    argumentos = sys.argv[1:]
    payload = construir_payload()
    if "--cambios" in argumentos:  # reporte BUK «nuevo» con altas, bajas y cambios (para la demo)
        argumentos.remove("--cambios")
        payload = aplicar_cambios_demo(payload)
    print(f"Contratos: {len(payload['contratos'])} · excluidos: {len(payload['excluidos'])} · "
          f"reparto multi-instituto: {len(payload['multi_instituto'])} · "
          f"tamaño: {len(json.dumps(payload)) / 1024:.0f} KB")
    if argumentos and argumentos[0] == "--guardar":
        destino = argumentos[1] if len(argumentos) > 1 else "carga_buk.json"
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print("JSON guardado en", destino)
    else:
        print("Respuesta:", enviar(argumentos[0] if argumentos else "http://localhost:8000", payload))

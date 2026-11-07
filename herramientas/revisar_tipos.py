"""
Revisa el tipo de dato real de cada celda en los Excel de BUK y de planificación.

Para cada columna cuenta cuántas celdas son entero, decimal, texto, fecha, duración,
celda vacía o texto vacío (''), y muestra el formato de número de Excel. Así se
detectan problemas como fechas vacías guardadas como texto o números guardados como texto.

No modifica ningún archivo: solo lee y muestra el resultado (o lo guarda en un CSV).

Uso (desde la carpeta del proyecto):
    python herramientas/revisar_tipos.py
        Revisa los Excel del kit en data/raw/ (todas las hojas de la lista REVISIONES).
    python herramientas/revisar_tipos.py "data/entrada/reporte BUK.xlsx" --hoja Dotacion_2026
        Revisa un archivo nuevo (por ejemplo, el que deja el bot de Blue Prism).
    python herramientas/revisar_tipos.py --csv tipos.csv
        Además guarda el resultado en un CSV.
"""

import argparse
import collections
import csv
import datetime as dt
import sys
import warnings
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

# Carpeta raíz del proyecto (funciona igual en Mac y en la VM Windows)
RAIZ = Path(__file__).resolve().parent.parent
BUK = "Nac - Base contratos x mes.xlsx"
PLAN = "Nac - Planificación Asistencial x mes.xlsx"

# Qué se revisa por defecto: (archivo en data/raw, hoja, rango).
# Rango None = se detecta solo la fila de encabezados y las filas de datos.
# Parámetros mezcla varias tablas en una hoja, por eso se indica el rango de cada una.
REVISIONES = [
    (BUK, "Dotacion_2026", None),
    (PLAN, "Dotacion_Asistencial", None),
    (PLAN, "Excepciones", None),
    (PLAN, "Distribucion_NAC", None),
    (PLAN, "Parámetros", "F3:I8"),      # factor grupal
    (PLAN, "Parámetros", "K1:L138"),    # días inhábiles y feriados
    (PLAN, "Parámetros", "X2:AD14"),    # días y semanas hábiles por mes
    (PLAN, "Parámetros", "AM1:AO26"),   # tabla Institutos
    (PLAN, "Parámetros", "AR1:AU70"),   # tabla Cargo_SIC
    (PLAN, "Parámetros", "AX1:AY25"),   # tabla Especialidades
]


def tipo_de(valor):
    """Devuelve el tipo de dato de una celda con el vocabulario del diccionario de datos."""
    if valor is None:
        return "vacía"
    if isinstance(valor, str):
        return "texto vacío" if valor.strip() == "" else "texto"
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, int):
        return "entero"
    if isinstance(valor, float):
        # Excel guarda todos los números como decimales: 40.0 se cuenta como entero
        return "entero" if valor.is_integer() else "decimal"
    if isinstance(valor, dt.datetime):
        return "fecha" if valor.time() == dt.time(0) else "fecha y hora"
    if isinstance(valor, dt.timedelta):
        return "duración"  # horas con formato [h]:mm
    if isinstance(valor, dt.time):
        return "hora"
    return type(valor).__name__


def detectar_encabezados(filas):
    """Busca, entre las primeras 10 filas, la que tiene más textos: esa es la de encabezados."""
    mejor, max_textos = 0, -1
    for i, fila in enumerate(filas[:10]):
        textos = sum(1 for c in fila if isinstance(c.value, str) and c.value.strip())
        if textos > max_textos:
            mejor, max_textos = i, textos
    return mejor


def es_fin_de_datos(fila):
    """Los datos terminan en la primera fila vacía o en la fila de totales."""
    valores = [c.value for c in fila]
    if all(v is None or (isinstance(v, str) and not v.strip()) for v in valores):
        return True
    return any(isinstance(v, str) and v.strip().lower().startswith("total") for v in valores[:3])


def revisar_hoja(ruta, hoja, rango=None):
    """Lee una hoja y devuelve una lista de diccionarios, uno por columna."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # avisos de openpyxl sobre validaciones de Excel
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    ws = libro[hoja]
    if rango:
        col_min, fila_min, col_max, fila_max = range_boundaries(rango)
        filas = list(ws.iter_rows(min_row=fila_min, max_row=fila_max, min_col=col_min, max_col=col_max))
        i_enc = 0
    else:
        col_min = 1
        filas = list(ws.iter_rows())
        i_enc = detectar_encabezados(filas)
    encabezados = [c.value for c in filas[i_enc]]
    # Encabezado de dos filas (como en Distribucion_NAC): si la celda está vacía, se usa la de arriba
    arriba = [c.value for c in filas[i_enc - 1]] if i_enc > 0 else [None] * len(encabezados)

    datos = []
    for fila in filas[i_enc + 1:]:
        if es_fin_de_datos(fila):
            break
        datos.append(fila)

    resultado = []
    for j in range(len(encabezados)):
        tipos, formatos, textos = collections.Counter(), collections.Counter(), collections.Counter()
        espacios = 0  # textos con espacios al inicio o al final (rompen los cruces)
        for fila in datos:
            if j >= len(fila):
                continue
            celda = fila[j]
            t = tipo_de(celda.value)
            tipos[t] += 1
            if t not in ("vacía", "texto vacío"):
                formatos[getattr(celda, "number_format", "General")] += 1
            if t == "texto":
                textos[celda.value] += 1
                if celda.value != celda.value.strip():
                    espacios += 1
        if not tipos or set(tipos) == {"vacía"} and encabezados[j] is None:
            continue  # columna sin encabezado ni datos
        nombre = encabezados[j] if encabezados[j] is not None else (arriba[j] if j < len(arriba) else None)
        resultado.append({
            "hoja": hoja,
            "columna": get_column_letter(col_min + j),
            "encabezado": " ".join(str(nombre).split()) if nombre is not None else "(sin encabezado)",
            "filas": len(datos),
            "tipos": ", ".join(f"{t} {n}" for t, n in tipos.most_common()),
            "formato": ", ".join(f"{f} {n}" for f, n in formatos.most_common(2)),
            "valores_distintos": len(textos),
            "ejemplos": ", ".join(repr(v) for v, _ in textos.most_common(3)) if 0 < len(textos) <= 5 else "",
            "espacios_sobrantes": espacios,
            "fila_encabezados": (fila_min if rango else 1) + i_enc,
        })
    libro.close()
    return resultado


def imprimir(resultado):
    """Muestra una tabla simple por hoja y avisa de los tipos mezclados."""
    if not resultado:
        return
    r0 = resultado[0]
    print(f"\n=== {r0['hoja']} · encabezados en la fila {r0['fila_encabezados']} · {r0['filas']} filas de datos")
    for r in resultado:
        avisos = []
        if "texto vacío" in r["tipos"]:
            avisos.append("vacíos como texto ''")
        if r["espacios_sobrantes"]:
            avisos.append(f"{r['espacios_sobrantes']} textos con espacios sobrantes")
        if "texto" in r["tipos"].replace("texto vacío", "") and any(t in r["tipos"] for t in ("entero", "decimal", "fecha")):
            avisos.append("mezcla texto y números/fechas")
        linea = f"{r['columna']:>3}  {r['encabezado'][:45]:<45}  {r['tipos']}"
        if r["ejemplos"]:
            linea += f"  · valores: {r['ejemplos']}"
        if avisos:
            linea += "  ⚠ " + "; ".join(avisos)
        print(linea)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows a veces no muestra tildes
    parser = argparse.ArgumentParser(description="Revisa el tipo de dato de cada celda de un Excel.")
    parser.add_argument("archivo", nargs="?", help="Excel a revisar (por defecto, los del kit en data/raw)")
    parser.add_argument("--hoja", help="Hoja a revisar (por defecto, todas las del archivo)")
    parser.add_argument("--csv", help="Guarda el resultado en este archivo CSV")
    args = parser.parse_args()

    if args.archivo:
        ruta = Path(args.archivo)
        if args.hoja:
            hojas = [args.hoja]
        else:
            hojas = openpyxl.load_workbook(ruta, read_only=True).sheetnames
        tareas = [(ruta, h, None) for h in hojas]
    else:
        tareas = [(RAIZ / "data" / "raw" / archivo, hoja, rango) for archivo, hoja, rango in REVISIONES]

    todo = []
    for ruta, hoja, rango in tareas:
        if not ruta.exists():
            print(f"No se encontró el archivo: {ruta}")
            sys.exit(1)
        resultado = revisar_hoja(ruta, hoja, rango)
        for r in resultado:
            r["archivo"] = ruta.name
        imprimir(resultado)
        todo.extend(resultado)

    if args.csv:
        campos = ["archivo", "hoja", "columna", "encabezado", "fila_encabezados", "filas", "tipos",
                  "formato", "valores_distintos", "ejemplos", "espacios_sobrantes"]
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel abre bien las tildes
            escritor = csv.DictWriter(f, fieldnames=campos)
            escritor.writeheader()
            escritor.writerows({k: r[k] for k in campos} for r in todo)
        print(f"\nResultado guardado en {args.csv}")


if __name__ == "__main__":
    main()

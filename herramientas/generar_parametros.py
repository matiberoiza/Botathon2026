"""
Genera los dos archivos que lee el bot de Blue Prism, a partir de los Excel del kit:

  data/generados/parametros.xlsx
      Catálogos y reglas (institutos, cargos, % por tramo, asignaciones, factor grupal, calendario,
      feriados, jornada legal y parámetros sueltos). Sin datos personales.
  data/generados/entradas_planificacion.xlsx
      Datos por profesional que hoy solo existen en el Excel de planificación y no vienen en BUK
      (colación, asignaciones, ausencias, semanas hábiles, reparto multi-instituto, ajustes manuales).

Cada hoja tiene los encabezados en la fila 1 y una fila por registro, sin celdas combinadas ni
fórmulas, para que el bot la lea con «Get Worksheet As Collection» y la filtre.

Uso (desde la carpeta del proyecto):
    python herramientas/generar_parametros.py
"""

import pandas as pd

from comun import COL_HORAS_DISP, GENERADOS, abrir_plan, leer_buk, leer_dotacion

TRAMOS = [  # (código, horas desde [incluida], horas hasta [excluida], columnas de Distribucion_NAC)
    ("MAYOR_IGUAL_40", 40, None, (6, 7, 8)),
    ("ENTRE_22_40", 22, 40, (9, 10, 11)),
    ("MENOR_22", 0, 22, (12, 13, 14)),
]
SAN_CON = {131, 81}  # Santiago y Concepción: otro número de pacientes por grupo


def texto(v):
    """Texto limpio: sin espacios sobrantes; vacío → None."""
    if v is None or (isinstance(v, float) and v != v):  # celda vacía o NaN de pandas
        return None
    s = str(v).strip()
    return s or None


def num(v):
    """Número o 0 si la celda está vacía (en el Excel, un % vacío significa 0)."""
    return float(v) if isinstance(v, (int, float)) else 0.0


def generar_parametros(libro, buk, dot):
    p, nac = libro["Parámetros"], libro["Distribucion_NAC"]
    hojas = {}

    # --- Institutos (tabla Institutos de Parámetros; se toma el primer nombre de cada código) ---
    filas, vistos = [], set()
    for r in range(2, 27):
        it, abrev, nombre = p.cell(r, 39).value, texto(p.cell(r, 40).value), texto(p.cell(r, 41).value)
        if it is None or it in vistos:
            continue
        vistos.add(it)
        filas.append({
            "IT": it, "Abreviatura": abrev, "Nombre": nombre.replace("´", "'"),
            "GrupoFactorGrupal": "SAN_CON" if it in SAN_CON else "OTROS",
            "DiasVacacionesAdicionales": p["AG26"].value if it == 111 else p["AF26"].value,  # Coyhaique 10, resto 5
        })
    hojas["Institutos"] = pd.DataFrame(filas)

    # --- Alias: todas las formas en que aparece cada instituto en los reportes ---
    alias = {}
    for r in range(2, 27):
        for c in (40, 41):
            if texto(p.cell(r, c).value):
                alias[texto(p.cell(r, c).value)] = p.cell(r, 39).value
    for col in ("Instituto", "Área"):
        alias.update(dict(zip(buk[col].map(texto), buk["IT"])))
    for col in ("Instituto", "División"):
        alias.update(dict(zip(dot[col].map(texto), dot["IT"])))
    exc = libro["Excepciones"]
    for r in range(3, 20):
        for c in (1, 2):
            if texto(exc.cell(r, c).value):
                alias[texto(exc.cell(r, c).value)] = exc.cell(r, 3).value
    hojas["AliasInstitutos"] = pd.DataFrame(sorted(alias.items()), columns=["Alias", "IT"])

    # --- Cargos, minutos estándar y % por tramo (Distribucion_NAC filas 7 a 92) ---
    cod_esp = {texto(p.cell(r, 44).value): texto(p.cell(r, 47).value) for r in range(2, 71) if p.cell(r, 44).value}
    cod_esp_buk = buk.groupby("Cargo")["Cod_Esp"].agg(lambda s: s.mode()[0]).to_dict()
    cargos, distribucion = [], []
    for r in range(7, 93):
        cargo = texto(nac.cell(r, 2).value)
        if not cargo:
            continue
        cargos.append({
            "Cargo": cargo, "CodEsp": cod_esp.get(cargo) or cod_esp_buk.get(cargo),
            "Unidad": texto(nac.cell(r, 3).value),
            "MinDirecta": nac.cell(r, 4).value, "MinIndirecta": nac.cell(r, 5).value,
        })
        for tramo, _, _, (cd, ci, cn) in TRAMOS:
            d, i, n = num(nac.cell(r, cd).value), num(nac.cell(r, ci).value), num(nac.cell(r, cn).value)
            distribucion.append({"Cargo": cargo, "Tramo": tramo, "PctDirecto": d, "PctIndirecto": i, "PctNAS": n,
                                 "SumaOK": "SI" if abs(d + i + n - 1) < 1e-9 else "NO"})
    hojas["Cargos"] = pd.DataFrame(cargos)
    hojas["Distribucion"] = pd.DataFrame(distribucion)

    # --- Especialidades (tabla Especialidades de Parámetros) + códigos usados que no estén en ella ---
    especialidades = {texto(p.cell(r, 50).value): texto(p.cell(r, 51).value) for r in range(2, 26) if p.cell(r, 50).value}
    usados = set(hojas["Cargos"]["CodEsp"].dropna()) | set(buk["Cod_Esp"].dropna()) | set(dot["Area"].dropna())
    for codigo in sorted(usados - set(especialidades)):
        especialidades[codigo] = codigo  # sin nombre en el Excel: se usa el mismo código
    hojas["Especialidades"] = pd.DataFrame(sorted(especialidades.items()), columns=["CodEsp", "Especialidad"])
    hojas["Tramos"] = pd.DataFrame([{"Tramo": t, "HorasDesde": d, "HorasHasta": h} for t, d, h, _ in TRAMOS])

    # --- Catálogo de asignaciones (Distribucion_NAC R:T), sin duplicados ni nombres de personas ---
    asignaciones, vistos = [], set()
    for r in range(7, 40):
        nombre = texto(nac.cell(r, 18).value)
        if not nombre or nombre in vistos:
            continue
        vistos.add(nombre)
        desc = texto(nac.cell(r, 20).value) or ""
        if "Contrato" in desc:  # dos descripciones traen el nombre de una persona: no se copia
            desc = "Contrato (descripción omitida: contenía un nombre)"
        asignaciones.append({
            "Asignacion": nombre, "HorasSemanales": nac.cell(r, 19).value,
            "RequiereAutorizacionDMN": "SI" if "DMN" in desc else "NO",  # propuesta: confirmar con el equipo
            "Descripcion": desc,
        })
    asignaciones.append({"Asignacion": "Asignación 4 (sin nombre)", "HorasSemanales": 0.25,
                         "RequiereAutorizacionDMN": "NO",
                         "Descripcion": "0,25 h que el Excel aplica en 401 filas sin nombre (pregunta abierta)"})
    hojas["Asignaciones"] = pd.DataFrame(asignaciones)

    # --- Factor grupal (Parámetros F4:I8) ---
    hojas["FactorGrupal"] = pd.DataFrame(
        [{"CodEsp": p.cell(r, 6).value, "GrupoInstituto": g, "PctGrupal": p.cell(r, 7).value,
          "PacientesPorGrupo": p.cell(r, 8 if g == "SAN_CON" else 9).value}
         for r in range(4, 9) for g in ("SAN_CON", "OTROS")])

    # --- Calendario: días hábiles y semanas de planificación por mes (Parámetros X3:AD14) ---
    hojas["Calendario"] = pd.DataFrame(
        [{"Mes": r - 2, "Periodo": p.cell(r, 28).value.date(), "DiasHabiles": p.cell(r, 25).value,
          "Semanas": p.cell(r, 30).value} for r in range(3, 15)])

    # --- Feriados (Parámetros K:L, sin fines de semana) y feriado regional de Arica ---
    tipos = {"Feriado Colectivo": "COLECTIVO", "Feriados 2026": "NACIONAL", "Feriado 2026": "NACIONAL"}
    feriados = [{"Fecha": p.cell(r, 11).value.date(), "Tipo": tipos[texto(p.cell(r, 12).value)], "IT": None}
                for r in range(2, 139)
                if p.cell(r, 11).value is not None and texto(p.cell(r, 12).value) in tipos]
    feriados.append({"Fecha": p["S28"].value.date(), "Tipo": "REGIONAL", "IT": 11})
    hojas["Feriados"] = pd.DataFrame(feriados)

    hojas["JornadaLegal"] = pd.DataFrame([
        {"VigenteDesde": "2026-01-01", "HorasMaximas": 44},
        {"VigenteDesde": "2026-05-01", "HorasMaximas": 42},
    ])

    hojas["Parametros"] = pd.DataFrame([
        ("META_PCT", 0.9, "Meta de gestión: % de las atenciones planificadas (Dotacion_Asistencial FZ3)"),
        ("MAX_ASIGNACIONES", 2, "Máximo de asignaciones especiales para jornadas sobre el umbral"),
        ("UMBRAL_HORAS_MAX_ASIGNACIONES", 30, "Horas semanales desde las que rige el máximo de asignaciones"),
        ("HORAS_ALERTA_MAXIMO", 45, "Horas semanales sobre las que se genera alerta (RN-03)"),
        ("PAUSA_SALUDABLE_PCT_40", 0.10, "Pausa saludable en tramo >= 40 h (solo desglose del NAS)"),
        ("PAUSA_SALUDABLE_PCT_OTROS", 0.06, "Pausa saludable en los otros tramos (solo desglose del NAS)"),
        ("FACTOR_DIAS_PROGRESIVOS", 0.7, "Factor de días progresivos (Dotacion_Asistencial DQ2)"),
        ("FACTOR_DIAS_COMPLEMENTARIOS", 0.8, "Factor de días complementarios (DR2)"),
        ("FACTOR_LEY_21530", 1, "Factor de descanso reparatorio (DS2)"),
        ("FACTOR_VACACIONES_PENDIENTES", 1, "Factor de vacaciones legales pendientes (DT2)"),
        ("DIAS_POR_SEMANA", 5, "Para convertir días en semanas"),
    ], columns=["Clave", "Valor", "Descripcion"])
    return hojas


def generar_entradas(libro, dot):
    """Datos por fila de Dotacion_Asistencial (una persona puede tener varias filas: multi-instituto
    o jornada partida). FilaExcel permite volver a la fila original."""
    clave = ["FilaExcel", "PersonaId", "IT"]
    hojas = {}

    hojas["FilasPlanificacion"] = pd.DataFrame({
        "FilaExcel": dot["FilaExcel"], "PersonaId": dot["PersonaId"], "IT": dot["IT"],
        "Cargo": dot["Cargo"].str.strip(), "CodEsp": dot["Area"],
        "PeriodoInicio": dot["Periodo Inicio Jornada"].dt.date, "PeriodoFin": dot["Perido Fin Jornada"].dt.date,
        "HorasColacion": dot["Horas Colación en Contrato"].fillna(0),
        "DiasSemana": dot["N° Días Semana Contrato"],
        "LicenciaExtensa": dot["Licencia Extensa"].fillna("No"),
        "MultiInstituto": dot["Excepción"].notna().map({True: "SI", False: "NO"}),
    })

    # Asignaciones: hasta 4 columnas por fila → una fila por asignación
    columnas = [
        ("1", "Asignación 1 (seleccionar de lista desplegable)", "Hrs. Asignación 1"),
        ("2", "Asignación 2 (seleccionar de lista desplegable)", "Hrs. Asignación 2"),
        ("POR_AUTORIZAR", "Por Autorizar DMN y VP  (seleccionar de lista desplegable)", "Hrs. Asignación 3"),
        ("4", None, "Hrs. Asignación 4"),
    ]
    filas = []
    for _, r in dot.iterrows():
        for origen, col_nombre, col_horas in columnas:
            nombre = texto(r[col_nombre]) if col_nombre else "Asignación 4 (sin nombre)"
            h = r[col_horas]
            h = float(h) if isinstance(h, (int, float)) and h == h else None
            if (col_nombre and not nombre and not h) or (not col_nombre and not h):
                continue
            filas.append({"FilaExcel": r.FilaExcel, "PersonaId": r.PersonaId, "IT": r.IT, "Columna": origen,
                          "Asignacion": nombre or "(sin nombre)", "Horas": h,
                          "Observacion": "falta el nombre" if not nombre else ("faltan las horas" if h is None else "")})
    hojas["Asignaciones"] = pd.DataFrame(filas)

    # Ausencias en semanas por mes (patrón Lic1..12, Vac1..12, Perm1..12); solo valores distintos de 0
    filas = []
    for tipo, pref in (("LICENCIA", "Lic"), ("VACACIONES", "Vac"), ("PERMISO", "Perm")):
        for m in range(1, 13):
            for _, r in dot[dot[f"{pref}{m}"].fillna(0) != 0].iterrows():
                filas.append({"FilaExcel": r.FilaExcel, "PersonaId": r.PersonaId, "IT": r.IT, "Mes": m,
                              "Tipo": tipo, "Semanas": r[f"{pref}{m}"]})
    hojas["Ausencias"] = pd.DataFrame(filas)

    # Días adicionales del año (patrón DF:DW); solo valores distintos de 0
    cols_dias = list(dot.columns[dot.columns.get_loc("Feriado legal zona extrema ene'26"):
                                 dot.columns.get_loc("Lactancia (Equiv_días/año)") + 1])
    cols_dias.remove("Mes cumpleaños")
    largo = dot.melt(id_vars=clave, value_vars=cols_dias, var_name="Tipo", value_name="Dias")
    hojas["DiasAdicionales"] = largo[largo["Dias"].fillna(0) != 0].sort_values(clave)

    # Semanas hábiles por persona y mes: valores del Excel (su fórmula de julio a diciembre no se pudo reconstruir)
    largo = dot.melt(id_vars=clave, value_vars=[f"SemHab{m}" for m in range(1, 13)], var_name="Mes",
                     value_name="SemanasHabiles")
    largo["Mes"] = largo["Mes"].str.replace("SemHab", "").astype(int)
    hojas["SemanasHabiles"] = largo.sort_values(clave + ["Mes"])

    # Reparto multi-instituto (hoja Excepciones, horas por instituto y mes)
    exc = libro["Excepciones"]
    filas = [{"PersonaId": exc.cell(r, 5).value, "IT": exc.cell(r, 3).value, "Mes": m,
              "HorasSemanales": exc.cell(r, 10 + m).value}
             for r in range(3, 20) for m in range(1, 13) if exc.cell(r, 10 + m).value is not None]
    hojas["MultiInstituto"] = pd.DataFrame(filas)

    # Ajustes manuales: filas donde el Excel no usa el % o los minutos de la tabla
    nac = libro["Distribucion_NAC"]
    tabla = {texto(nac.cell(r, 2).value): [num(nac.cell(r, c).value) for c in range(4, 15)]
             for r in range(7, 93) if nac.cell(r, 2).value}
    filas = []
    for _, r in dot.iterrows():
        t = tabla[r.Cargo.strip()]
        x = r["Prom_Pond Horas Semanales"]
        k = 0 if x >= 40 else (1 if x >= 22 else 2)
        esperado = {"PCT_DIRECTO": t[2 + 3 * k], "PCT_INDIRECTO": t[3 + 3 * k], "PCT_NAS": t[4 + 3 * k], "MIN_DIRECTA": t[0]}
        real = {"PCT_DIRECTO": r["%Directo"], "PCT_INDIRECTO": r["%Indirecto"], "PCT_NAS": r["% NAS"],
                "MIN_DIRECTA": r["Estándar Minutos Atención Directa"]}
        for campo in esperado:
            if real[campo] == real[campo] and abs(real[campo] - esperado[campo]) > 1e-9:
                filas.append({"FilaExcel": r.FilaExcel, "PersonaId": r.PersonaId, "IT": r.IT, "Campo": campo,
                              "ValorTabla": esperado[campo], "ValorExcel": real[campo],
                              "Motivo": "Por confirmar: el Excel no explica el ajuste"})
    hojas["AjustesManuales"] = pd.DataFrame(filas)
    return hojas


LEEME_PARAMETROS = [
    ("Institutos", "Un instituto por código IT. GrupoFactorGrupal decide los pacientes por grupo."),
    ("AliasInstitutos", "Todas las formas en que aparece un instituto en los reportes → su IT. Usar el IT, no el nombre."),
    ("Cargos", "Minutos estándar por cargo. Si un cargo de BUK no está aquí: registro EXCLUIDO."),
    ("Distribucion", "% directo, indirecto y NAS por cargo y tramo. SumaOK = NO → error de parámetros."),
    ("Especialidades", "Código de especialidad o área → nombre."),
    ("Tramos", "Tramo según el promedio de horas: desde (incluida) hasta (excluida)."),
    ("Asignaciones", "Catálogo de asignaciones especiales. RequiereAutorizacionDMN es una propuesta a confirmar."),
    ("FactorGrupal", "% grupal y pacientes por grupo por especialidad y grupo de instituto."),
    ("Calendario", "Días hábiles y semanas de planificación de cada mes."),
    ("Feriados", "Feriados nacionales, colectivos y regionales (con IT)."),
    ("JornadaLegal", "Jornada máxima legal vigente desde cada fecha."),
    ("Parametros", "Valores sueltos (meta, máximos, factores)."),
]
LEEME_ENTRADAS = [
    ("FilasPlanificacion", "Una fila por fila de Dotacion_Asistencial: colación, días por semana, vigencia de la jornada."),
    ("Asignaciones", "Asignaciones de cada fila (una por renglón). Observacion marca datos incompletos."),
    ("Ausencias", "Licencias, vacaciones y permisos en SEMANAS por mes."),
    ("DiasAdicionales", "Días adicionales del año por tipo (cumpleaños, feriado adicional…)."),
    ("SemanasHabiles", "Semanas hábiles por fila y mes tomadas del Excel (su fórmula de jul–dic está pendiente)."),
    ("MultiInstituto", "Horas por instituto y mes de los profesionales multi-instituto (hoja Excepciones)."),
    ("AjustesManuales", "Filas en que el Excel no usa el % o los minutos de la tabla. Confirmar si se mantienen."),
]


def escribir(ruta, hojas, leeme):
    with pd.ExcelWriter(ruta, engine="openpyxl") as w:
        pd.DataFrame(leeme, columns=["Hoja", "Contenido"]).to_excel(w, sheet_name="LEEME", index=False)
        for nombre, df in hojas.items():
            df.to_excel(w, sheet_name=nombre, index=False)
    print(f"\n{ruta.relative_to(GENERADOS.parent.parent)}")
    for nombre, df in hojas.items():
        print(f"  {nombre:<20} {len(df):>5} filas")


def main():
    GENERADOS.mkdir(parents=True, exist_ok=True)
    libro, buk, dot = abrir_plan(), leer_buk(), leer_dotacion()
    parametros = generar_parametros(libro, buk, dot)
    entradas = generar_entradas(libro, dot)

    # Controles: todo cargo e instituto de BUK debe estar en los catálogos
    faltan_cargos = set(buk["Cargo"]) - set(parametros["Cargos"]["Cargo"])
    faltan_it = set(buk["IT"]) - set(parametros["Institutos"]["IT"])
    malas = parametros["Distribucion"].query("SumaOK == 'NO'")
    print(f"Control: cargos de BUK sin parámetros: {len(faltan_cargos)} | IT sin catálogo: {len(faltan_it)} "
          f"| distribuciones que no suman 100 %: {len(malas)}")

    escribir(GENERADOS / "parametros.xlsx", parametros, LEEME_PARAMETROS)
    escribir(GENERADOS / "entradas_planificacion.xlsx", entradas, LEEME_ENTRADAS)


if __name__ == "__main__":
    main()

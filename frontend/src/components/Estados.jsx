// Mensajes comunes mientras se cargan los datos, si no hay datos o si hay un error.
export function Cargando() {
  return <p role="status" className="text-slate-700">Cargando…</p>
}

export function SinPlanificacion() {
  return (
    <p role="status" className="rounded-lg border border-dashed border-slate-300 bg-white p-4 text-slate-800">
      Todavía no hay planificación calculada. Aparecerá cuando Blue Prism envíe el reporte de BUK.
    </p>
  )
}

export function MensajeError({ texto }) {
  return (
    <p role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-red-900">
      No se pudieron cargar los datos: {texto}
    </p>
  )
}

// Estado de calidad de un registro: texto + color (nunca solo color)
const ESTILOS = {
  VALIDO: 'bg-green-100 text-green-900',
  ALERTA: 'bg-amber-100 text-amber-900',
  PENDIENTE: 'bg-blue-100 text-blue-900',
  EXCLUIDO: 'bg-red-100 text-red-900',
}
const NOMBRES = { VALIDO: 'Válido', ALERTA: 'Alerta', PENDIENTE: 'Pendiente', EXCLUIDO: 'Excluido' }

export function Insignia({ estado }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-sm font-medium ${ESTILOS[estado] ?? 'bg-slate-100'}`}>
      {NOMBRES[estado] ?? estado}
    </span>
  )
}

// Llamadas al backend FastAPI. En desarrollo, Vite reenvía /api al puerto 8000 (ver vite.config.js).

export class SinDatos extends Error {}

async function pedir(ruta, opciones) {
  const respuesta = await fetch(ruta, opciones)
  const datos = await respuesta.json().catch(() => ({}))
  if (respuesta.status === 404) throw new SinDatos(datos.detail || 'Sin datos')
  if (!respuesta.ok) {
    // FastAPI devuelve el motivo del error en "detail"
    throw new Error(typeof datos.detail === 'string' ? datos.detail : `Error ${respuesta.status}`)
  }
  return datos
}

// Arma «?it=131&mes=6» omitiendo los filtros vacíos
function consulta(filtros) {
  const p = new URLSearchParams()
  Object.entries(filtros).forEach(([k, v]) => v !== '' && v != null && p.set(k, v))
  const texto = p.toString()
  return texto ? `?${texto}` : ''
}

export const api = {
  salud: () => pedir('/api/salud'),
  kpis: (filtros) => pedir(`/api/v1/dashboard/kpis${consulta(filtros)}`),
  institutos: (mes) => pedir(`/api/v1/dashboard/institutos${consulta({ mes })}`),
  profesionales: (filtros) => pedir(`/api/v1/profesionales${consulta(filtros)}`),
  excepciones: (it) => pedir(`/api/v1/excepciones${consulta({ it })}`),
  parametros: () => pedir('/api/v1/parametros'),
  cambiarParametro: (clave, cuerpo) =>
    pedir(`/api/v1/parametros/${clave}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cuerpo),
    }),
  versiones: () => pedir('/api/v1/versiones'),
  cambios: () => pedir('/api/v1/cambios'),
}

export const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre']

export const numero = (v, decimales = 0) =>
  v == null ? '—' : Number(v).toLocaleString('es-CL', { maximumFractionDigits: decimales })

export const porcentaje = (v) => (v == null ? 'No aplica' : `${(v * 100).toLocaleString('es-CL', { maximumFractionDigits: 1 })} %`)

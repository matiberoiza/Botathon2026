import { useState } from 'react'
import { api, numero } from '../api.js'
import { useDatos } from '../hooks.js'
import { Cargando, MensajeError } from '../components/Estados.jsx'

const ESTADOS = { PUBLICADA: 'Publicada', EN_PROCESO: 'En proceso', FALLIDA: 'Fallida' }
const TIPOS = { ALTA: 'Alta', BAJA: 'Baja', MODIFICACION: 'Modificación', PARAMETRO: 'Parámetro' }
const ESTILO_TIPO = {
  ALTA: 'bg-green-100 text-green-900',
  BAJA: 'bg-red-100 text-red-900',
  MODIFICACION: 'bg-blue-100 text-blue-900',
  PARAMETRO: 'bg-slate-200 text-slate-900',
}

// Trazabilidad: cambios detectados entre reportes de BUK y cambios de parámetros, y versiones del cálculo
export default function Historial({ version }) {
  const cambios = useDatos(() => api.cambios(), [version])
  const versiones = useDatos(() => api.versiones(), [version])
  const [tipo, setTipo] = useState('')

  if ((cambios.cargando && !cambios.datos) || (versiones.cargando && !versiones.datos)) return <Cargando />
  if (cambios.error || versiones.error) return <MensajeError texto={cambios.error || versiones.error} />
  const { resumen, cambios: lista } = cambios.datos
  const visibles = lista.filter((c) => !tipo || c.tipo_cambio === tipo)

  return (
    <div className="space-y-8">
      <section aria-labelledby="titulo-cambios" className="space-y-3">
        <h3 id="titulo-cambios" className="font-semibold">Cambios detectados</h3>
        <p className="text-slate-800">
          Cada vez que llega un reporte de BUK, se compara con el anterior. La planificación se ajusta desde la fecha en
          que rige cada cambio.
        </p>
        {lista.length === 0 ? (
          <p className="text-slate-800">Todavía no hay cambios: aparecerán cuando llegue un segundo reporte de BUK.</p>
        ) : (
          <>
            <ul className="flex flex-wrap gap-3" aria-label="Resumen de cambios">
              {Object.entries(TIPOS).filter(([t]) => resumen[t]).map(([t, nombre]) => (
                <li key={t} className={`rounded-full px-3 py-1 text-sm font-medium ${ESTILO_TIPO[t]}`}>
                  {nombre}: {numero(resumen[t])}
                </li>
              ))}
            </ul>
            <div>
              <label htmlFor="filtro-tipo" className="block text-sm font-medium text-slate-700">Tipo de cambio</label>
              <select id="filtro-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)}
                      className="mt-1 rounded border border-slate-400 bg-white px-3 py-2 text-base">
                <option value="">Todos</option>
                {Object.entries(TIPOS).map(([t, nombre]) => <option key={t} value={t}>{nombre}</option>)}
              </select>
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-left text-sm">
                <caption className="sr-only">Cambios detectados</caption>
                <thead className="bg-slate-100">
                  <tr>
                    {['Tipo', 'PersonaId', 'Instituto', 'Qué cambió', 'Antes', 'Ahora', 'Rige desde', 'Origen'].map((t) => (
                      <th key={t} scope="col" className="px-3 py-2">{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((c) => (
                    <tr key={c.cambio_id} className="border-t border-slate-200">
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2 py-0.5 font-medium ${ESTILO_TIPO[c.tipo_cambio]}`}>
                          {TIPOS[c.tipo_cambio] ?? c.tipo_cambio}
                        </span>
                      </td>
                      <td className="px-3 py-2">{c.persona_id ?? '—'}</td>
                      <td className="px-3 py-2">{c.instituto ?? '—'}</td>
                      <td className="px-3 py-2">{c.campo ?? '—'}</td>
                      <td className="px-3 py-2">{c.valor_anterior ?? '—'}</td>
                      <td className="px-3 py-2">{c.valor_nuevo ?? '—'}</td>
                      <td className="px-3 py-2">{c.vigente_desde}</td>
                      <td className="px-3 py-2">{c.origen === 'BOT' ? 'Reporte BUK (bot)' : `Dashboard (${c.usuario})`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section aria-labelledby="titulo-versiones" className="space-y-3">
        <h3 id="titulo-versiones" className="font-semibold">Versiones del cálculo</h3>
        <table className="w-full rounded-lg border border-slate-200 bg-white text-left">
          <caption className="sr-only">Versiones del cálculo</caption>
          <thead className="bg-slate-100">
            <tr>
              {['Versión', 'Fecha', 'Motivo', 'Quién', 'Estado'].map((t) => (
                <th key={t} scope="col" className="px-3 py-2">{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {versiones.datos.map((v) => (
              <tr key={v.version_id} className="border-t border-slate-200">
                <td className="px-3 py-2">{v.version_id}</td>
                <td className="px-3 py-2">{v.creada_en}</td>
                <td className="px-3 py-2">{v.motivo}</td>
                <td className="px-3 py-2">{v.usuario}</td>
                <td className="px-3 py-2">{ESTADOS[v.estado] ?? v.estado}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}

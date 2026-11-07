import { api, numero } from '../api.js'
import { useDatos } from '../hooks.js'
import { Cargando, Insignia, MensajeError, SinPlanificacion } from '../components/Estados.jsx'

// Alertas agrupadas por tipo (para no saturar la vista) y errores de la última carga de BUK
export default function Excepciones({ filtros, version }) {
  const datos = useDatos(() => api.excepciones(filtros.it), [filtros.it, version])

  if (datos.cargando && !datos.datos) return <Cargando />
  if (datos.sinDatos) return <SinPlanificacion />
  if (datos.error) return <MensajeError texto={datos.error} />
  const { alertas_agrupadas: grupos, errores_carga: errores } = datos.datos

  return (
    <div className="space-y-8">
      <section aria-labelledby="titulo-alertas">
        <h3 id="titulo-alertas" className="mb-2 font-semibold">Observaciones en la planificación</h3>
        {grupos.length === 0 ? (
          <p className="text-slate-800">No hay observaciones.</p>
        ) : (
          <table className="w-full rounded-lg border border-slate-200 bg-white text-left">
            <caption className="sr-only">Observaciones agrupadas por tipo</caption>
            <thead className="bg-slate-100">
              <tr>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">Motivo</th>
                <th scope="col" className="px-3 py-2">Profesionales</th>
              </tr>
            </thead>
            <tbody>
              {grupos.map((g) => (
                <tr key={`${g.estado}-${g.motivo}`} className="border-t border-slate-200">
                  <td className="px-3 py-2"><Insignia estado={g.estado} /></td>
                  <td className="px-3 py-2">{g.motivo}</td>
                  <td className="px-3 py-2">{numero(g.profesionales)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-labelledby="titulo-errores">
        <h3 id="titulo-errores" className="mb-2 font-semibold">Filas rechazadas en la última carga de BUK</h3>
        {errores.length === 0 ? (
          <p className="text-slate-800">Ninguna: todas las filas pasaron la validación.</p>
        ) : (
          <table className="w-full rounded-lg border border-slate-200 bg-white text-left">
            <caption className="sr-only">Filas rechazadas</caption>
            <thead className="bg-slate-100">
              <tr>
                {['Fila', 'PersonaId', 'Campo', 'Valor', 'Motivo', 'Detectado por'].map((t) => (
                  <th key={t} scope="col" className="px-3 py-2">{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {errores.map((e, i) => (
                <tr key={i} className="border-t border-slate-200">
                  <td className="px-3 py-2">{e.fila ?? '—'}</td>
                  <td className="px-3 py-2">{e.persona_id ?? '—'}</td>
                  <td className="px-3 py-2">{e.campo ?? '—'}</td>
                  <td className="px-3 py-2">{e.valor ?? '—'}</td>
                  <td className="px-3 py-2">{e.detalle}</td>
                  <td className="px-3 py-2">{e.detectado_por === 'BOT' ? 'Blue Prism' : 'Backend'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}

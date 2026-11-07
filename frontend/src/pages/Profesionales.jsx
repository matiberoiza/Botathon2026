import { useState } from 'react'
import { api, MESES, numero, porcentaje } from '../api.js'
import { useDatos } from '../hooks.js'
import { Cargando, Insignia, MensajeError, SinPlanificacion } from '../components/Estados.jsx'

// Detalle por profesional. Sin instituto ni mes elegidos serían miles de filas: se pide elegir uno.
export default function Profesionales({ filtros, version }) {
  const [buscar, setBuscar] = useState('')
  const elegido = filtros.it || filtros.mes
  const filas = useDatos(() => (elegido ? api.profesionales(filtros) : Promise.resolve([])), [filtros.it, filtros.mes, version])

  if (!elegido) return <p className="text-slate-800">Elige un instituto o un mes en los filtros para ver el detalle por profesional.</p>
  if (filas.cargando && !filas.datos) return <Cargando />
  if (filas.sinDatos) return <SinPlanificacion />
  if (filas.error) return <MensajeError texto={filas.error} />

  const visibles = (filas.datos ?? []).filter(
    (f) => !buscar || String(f.persona_id).includes(buscar) || f.cargo.toLowerCase().includes(buscar.toLowerCase()),
  )

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="buscar" className="block text-sm font-medium text-slate-700">Buscar por PersonaId o cargo</label>
        <input
          id="buscar"
          type="search"
          value={buscar}
          onChange={(e) => setBuscar(e.target.value)}
          className="mt-1 w-full max-w-sm rounded border border-slate-400 px-3 py-2 text-base"
        />
      </div>
      <p role="status" className="text-sm text-slate-600">{numero(visibles.length)} registros</p>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Planificación por profesional y mes</caption>
          <thead className="bg-slate-100">
            <tr>
              {['PersonaId', 'Mes', 'Cargo', 'Horas', 'Tramo', 'Directa h/sem', 'Indirecta h/sem', 'NAS h/sem',
                'Atenciones', 'Meta', 'FOJA', 'Estado'].map((t) => (
                <th key={t} scope="col" className="px-3 py-2 font-semibold">{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibles.map((f) => (
              <tr key={`${f.persona_id}-${f.it}-${f.periodo}`} className="border-t border-slate-200">
                <td className="px-3 py-2">{f.persona_id}</td>
                <td className="px-3 py-2">{MESES[Number(f.periodo.slice(5, 7)) - 1]}{f.origen_dato === 'PROYECCION' ? ' (proyectado)' : ''}</td>
                <td className="px-3 py-2">{f.cargo}</td>
                <td className="px-3 py-2">{numero(f.horas_semanales, 1)}</td>
                <td className="px-3 py-2">{f.tramo.replaceAll('_', ' ').toLowerCase()}</td>
                <td className="px-3 py-2">{numero(f.horas_directa_sem, 1)}</td>
                <td className="px-3 py-2">{numero(f.horas_indirecta_sem, 1)}</td>
                <td className="px-3 py-2">{numero(f.horas_nas_sem, 1)}</td>
                <td className="px-3 py-2">{numero(f.atenciones_total_mes)}</td>
                <td className="px-3 py-2">{numero(f.meta_total_mes)}</td>
                <td className="px-3 py-2">{porcentaje(f.foja)}</td>
                <td className="px-3 py-2" title={f.motivos ?? ''}><Insignia estado={f.estado_calidad} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

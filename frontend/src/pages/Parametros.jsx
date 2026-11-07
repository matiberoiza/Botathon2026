import { useState } from 'react'
import { api } from '../api.js'
import { useDatos } from '../hooks.js'
import { Cargando, MensajeError } from '../components/Estados.jsx'

// Parámetros editables sin tocar código. Al guardar, el backend registra el cambio y recalcula.
export default function Parametros({ version, onRecalculado }) {
  const lista = useDatos(() => api.parametros(), [version])
  const [editando, setEditando] = useState(null) // clave del parámetro que se está editando
  const [form, setForm] = useState({ valor: '', motivo: '', usuario: '' })
  const [aviso, setAviso] = useState({ tipo: '', texto: '' })
  const [guardando, setGuardando] = useState(false)

  if (lista.cargando && !lista.datos) return <Cargando />
  if (lista.error) return <MensajeError texto={lista.error} />

  function abrir(p) {
    setEditando(p.clave)
    setForm({ valor: p.valor, motivo: '', usuario: '' })
    setAviso({ tipo: '', texto: '' })
  }

  async function guardar(e) {
    e.preventDefault()
    if (!form.motivo.trim() || !form.usuario.trim()) {
      setAviso({ tipo: 'error', texto: 'Indica quién hace el cambio y por qué (queda en el historial).' })
      return
    }
    setGuardando(true)
    try {
      const r = await api.cambiarParametro(editando, form)
      setAviso({ tipo: 'ok', texto: `${r.clave}: ${r.valor_anterior} → ${r.valor_nuevo}. Recalculado (versión ${r.version_id}).` })
      setEditando(null)
      onRecalculado()
    } catch (err) {
      setAviso({ tipo: 'error', texto: err.message })
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-slate-800">
        Cambia un valor y la planificación se recalcula. Por ejemplo, la meta de gestión (<code>META_PCT</code>) de 0.9 a 0.85.
      </p>
      <div aria-live="polite">
        {aviso.texto && (
          <p role={aviso.tipo === 'error' ? 'alert' : 'status'}
             className={`rounded border p-3 ${aviso.tipo === 'error' ? 'border-red-300 bg-red-50 text-red-900' : 'border-green-300 bg-green-50 text-green-900'}`}>
            {aviso.texto}
          </p>
        )}
      </div>
      <table className="w-full rounded-lg border border-slate-200 bg-white text-left">
        <caption className="sr-only">Parámetros del cálculo</caption>
        <thead className="bg-slate-100">
          <tr>
            <th scope="col" className="px-3 py-2">Parámetro</th>
            <th scope="col" className="px-3 py-2">Valor</th>
            <th scope="col" className="px-3 py-2">Descripción</th>
            <th scope="col" className="px-3 py-2"><span className="sr-only">Acción</span></th>
          </tr>
        </thead>
        <tbody>
          {lista.datos.map((p) => (
            <tr key={p.clave} className="border-t border-slate-200 align-top">
              <td className="px-3 py-2 font-mono text-sm">{p.clave}</td>
              <td className="px-3 py-2">
                {editando === p.clave ? (
                  <form onSubmit={guardar} className="space-y-2">
                    <label className="block text-sm">Nuevo valor
                      <input value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })}
                             className="mt-1 block w-28 rounded border border-slate-400 px-2 py-1" autoFocus />
                    </label>
                    <label className="block text-sm">Motivo
                      <input value={form.motivo} onChange={(e) => setForm({ ...form, motivo: e.target.value })}
                             className="mt-1 block w-48 rounded border border-slate-400 px-2 py-1" />
                    </label>
                    <label className="block text-sm">Tu nombre
                      <input value={form.usuario} onChange={(e) => setForm({ ...form, usuario: e.target.value })}
                             className="mt-1 block w-48 rounded border border-slate-400 px-2 py-1" />
                    </label>
                    <div className="flex gap-2">
                      <button type="submit" disabled={guardando}
                              className="rounded bg-teleton-700 px-3 py-1 font-semibold text-white hover:bg-teleton-800 disabled:bg-slate-400">
                        {guardando ? 'Recalculando…' : 'Guardar y recalcular'}
                      </button>
                      <button type="button" onClick={() => setEditando(null)} className="rounded border border-slate-400 px-3 py-1">
                        Cancelar
                      </button>
                    </div>
                  </form>
                ) : (
                  p.valor
                )}
              </td>
              <td className="px-3 py-2 text-sm text-slate-700">{p.descripcion}</td>
              <td className="px-3 py-2">
                {editando !== p.clave && (
                  <button type="button" onClick={() => abrir(p)} aria-label={`Editar ${p.clave}`}
                          className="rounded border border-teleton-700 px-3 py-1 text-teleton-800">
                    Editar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

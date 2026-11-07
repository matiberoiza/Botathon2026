import { MESES } from '../api.js'

// Filtros globales: instituto y mes. Afectan a todas las secciones (conMes=false oculta el mes).
export default function Filtros({ institutos, it, mes, onCambiar, conMes = true }) {
  return (
    <form className="flex flex-wrap items-end gap-4" onSubmit={(e) => e.preventDefault()} aria-label="Filtros">
      <div>
        <label htmlFor="filtro-instituto" className="block text-sm font-medium text-slate-700">Instituto</label>
        <select
          id="filtro-instituto"
          value={it}
          onChange={(e) => onCambiar({ it: e.target.value, mes })}
          className="mt-1 rounded border border-slate-400 bg-white px-3 py-2 text-base"
        >
          <option value="">Todos (nacional)</option>
          {institutos.map((i) => (
            <option key={i.it} value={i.it}>{i.instituto}</option>
          ))}
        </select>
      </div>
      {conMes && <div>
        <label htmlFor="filtro-mes" className="block text-sm font-medium text-slate-700">Mes</label>
        <select
          id="filtro-mes"
          value={mes}
          onChange={(e) => onCambiar({ it, mes: e.target.value })}
          className="mt-1 rounded border border-slate-400 bg-white px-3 py-2 text-base"
        >
          <option value="">Todo el año</option>
          {MESES.map((nombre, i) => (
            <option key={nombre} value={i + 1}>{nombre}</option>
          ))}
        </select>
      </div>}
    </form>
  )
}

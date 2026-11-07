import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

// Gráfico de dona accesible: el color va siempre acompañado de texto (leyenda con % y horas)
// y hay una tabla con los mismos datos para lectores de pantalla.
// datos: [{ nombre, valor, color }]
export default function GraficoDona({ titulo, datos, unidad = 'horas' }) {
  const total = datos.reduce((s, d) => s + (d.valor || 0), 0)
  if (!total) {
    return (
      <figure className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
        <figcaption className="font-semibold">{titulo}</figcaption>
        <p className="mt-2 text-slate-700">Todavía no hay datos para mostrar.</p>
      </figure>
    )
  }
  const pct = (v) => `${((v / total) * 100).toLocaleString('es-CL', { maximumFractionDigits: 1 })} %`
  const num = (v) => Math.round(v).toLocaleString('es-CL')

  return (
    <figure className="rounded-lg border border-slate-200 bg-white p-4">
      <figcaption className="mb-2 font-semibold">{titulo}</figcaption>
      <div className="flex flex-wrap items-center gap-6">
        {/* Tamaño fijo: el gráfico necesita un contenedor con medidas reales para dibujarse */}
        <div aria-hidden="true" style={{ width: 224, height: 224, flexShrink: 0 }}>
          <ResponsiveContainer width={224} height={224}>
            <PieChart>
              {/* Sin animación: se dibuja de inmediato (y respeta a quienes prefieren menos movimiento) */}
              <Pie data={datos} dataKey="valor" nameKey="nombre" innerRadius="55%" outerRadius="90%" paddingAngle={2}
                   isAnimationActive={false}>
                {datos.map((d) => <Cell key={d.nombre} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v) => `${num(v)} ${unidad} (${pct(v)})`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {/* Leyenda con texto: se entiende sin distinguir colores */}
        <ul className="space-y-2">
          {datos.map((d) => (
            <li key={d.nombre} className="flex items-center gap-3">
              <span aria-hidden="true" className="inline-block h-4 w-4 rounded-sm" style={{ backgroundColor: d.color }} />
              <span><strong>{d.nombre}:</strong> {pct(d.valor)} · {num(d.valor)} {unidad}</span>
            </li>
          ))}
        </ul>
      </div>
      <details className="mt-4">
        <summary className="cursor-pointer text-blue-800 underline">Ver los datos en una tabla</summary>
        <table className="mt-2 w-full text-left">
          <thead>
            <tr>
              <th scope="col" className="py-1">Tipo</th>
              <th scope="col" className="py-1">Horas</th>
              <th scope="col" className="py-1">Porcentaje</th>
            </tr>
          </thead>
          <tbody>
            {datos.map((d) => (
              <tr key={d.nombre} className="border-t border-slate-200">
                <td className="py-1">{d.nombre}</td>
                <td className="py-1">{num(d.valor)}</td>
                <td className="py-1">{pct(d.valor)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}

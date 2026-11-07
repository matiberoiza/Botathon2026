import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// Gráfico de barras accesible: además del dibujo, incluye una tabla con los mismos datos
// que leen los lectores de pantalla (y que cualquiera puede desplegar).
export default function GraficoBarras({ titulo, datos, campoEtiqueta, campoValor, nombreValor }) {
  if (!datos || datos.length === 0) {
    return (
      <figure className="rounded-lg border border-dashed border-slate-300 bg-white p-6">
        <figcaption className="font-semibold">{titulo}</figcaption>
        <p className="mt-2 text-slate-700">Todavía no hay datos para mostrar.</p>
      </figure>
    )
  }

  return (
    <figure className="rounded-lg border border-slate-200 bg-white p-4">
      <figcaption className="mb-4 font-semibold">{titulo}</figcaption>
      <div aria-hidden="true" className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datos} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" />
            {/* interval 0: muestra el nombre de todos los institutos, inclinados para que quepan */}
            <XAxis dataKey={campoEtiqueta} tick={{ fill: '#334155', fontSize: 12 }} interval={0} angle={-40}
                   textAnchor="end" height={80} />
            <YAxis tick={{ fill: '#334155' }} />
            <Tooltip />
            <Bar dataKey={campoValor} name={nombreValor} fill="#b8000f" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-4">
        <summary className="cursor-pointer text-teleton-800 underline">Ver los datos en una tabla</summary>
        <table className="mt-2 w-full text-left">
          <thead>
            <tr>
              <th scope="col" className="py-1">{campoEtiqueta}</th>
              <th scope="col" className="py-1">{nombreValor}</th>
            </tr>
          </thead>
          <tbody>
            {datos.map((fila) => (
              <tr key={fila[campoEtiqueta]} className="border-t border-slate-200">
                <td className="py-1">{fila[campoEtiqueta]}</td>
                <td className="py-1">{fila[campoValor].toLocaleString('es-CL')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
}

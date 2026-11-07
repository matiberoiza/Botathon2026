import { useEffect, useState } from 'react'
import { CircleAlert, CircleCheck } from 'lucide-react'
import { api } from '../api.js'

// Etiqueta de estado: usa texto e ícono además de color (accesibilidad)
function Indicador({ ok, texto }) {
  const Icono = ok ? CircleCheck : CircleAlert
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium ${ok ? 'bg-green-100 text-green-900' : 'bg-amber-100 text-amber-900'}`}>
      <Icono aria-hidden="true" className="h-4 w-4" />
      {texto}
    </span>
  )
}

// Muestra si la API y la base de datos responden
export default function EstadoConexion() {
  const [estado, setEstado] = useState({ cargando: true })

  useEffect(() => {
    api.salud()
      .then((datos) => setEstado({ api: true, base: datos.base_datos_conectada, detalle: datos.detalle_base_datos }))
      .catch(() => setEstado({ api: false, base: false, detalle: 'No se pudo contactar al backend (puerto 8000).' }))
  }, [])

  if (estado.cargando) {
    return <p role="status" className="text-sm text-slate-600">Revisando conexión…</p>
  }

  return (
    <div role="status" className="flex flex-wrap items-center gap-2" title={estado.detalle}>
      <Indicador ok={estado.api} texto={estado.api ? 'API conectada' : 'API sin conexión'} />
      <Indicador ok={estado.base} texto={estado.base ? 'Base de datos conectada' : 'Base de datos sin conexión'} />
    </div>
  )
}

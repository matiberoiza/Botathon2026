import { useState } from 'react'
import { Heart, History, LayoutDashboard, SlidersHorizontal, TriangleAlert, Users } from 'lucide-react'
import { api } from './api.js'
import { useDatos } from './hooks.js'
import EstadoConexion from './components/EstadoConexion.jsx'
import Filtros from './components/Filtros.jsx'
import Resumen from './pages/Resumen.jsx'
import Profesionales from './pages/Profesionales.jsx'
import Excepciones from './pages/Excepciones.jsx'
import Parametros from './pages/Parametros.jsx'
import Historial from './pages/Historial.jsx'

// Secciones de la aplicación (navegación simple, sin librería de rutas)
const SECCIONES = [
  { id: 'resumen', titulo: 'Resumen nacional', Icono: LayoutDashboard, Componente: Resumen },
  { id: 'profesionales', titulo: 'Profesionales', Icono: Users, Componente: Profesionales },
  { id: 'excepciones', titulo: 'Excepciones', Icono: TriangleAlert, Componente: Excepciones },
  { id: 'parametros', titulo: 'Parámetros', Icono: SlidersHorizontal, Componente: Parametros },
  { id: 'historial', titulo: 'Historial', Icono: History, Componente: Historial },
]

export default function App() {
  const [actual, setActual] = useState('resumen')
  const [filtros, setFiltros] = useState({ it: '', mes: '' })
  const [version, setVersion] = useState(0) // sube al cambiar un parámetro: obliga a recargar los datos
  const seccion = SECCIONES.find((s) => s.id === actual)
  const institutos = useDatos(() => api.institutos(), [version])
  const usaFiltros = actual !== 'parametros' && actual !== 'historial'

  return (
    <div className="min-h-screen bg-stone-50 text-slate-900">
      {/* Enlace para saltar directo al contenido con el teclado */}
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-10 focus:rounded focus:bg-white focus:px-4 focus:py-2 focus:font-semibold"
      >
        Saltar al contenido
      </a>

      {/* Barra superior: título, filtros globales (instituto y mes) y estado de conexión */}
      <header className="z-20 border-t-[6px] border-b border-t-teleton-600 border-b-slate-200 bg-white md:sticky md:top-0">
        <div className="flex flex-wrap items-end justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            {/* Corazón rojo como sello de la Teletón (decorativo) */}
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-teleton-600" aria-hidden="true">
              <Heart className="h-6 w-6 fill-white text-white" />
            </span>
            <div>
              <p className="text-sm font-semibold text-teleton-700">Teletón · Planificación asistencial 2026</p>
              <h1 className="text-2xl font-extrabold">Cada hora cuenta</h1>
            </div>
          </div>
          {usaFiltros && (
            <Filtros institutos={institutos.datos ?? []} it={filtros.it} mes={filtros.mes} onCambiar={setFiltros}
                     conMes={actual !== 'excepciones'} />
          )}
          <EstadoConexion />
        </div>
      </header>

      <div className="md:flex">
        {/* Barra lateral de navegación: en pantallas chicas queda como una fila arriba del contenido */}
        <aside className="border-b border-slate-200 bg-white md:sticky md:top-[94px] md:h-[calc(100vh-94px)] md:w-60 md:shrink-0 md:border-r md:border-b-0">
          <nav aria-label="Secciones" className="p-3">
            <ul className="flex gap-1 overflow-x-auto md:flex-col">
              {SECCIONES.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => setActual(s.id)}
                    aria-current={s.id === actual ? 'page' : undefined}
                    className={`flex w-full items-center gap-3 whitespace-nowrap rounded-md px-3 py-2 text-left text-base font-medium ${
                      s.id === actual ? 'bg-teleton-50 text-teleton-800 ring-1 ring-teleton-700' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {/* El ícono acompaña al texto: aria-hidden para que el lector de pantalla no lo repita */}
                    <s.Icono aria-hidden="true" className="h-5 w-5 shrink-0" />
                    {s.titulo}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
        </aside>

        <main id="contenido" tabIndex={-1} className="min-w-0 flex-1 space-y-6 px-4 py-6 md:px-8">
          <h2 className="text-xl font-bold">{seccion.titulo}</h2>
          <seccion.Componente
            filtros={filtros}
            institutos={institutos.datos ?? []}
            version={version}
            onRecalculado={() => setVersion((v) => v + 1)}
          />
        </main>
      </div>
    </div>
  )
}

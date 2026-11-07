import { useState } from 'react'
import { History, LayoutDashboard, SlidersHorizontal, TriangleAlert, Users } from 'lucide-react'
import { api } from './api.js'
import { useDatos } from './hooks.js'
import EstadoConexion from './components/EstadoConexion.jsx'
import Filtros from './components/Filtros.jsx'
import Resumen from './pages/Resumen.jsx'
import Profesionales from './pages/Profesionales.jsx'
import Excepciones from './pages/Excepciones.jsx'
import Parametros from './pages/Parametros.jsx'
import Historial from './pages/Historial.jsx'
import logoDuoc from './assets/logos/duocuc.png'
import logoTeleton from './assets/logos/teleton.png'
import logoTeletonRojo from './assets/logos/teleton_rojo.png'
import logoBluePrism from './assets/logos/blueprism.png'

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

      {/* Franja del evento: Botathon 2026 y los logos de las organizaciones */}
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 bg-teleton-700 px-4 py-2 text-white md:px-6">
        <p className="text-sm font-semibold">Botathon 2026 · Desafío Teletón</p>
        <ul className="flex flex-wrap items-center gap-x-6 gap-y-2" aria-label="Organizan">
          <li><img src={logoDuoc} alt="Duoc UC, Escuela de Informática y Telecomunicaciones" className="h-5 w-auto md:h-6" /></li>
          <li><img src={logoTeleton} alt="Teletón" className="h-6 w-auto md:h-7" /></li>
          <li><img src={logoBluePrism} alt="SS&C Blue Prism" className="h-5 w-auto md:h-6" /></li>
        </ul>
      </div>

      {/* Barra superior: título, filtros globales (instituto y mes) y estado de conexión */}
      <header className="z-20 border-b border-slate-200 bg-white md:sticky md:top-0">
        <div className="flex flex-wrap items-end justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            {/* Logo de la Teletón en rojo; la línea gris lo separa del título */}
            <img src={logoTeletonRojo} alt="" className="hidden h-11 w-auto border-r border-slate-300 pr-3 sm:block" />
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

      <div className="flex">
        {/* Barra lateral de navegación, siempre a la izquierda.
            En pantallas angostas muestra solo los íconos; desde 768 px, ícono y texto. */}
        <aside className="sticky top-0 h-screen w-16 shrink-0 self-start border-r border-slate-200 bg-white md:top-[88px] md:h-[calc(100vh-88px)] md:w-60">
          <nav aria-label="Secciones" className="p-2 md:p-3">
            <ul className="flex flex-col gap-1">
              {SECCIONES.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => setActual(s.id)}
                    aria-current={s.id === actual ? 'page' : undefined}
                    className={`group relative flex w-full items-center justify-center gap-3 whitespace-nowrap rounded-md px-3 py-2 text-left text-base font-medium md:justify-start ${
                      s.id === actual ? 'bg-teleton-50 text-teleton-800 ring-1 ring-teleton-700' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {/* El ícono acompaña al texto: aria-hidden para que el lector de pantalla no lo repita */}
                    <s.Icono aria-hidden="true" className="h-5 w-5 shrink-0" />
                    {/* En pantallas angostas el texto queda oculto a la vista, pero el lector de pantalla lo lee */}
                    <span className="sr-only md:not-sr-only">{s.titulo}</span>
                    {/* Etiqueta flotante: aparece al pasar el cursor o al llegar con el teclado (solo con la barra angosta) */}
                    <span
                      aria-hidden="true"
                      className="pointer-events-none absolute left-full top-1/2 z-30 ml-3 hidden -translate-y-1/2 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white shadow-lg group-hover:block group-focus-visible:block md:!hidden"
                    >
                      {s.titulo}
                    </span>
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

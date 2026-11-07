import { Activity, Gauge, Target, Users } from 'lucide-react'
import { api, MESES, numero, porcentaje } from '../api.js'
import { useDatos } from '../hooks.js'
import GraficoBarras from '../components/GraficoBarras.jsx'
import GraficoDona from '../components/GraficoDona.jsx'
import { Cargando, MensajeError, SinPlanificacion } from '../components/Estados.jsx'

// Indicadores del consolidado (nacional o del instituto elegido) y gráfico por instituto
export default function Resumen({ filtros, institutos, version }) {
  const kpis = useDatos(() => api.kpis(filtros), [filtros.it, filtros.mes, version])
  const porInstituto = useDatos(() => api.institutos(filtros.mes), [filtros.mes, version])

  if (kpis.cargando && !kpis.datos) return <Cargando />
  if (kpis.sinDatos) return <SinPlanificacion />
  if (kpis.error) return <MensajeError texto={kpis.error} />
  const k = kpis.datos

  const lugar = filtros.it ? (institutos.find((i) => String(i.it) === String(filtros.it))?.instituto ?? 'el instituto') : 'todo el país'
  const periodo = filtros.mes ? `en ${MESES[filtros.mes - 1]}` : 'en el año 2026'

  const indicadores = [
    { titulo: 'Meta de gestión', Icono: Target, valor: numero(k.meta_gestion), explicacion: `${numero(k.meta_directa)} de atención directa` },
    { titulo: 'Atenciones planificadas', Icono: Activity, valor: numero(k.atenciones_planificadas), explicacion: `${numero(k.atenciones_directas)} directas` },
    { titulo: 'FOJA', Icono: Gauge, valor: porcentaje(k.foja_promedio), explicacion: 'Horas para atención directa ÷ horas contratadas' },
    { titulo: 'Profesionales', Icono: Users, valor: numero(k.profesionales), explicacion: `${numero(k.horas_contratadas_mes)} horas contratadas` },
  ]

  return (
    <div className="space-y-8">
      {/* Resumen en lenguaje simple (criterio de accesibilidad del jurado) */}
      <section aria-labelledby="titulo-en-palabras" className="rounded-lg border border-slate-200 bg-white p-4">
        <h3 id="titulo-en-palabras" className="font-semibold">En palabras simples</h3>
        <p className="mt-2 text-slate-800">
          En {lugar}, {periodo}, {numero(k.profesionales)} profesionales tienen planificadas{' '}
          {numero(k.atenciones_planificadas)} atenciones. La meta de gestión es {numero(k.meta_gestion)} atenciones.
          De cada 100 horas contratadas, {Math.round((k.foja_promedio ?? 0) * 100)} van a atención directa con pacientes.
        </p>
      </section>

      <section aria-labelledby="titulo-indicadores">
        <h3 id="titulo-indicadores" className="sr-only">Indicadores</h3>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {indicadores.map((ind) => (
            <li key={ind.titulo} className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-slate-700">
                <ind.Icono aria-hidden="true" className="h-5 w-5 text-blue-700" />
                {ind.titulo}
              </p>
              <p className="mt-1 text-3xl font-bold">{ind.valor}</p>
              <p className="mt-1 text-sm text-slate-600">{ind.explicacion}</p>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-sm text-slate-600">
          Versión del cálculo {k.version_id} · actualizada {k.actualizado_en} · {numero(k.registros_con_observaciones)} registros con
          observaciones (ver Excepciones).
        </p>
      </section>

      {/* Colores con buen contraste sobre blanco; el texto de la leyenda no depende del color */}
      <GraficoDona
        titulo={`Distribución de las horas disponibles ${periodo}`}
        datos={[
          { nombre: 'Atención directa', valor: k.horas_directas_mes, color: '#1d4ed8' },
          { nombre: 'Atención indirecta', valor: k.horas_indirectas_mes, color: '#0f766e' },
          { nombre: 'No asistencial (NAS)', valor: k.horas_nas_mes, color: '#b45309' },
        ]}
      />

      <GraficoBarras
        titulo={`Atenciones planificadas por instituto ${periodo}`}
        datos={(porInstituto.datos ?? []).map((i) => ({ Instituto: i.instituto, atenciones: i.atenciones_planificadas }))}
        campoEtiqueta="Instituto"
        campoValor="atenciones"
        nombreValor="Atenciones"
      />
    </div>
  )
}

import { useEffect, useState } from 'react'
import { SinDatos } from './api.js'

// Pide datos al backend y devuelve { datos, cargando, error, sinDatos }.
// Se vuelve a pedir cada vez que cambia algo de «dependencias» (filtros o versión del cálculo).
export function useDatos(funcion, dependencias) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: '', sinDatos: false })

  useEffect(() => {
    let vigente = true
    setEstado((e) => ({ ...e, cargando: true, error: '' }))
    funcion()
      .then((datos) => vigente && setEstado({ datos, cargando: false, error: '', sinDatos: false }))
      .catch((e) =>
        vigente &&
        setEstado({ datos: null, cargando: false, error: e instanceof SinDatos ? '' : e.message, sinDatos: e instanceof SinDatos }),
      )
    return () => {
      vigente = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias)

  return estado
}

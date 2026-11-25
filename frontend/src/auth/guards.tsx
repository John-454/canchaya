/** Guardas de ruta por estado de sesión y rol. */

import { Navigate, useLocation } from 'react-router-dom'

import type { Rol } from '../api/types'
import { useAuth } from '../auth/AuthProvider'
import { Cargando } from '../components/estados'
import { SinPermiso } from '../components/SinPermiso'

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { estado } = useAuth()
  const location = useLocation()

  if (estado === 'cargando') return <Cargando mensaje="Verificando sesión…" />
  if (estado === 'anonimo') return <Navigate to="/login" replace state={{ from: location }} />
  return <>{children}</>
}

export function RequireRol({ rol, children }: { rol: Rol; children: React.ReactNode }) {
  const { estado, perfil } = useAuth()

  if (estado === 'cargando') return <Cargando mensaje="Verificando permisos…" />
  if (estado === 'anonimo') return <Navigate to="/login" replace />
  if (perfil?.rol !== rol) return <SinPermiso rolRequerido={rol} />
  return <>{children}</>
}

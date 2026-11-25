import { Link } from 'react-router-dom'

import type { Rol } from '../api/types'
import { useAuth } from '../auth/AuthProvider'

export function SinPermiso({ rolRequerido }: { rolRequerido: Rol }) {
  const { perfil, logout } = useAuth()
  return (
    <div className="mx-auto max-w-lg p-8" role="alert">
      <div className="rounded-card border border-brand-line bg-white p-8 shadow-card">
        <h1 className="text-xl font-semibold text-brand-dark">Acceso restringido</h1>
        <p className="mt-2 text-brand-muted">
          Esta sección requiere el rol <strong>{rolRequerido}</strong>. Tu cuenta es{' '}
          <strong>{perfil?.rol ?? 'desconocido'}</strong>.
        </p>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={() => void logout()}
            className="rounded-lg bg-brand-dark px-4 py-2 text-sm text-white"
          >
            Cerrar sesión
          </button>
          <Link to="/" className="rounded-lg border border-brand-line px-4 py-2 text-sm">
            Volver
          </Link>
        </div>
      </div>
    </div>
  )
}

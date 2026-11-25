/** Estados de UI reutilizables: carga, vacío y error tipado. */

import type { ReactNode } from 'react'

import { ApiError } from '../lib/api'

export function Cargando({ mensaje = 'Cargando…' }: { mensaje?: string }) {
  return (
    <div className="flex items-center gap-3 p-8 text-brand-muted" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-line border-t-brand-action" />
      {mensaje}
    </div>
  )
}

export function Vacio({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-brand-line bg-white p-10 text-center">
      <p className="font-medium text-brand-dark">{titulo}</p>
      {children ? <div className="mt-2 text-sm text-brand-muted">{children}</div> : null}
    </div>
  )
}

interface PropsError {
  error: unknown
  onReintentar?: () => void
}

export function ErrorApi({ error, onReintentar }: PropsError) {
  const esApi = error instanceof ApiError
  const status = esApi ? error.status : 0
  const mensaje = esApi ? error.mensajeUsuario : 'No pudimos conectar con el servidor.'

  return (
    <div
      className="rounded-card border border-red-200 bg-red-50 p-6"
      role="alert"
      data-testid={`error-api-${status}`}
    >
      <p className="font-semibold text-red-900">{mensaje}</p>
      {esApi ? (
        <p className="mt-1 text-sm text-red-700">
          Código: <code>{error.code}</code> · HTTP {error.status}
        </p>
      ) : null}
      {onReintentar ? (
        <button
          type="button"
          onClick={onReintentar}
          className="mt-3 rounded-lg bg-brand-dark px-3 py-1.5 text-sm text-white hover:bg-brand-darkAlt"
        >
          Reintentar
        </button>
      ) : null}
    </div>
  )
}

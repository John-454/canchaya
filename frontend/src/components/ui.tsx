/** Componentes base del design system (tokens de Canva). */

import type { ReactNode } from 'react'

export function Card({
  titulo,
  acciones,
  children,
  className = '',
}: {
  titulo?: string
  acciones?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-card border border-brand-line bg-white shadow-card ${className}`}>
      {titulo || acciones ? (
        <header className="flex items-center justify-between gap-4 border-b border-brand-line px-5 py-4">
          {titulo ? <h2 className="font-semibold text-brand-dark">{titulo}</h2> : <span />}
          {acciones}
        </header>
      ) : null}
      <div className="p-5">{children}</div>
    </section>
  )
}

const ESTILOS_BADGE: Record<string, string> = {
  Pendiente: 'bg-amber-100 text-amber-800',
  Confirmada: 'bg-brand-actionSoft text-brand-actionHover',
  Cancelada: 'bg-slate-200 text-slate-700',
  Finalizada: 'bg-sky-100 text-sky-800',
  Pagado: 'bg-brand-actionSoft text-brand-actionHover',
  true: 'bg-brand-actionSoft text-brand-actionHover',
  false: 'bg-slate-200 text-slate-700',
}

export function Badge({ children }: { children: string }) {
  const estilo = ESTILOS_BADGE[children] ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${estilo}`}>
      {children}
    </span>
  )
}

export function Boton({
  children,
  onClick,
  tipo = 'button',
  variante = 'primario',
  disabled,
  cargando,
  className = '',
}: {
  children: ReactNode
  onClick?: () => void
  tipo?: 'button' | 'submit'
  variante?: 'primario' | 'secundario' | 'peligro' | 'fantasma'
  disabled?: boolean
  cargando?: boolean
  className?: string
}) {
  const estilos = {
    primario: 'bg-brand-action text-white hover:bg-brand-actionHover',
    secundario: 'border border-brand-line bg-white text-brand-dark hover:bg-brand-bg',
    peligro: 'bg-red-600 text-white hover:bg-red-700',
    fantasma: 'text-brand-action hover:underline',
  }[variante]

  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={disabled || cargando}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${estilos} ${className}`}
    >
      {cargando ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
      ) : null}
      {children}
    </button>
  )
}

export function Campo({
  etiqueta,
  error,
  children,
  ayuda,
}: {
  etiqueta: string
  error?: string
  ayuda?: string
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-brand-dark">{etiqueta}</span>
      {children}
      {ayuda && !error ? <span className="mt-1 block text-xs text-brand-muted">{ayuda}</span> : null}
      {error ? (
        <span className="mt-1 block text-xs text-red-600" role="alert">
          {error}
        </span>
      ) : null}
    </label>
  )
}

export const clasesInput =
  'w-full rounded-lg border border-brand-line bg-white px-3 py-2 text-sm text-brand-dark outline-none focus:border-brand-action focus:ring-2 focus:ring-brand-actionSoft'

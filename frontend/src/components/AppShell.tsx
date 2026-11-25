/** Layout del panel: barra lateral oscura + cabecera. */

import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import { Boton } from './ui'

const NAVEGACION = [
  { to: '/panel', etiqueta: 'Dashboard', exacto: true },
  { to: '/panel/cancha', etiqueta: 'Mi cancha' },
  { to: '/panel/fotografias', etiqueta: 'Fotografías' },
  { to: '/panel/horarios', etiqueta: 'Horarios' },
  { to: '/panel/tarifas', etiqueta: 'Tarifas' },
  { to: '/panel/reservas', etiqueta: 'Reservas' },
  { to: '/panel/calendario', etiqueta: 'Calendario' },
  { to: '/panel/contabilidad', etiqueta: 'Contabilidad' },
]

export function AppShell() {
  const { perfil, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-brand-bg">
      <aside className="hidden w-60 shrink-0 flex-col bg-brand-dark p-5 text-white lg:flex">
        <div className="mb-8">
          <p className="text-xl font-bold tracking-tight">
            canchaya<span className="text-brand-action">.</span>
          </p>
          <p className="text-xs text-white/60">Panel del propietario</p>
        </div>
        <nav className="flex flex-col gap-1" aria-label="Navegación principal">
          {NAVEGACION.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exacto}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-brand-action text-white'
                    : 'text-white/75 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              {item.etiqueta}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto pt-6 text-xs text-white/50">
          <p className="truncate">{perfil?.nombre}</p>
          <p className="truncate">{perfil?.correo}</p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-brand-line bg-white px-6 py-3">
          <p className="font-medium text-brand-dark lg:hidden">canchaya.</p>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-brand-muted sm:inline">{perfil?.correo}</span>
            <Boton variante="secundario" onClick={() => void logout()}>
              Salir
            </Boton>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

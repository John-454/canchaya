/** Enrutador: login público + panel protegido por rol `administrador`. */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { ApiError } from './lib/api'
import { AuthProvider } from './auth/AuthProvider'
import { RequireAuth, RequireRol } from './auth/guards'
import { AppShell } from './components/AppShell'
import { CalendarioPage } from './pages/CalendarioPage'
import { ContabilidadPage } from './pages/ContabilidadPage'
import { DashboardPage } from './pages/DashboardPage'
import { FotografiasPage } from './pages/FotografiasPage'
import { HorariosPage } from './pages/HorariosPage'
import { LoginPage } from './pages/LoginPage'
import { MiCanchaPage } from './pages/MiCanchaPage'
import { ReservasPage } from './pages/ReservasPage'
import { TarifasPage } from './pages/TarifasPage'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Reintenta solo errores de red/5xx; 4xx no tiene sentido reintentarlos.
      retry: (intentos, error) =>
        error instanceof ApiError ? error.status >= 500 && intentos < 2 : intentos < 2,
      staleTime: 15_000,
      refetchOnWindowFocus: false,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/panel"
              element={
                <RequireAuth>
                  <RequireRol rol="administrador">
                    <AppShell />
                  </RequireRol>
                </RequireAuth>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="cancha" element={<MiCanchaPage />} />
              <Route path="fotografias" element={<FotografiasPage />} />
              <Route path="horarios" element={<HorariosPage />} />
              <Route path="tarifas" element={<TarifasPage />} />
              <Route path="reservas" element={<ReservasPage />} />
              <Route path="calendario" element={<CalendarioPage />} />
              <Route path="contabilidad" element={<ContabilidadPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/panel" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

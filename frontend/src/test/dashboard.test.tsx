import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DashboardPage } from '../pages/DashboardPage'
import { mockFetch, renderConProviders } from './utils'

const DASHBOARD = {
  kpis: {
    reservas_hoy: 3,
    pendientes_hoy: 1,
    confirmadas_hoy: 1,
    canceladas_hoy: 1,
    por_aprobar: 2,
    ingresos_recibidos: '160000.00',
    dinero_pendiente: '100000.00',
  },
  serie_actividad: [{ fecha: '2026-12-01', reservas: 2 }],
  serie_ingresos: [{ mes: '2026-12', ingresos_recibidos: '160000.00' }],
  solicitudes_por_aprobar: [
    {
      id_reserva: 7,
      codigo_reserva: 'CY-261201-AAAA',
      fecha_reserva: '2026-12-02',
      hora_inicio: '08:00',
      hora_fin: '09:00',
      nombre_cliente: 'Ana Pérez',
      precio_total: '60000.00',
    },
  ],
  proximos_partidos: [],
}

describe('DashboardPage', () => {
  it('pinta los KPIs y las solicitudes por aprobar', async () => {
    mockFetch({ '/admin/finance/dashboard/': { body: DASHBOARD } })
    renderConProviders(<DashboardPage />)

    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument()
    expect(screen.getByText('Reservas hoy')).toBeInTheDocument()
    expect(screen.getAllByText(/160\.000/).length).toBeGreaterThan(0)
  })

  it('muestra el estado vacío cuando no hay partidos ni solicitudes', async () => {
    mockFetch({
      '/admin/finance/dashboard/': {
        body: { ...DASHBOARD, solicitudes_por_aprobar: [], proximos_partidos: [] },
      },
    })
    renderConProviders(<DashboardPage />)

    expect(await screen.findByText(/No hay solicitudes pendientes/)).toBeInTheDocument()
    expect(screen.getByText(/No hay partidos confirmados/)).toBeInTheDocument()
  })

  it('aprueba una solicitud y refresca los datos', async () => {
    const fetchMock = mockFetch({
      '/admin/bookings/7/approve/': { body: { id_reserva: 7, estado_reserva: 'Confirmada' } },
      '/admin/finance/dashboard/': { body: DASHBOARD },
    })
    renderConProviders(<DashboardPage />)

    const boton = await screen.findByRole('button', { name: 'Aprobar' })
    await userEvent.click(boton)

    await waitFor(() => {
      const llamadas = fetchMock.mock.calls.map((c) => String(c[0]))
      expect(llamadas.some((u) => u.includes('/admin/bookings/7/approve/'))).toBe(true)
    })
  })

  it('muestra el error 403 admin_sin_cancha', async () => {
    mockFetch({
      '/admin/finance/dashboard/': {
        status: 403,
        body: { code: 'admin_sin_cancha', detail: 'Sin cancha' },
      },
    })
    renderConProviders(<DashboardPage />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/no tiene una cancha/)
  })

  it('muestra el error 401 y permite reintentar', async () => {
    const fetchMock = mockFetch({
      '/admin/finance/dashboard/': { status: 401, body: { code: 'token_expirado', detail: 'x' } },
    })
    renderConProviders(<DashboardPage />)

    const alerta = await screen.findByRole('alert')
    expect(alerta).toBeInTheDocument()
    const antes = fetchMock.mock.calls.length
    await userEvent.click(screen.getByRole('button', { name: /reintentar/i }))
    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(antes))
  })

  it('marca error inesperado si falla la red', async () => {
    const original = globalThis.fetch
    globalThis.fetch = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    }) as unknown as typeof fetch
    try {
      renderConProviders(<DashboardPage />)
      expect(await screen.findByRole('alert')).toHaveTextContent(/No pudimos conectar/)
    } finally {
      globalThis.fetch = original
    }
  })
})

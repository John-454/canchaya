import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { ReservasPage } from '../pages/ReservasPage'
import { mockFetch, renderConProviders } from './utils'

const RESERVA = {
  id_reserva: 5,
  codigo_reserva: 'CY-261201-AAAA',
  fecha_reserva: '2026-12-02',
  hora_inicio: '08:00:00',
  hora_fin: '10:00:00',
  precio_total: '120000.00',
  estado_reserva: 'Pendiente',
  estado_pago: 'Pendiente',
  fecha_pago: null,
  observaciones: '',
  fecha_creacion: '2026-12-01T10:00:00Z',
  cliente: {
    id_cliente: 2,
    nombre: 'Ana Pérez',
    correo: 'ana@canchaya.test',
    telefono: '+573001112233',
  },
}

const LISTADO = { count: 1, next: null, previous: null, results: [RESERVA] }

describe('ReservasPage', () => {
  it('lista reservas con estado y pago', async () => {
    mockFetch({ '/admin/bookings/': { body: LISTADO } })
    renderConProviders(<ReservasPage />)

    expect(await screen.findByText('CY-261201-AAAA')).toBeInTheDocument()
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument()
    expect(screen.getAllByText('Pendiente').length).toBeGreaterThanOrEqual(2)
  })

  it('abre el detalle y aprueba la reserva', async () => {
    mockFetch({
      '/admin/bookings/5/approve/': { body: { ...RESERVA, estado_reserva: 'Confirmada' } },
      '/admin/bookings/': { body: LISTADO },
    })
    renderConProviders(<ReservasPage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Ver' }))
    const dialogo = await screen.findByRole('dialog')
    expect(dialogo).toHaveTextContent('+573001112233')

    await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
    // La respuesta actualiza la reserva seleccionada sin cerrar el panel.
    await screen.findByRole('dialog')
  })

  it('muestra 409 estado_invalido al aprobar una reserva ya cambiada', async () => {
    mockFetch({
      '/admin/bookings/5/approve/': {
        status: 409,
        body: { code: 'estado_invalido', detail: 'x' },
      },
      '/admin/bookings/': { body: LISTADO },
    })
    renderConProviders(<ReservasPage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Ver' }))
    await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
    expect(await screen.findByTestId('error-api-409')).toHaveTextContent(/cambió de estado/)
  })

  it('muestra el vacío cuando no hay resultados', async () => {
    mockFetch({
      '/admin/bookings/': { body: { count: 0, next: null, previous: null, results: [] } },
    })
    renderConProviders(<ReservasPage />)
    expect(await screen.findByText(/No hay reservas con estos filtros/)).toBeInTheDocument()
  })

  it('pagina cuando hay siguiente página', async () => {
    const espia = mockFetch({
      '/admin/bookings/': {
        body: { ...LISTADO, count: 40, next: 'http://x/?page=2' },
      },
    })
    renderConProviders(<ReservasPage />)
    await screen.findByText('CY-261201-AAAA')
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    const llamadas = espia.mock.calls.map((c) => String(c[0]))
    expect(llamadas.some((u) => u.includes('page=2'))).toBe(true)
  })
})

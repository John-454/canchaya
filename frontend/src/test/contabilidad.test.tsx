import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ContabilidadPage } from '../pages/ContabilidadPage'
import { mockFetch, renderConProviders } from './utils'

const RESUMEN = {
  periodo: 'month',
  inicio: '2026-12-01',
  fin: '2026-12-31',
  ingresos_recibidos: '160000.00',
  dinero_pendiente: '100000.00',
  total_reservas: 4,
  reservas_pagadas: 2,
  reservas_pendientes_pago: 2,
  por_dia: [{ fecha: '2026-12-01', ingresos_recibidos: '160000.00', dinero_pendiente: '0.00', reservas: 2 }],
  historial: [
    {
      id_reserva: 9,
      codigo_reserva: 'CY-261201-BBBB',
      fecha_reserva: '2026-12-01',
      hora_inicio: '08:00',
      hora_fin: '09:00',
      nombre_cliente: 'Luis Gómez',
      precio_total: '60000.00',
      estado_reserva: 'Confirmada',
      estado_pago: 'Pagado',
      fecha_pago: '2026-12-01T14:00:00Z',
    },
  ],
}

describe('ContabilidadPage', () => {
  it('muestra ingresos, pendiente y el historial', async () => {
    mockFetch({ '/admin/finance/summary/': { body: RESUMEN } })
    renderConProviders(<ContabilidadPage />)

    expect(await screen.findByText('Ingresos recibidos')).toBeInTheDocument()
    expect(screen.getAllByText(/160\.000/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/100\.000/).length).toBeGreaterThan(0)
    expect(screen.getByText('CY-261201-BBBB')).toBeInTheDocument()
    expect(screen.getByText('2 / 2')).toBeInTheDocument()
  })

  it('muestra 400 al pedir un rango personalizado inválido', async () => {
    mockFetch({
      '/admin/finance/summary/': {
        status: 400,
        body: { code: 'parametros_invalidos', detail: 'start no puede ser posterior a end' },
      },
    })
    renderConProviders(<ContabilidadPage />)
    expect(await screen.findByTestId('error-api-400')).toBeInTheDocument()
  })
})

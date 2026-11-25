import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { HorariosPage } from '../pages/HorariosPage'
import { TarifasPage } from '../pages/TarifasPage'
import { mockFetch, renderConProviders } from './utils'

describe('HorariosPage', () => {
  it('lista las franjas por día', async () => {
    mockFetch({
      '/admin/field/schedules/': {
        body: [
          {
            id_horario: 1,
            dia_semana: 1,
            hora_apertura: '08:00:00',
            hora_cierre: '12:00:00',
            activo: true,
          },
        ],
      },
    })
    renderConProviders(<HorariosPage />)
    expect(await screen.findByText('08:00 – 12:00')).toBeInTheDocument()
    expect(screen.getAllByText('Cerrado').length).toBe(6)
  })

  it('muestra el 409 horario_solapado al crear', async () => {
    // GET del listado OK; el POST de creación devuelve 409.
    const fetchFalso = async (_input: RequestInfo | URL, init?: RequestInit) => {
      const esPost = (init?.method ?? 'GET').toUpperCase() === 'POST'
      const cuerpo = esPost
        ? { code: 'horario_solapado', detail: 'x' }
        : []
      const status = esPost ? 409 : 200
      return new Response(JSON.stringify(cuerpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    globalThis.fetch = fetchFalso as unknown as typeof fetch

    renderConProviders(<HorariosPage />)
    const boton = await screen.findByRole('button', { name: /Agregar/ })
    await userEvent.click(boton)
    expect(await screen.findByTestId('error-api-409')).toHaveTextContent(/se solapa/)
  })
})

describe('TarifasPage', () => {
  it('separa semanales y fechas especiales', async () => {
    mockFetch({
      '/admin/field/rates/': {
        body: [
          {
            id_tarifa: 1,
            dia_semana: 2,
            fecha_especial: null,
            hora_inicio: '08:00:00',
            hora_fin: '10:00:00',
            precio_hora: '70000.00',
            activo: true,
            origen: 'semanal',
          },
          {
            id_tarifa: 2,
            dia_semana: null,
            fecha_especial: '2026-12-24',
            hora_inicio: '08:00:00',
            hora_fin: '12:00:00',
            precio_hora: '95000.00',
            activo: true,
            origen: 'especial',
          },
        ],
      },
    })
    renderConProviders(<TarifasPage />)

    expect(await screen.findByText(/Martes · 08:00–10:00/)).toBeInTheDocument()
    expect(screen.getByText(/2026-12-24 · 08:00–12:00/)).toBeInTheDocument()
  })

  it('muestra la vista previa con el origen del precio', async () => {
    mockFetch({
      '/admin/field/rates/preview/': {
        body: {
          fecha: '2026-12-01',
          dia_semana: 2,
          precio_base: '60000.00',
          bloques: [
            { hora_inicio: '08:00', hora_fin: '09:00', precio: '70000.00', origen: 'semanal' },
            { hora_inicio: '09:00', hora_fin: '10:00', precio: '99000.00', origen: 'especial' },
            { hora_inicio: '10:00', hora_fin: '11:00', precio: '60000.00', origen: 'base' },
          ],
        },
      },
      '/admin/field/rates/': { body: [] },
    })
    renderConProviders(<TarifasPage />)

    await userEvent.click(await screen.findByRole('button', { name: 'Consultar' }))

    expect(await screen.findByText('Tarifa semanal', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('Fecha especial', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('Precio base')).toBeInTheDocument()
  })
})

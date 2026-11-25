import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ErrorApi, Vacio } from '../components/estados'
import { ApiError } from '../lib/api'

describe('ErrorApi', () => {
  it('muestra el mensaje de negocio y el código para admin sin cancha (403)', () => {
    render(<ErrorApi error={new ApiError(403, 'admin_sin_cancha', 'x')} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/no tiene una cancha/)
    expect(screen.getByTestId('error-api-403')).toBeInTheDocument()
    expect(screen.getByText('admin_sin_cancha')).toBeInTheDocument()
  })

  it('muestra rol requerido (403)', () => {
    render(<ErrorApi error={new ApiError(403, 'rol_requerido', 'x')} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/exclusiva para administradores/)
  })

  it('muestra el solape de tarifas (409)', () => {
    render(<ErrorApi error={new ApiError(409, 'tarifa_solapada', 'x')} />)
    expect(screen.getByTestId('error-api-409')).toHaveTextContent(/se solapa con otra activa/)
  })

  it('muestra errores de validación (400)', () => {
    render(<ErrorApi error={new ApiError(400, 'bloque_no_alineado', 'x')} />)
    expect(screen.getByTestId('error-api-400')).toHaveTextContent(/en punto/)
  })

  it('cae a un mensaje genérico para errores de red', () => {
    render(<ErrorApi error={new Error('ECONNREFUSED')} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/No pudimos conectar/)
  })

  it('ofrece reintentar', () => {
    let reintentos = 0
    render(
      <ErrorApi
        error={new ApiError(500, 'error', 'x')}
        onReintentar={() => {
          reintentos += 1
        }}
      />,
    )
    screen.getByRole('button', { name: /reintentar/i }).click()
    expect(reintentos).toBe(1)
  })
})

describe('Vacio', () => {
  it('muestra el título y el contenido', () => {
    render(<Vacio titulo="Sin datos">Agrega uno</Vacio>)
    expect(screen.getByText('Sin datos')).toBeInTheDocument()
    expect(screen.getByText('Agrega uno')).toBeInTheDocument()
  })
})

import { describe, expect, it } from 'vitest'

import { ApiError } from '../lib/api'

describe('ApiError', () => {
  it('traduce los códigos de negocio a mensajes de usuario', () => {
    expect(new ApiError(403, 'admin_sin_cancha', 'x').mensajeUsuario).toMatch(/no tiene una cancha/)
    expect(new ApiError(403, 'rol_requerido', 'x').mensajeUsuario).toMatch(/exclusiva para administradores/)
    expect(new ApiError(409, 'horario_solapado', 'x').mensajeUsuario).toMatch(/se solapa/)
    expect(new ApiError(409, 'tarifa_solapada', 'x').mensajeUsuario).toMatch(/se solapa/)
    expect(new ApiError(409, 'estado_invalido', 'x').mensajeUsuario).toMatch(/cambió de estado/)
    expect(new ApiError(400, 'telefono_invalido', 'x').mensajeUsuario).toMatch(/10 dígitos/)
    expect(new ApiError(400, 'fuera_de_horario', 'x').mensajeUsuario).toMatch(/fuera del horario/)
  })

  it('conserva status, code y errors', () => {
    const e = new ApiError(409, 'horario_solapado', 'detalle', { hora: 'x' })
    expect(e.status).toBe(409)
    expect(e.code).toBe('horario_solapado')
    expect(e.errors).toEqual({ hora: 'x' })
  })

  it('cae al detalle cuando el código es desconocido', () => {
    expect(new ApiError(500, 'boom', 'Falla interna').mensajeUsuario).toBe('Falla interna')
  })
})

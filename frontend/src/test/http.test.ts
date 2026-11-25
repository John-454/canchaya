import { describe, expect, it } from 'vitest'

import { api, ApiError, setTokenProvider } from '../lib/api'
import { mockFetch } from './utils'

describe('cliente HTTP', () => {
  it('envía el Bearer token de Supabase', async () => {
    const espia = mockFetch({ '/auth/me/': { body: { correo: 'a@b.co' } } })
    setTokenProvider(async () => 'token-123')

    await api.get('/auth/me/')

    const llamada = espia.mock.calls[0] as unknown as [RequestInfo | URL, RequestInit?]
    expect(String(llamada[0])).toContain('/auth/me/')
    const headers = new Headers(llamada[1]?.headers)
    expect(headers.get('Authorization')).toBe('Bearer token-123')
  })

  it('normaliza errores del backend a ApiError', async () => {
    mockFetch({
      '/admin/field/schedules/': {
        status: 409,
        body: { code: 'horario_solapado', detail: 'Se solapa' },
      },
    })
    setTokenProvider(async () => 't')

    await expect(api.post('/admin/field/schedules/', {})).rejects.toMatchObject({
      status: 409,
      code: 'horario_solapado',
    })
  })

  it('serializa los filtros como query string e ignora vacíos', async () => {
    const espia = mockFetch({ '/admin/bookings/': { body: { results: [] } } })
    setTokenProvider(async () => 't')

    await api.get('/admin/bookings/', { fecha: '2026-12-01', cliente: '', page: 2 })

    const url = String(espia.mock.calls[0][0])
    expect(url).toContain('fecha=2026-12-01')
    expect(url).toContain('page=2')
    expect(url).not.toContain('cliente=')
  })

  it('reintenta una vez ante un 401 (token refrescado)', async () => {
    let llamadas = 0
    const fetchFalso = async () => {
      llamadas += 1
      const cuerpo = llamadas === 1 ? { code: 'token_expirado', detail: 'x' } : { ok: true }
      const status = llamadas === 1 ? 401 : 200
      return new Response(JSON.stringify(cuerpo), {
        status,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    const original = globalThis.fetch
    globalThis.fetch = fetchFalso as unknown as typeof fetch
    setTokenProvider(async () => 't')
    try {
      const datos = await api.get<{ ok: boolean }>('/auth/me/')
      expect(datos.ok).toBe(true)
      expect(llamadas).toBe(2)
    } finally {
      globalThis.fetch = original
    }
  })

  it('devuelve undefined en 204', async () => {
    mockFetch({ '/admin/field/images/1/': { status: 204, body: null } })
    setTokenProvider(async () => 't')
    await expect(api.delete('/admin/field/images/1/')).resolves.toBeUndefined()
  })

  it('marca como ApiError un 403 de rol', async () => {
    mockFetch({ '/admin/field/': { status: 403, body: { code: 'rol_requerido', detail: 'x' } } })
    setTokenProvider(async () => 't')
    const error = (await api.get('/admin/field/').catch((e) => e)) as ApiError
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(403)
  })
})

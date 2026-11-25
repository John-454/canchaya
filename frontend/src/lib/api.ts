/**
 * Cliente HTTP del panel.
 *
 * Responsabilidades:
 *  - Adjuntar el access token de Supabase en cada petición.
 *  - Refrescar la sesión una vez si el backend responde 401 `token_expirado`.
 *  - Normalizar TODOS los errores del backend a `ApiError` con `status` y
 *    `code`, para que la UI decida qué pintar.
 */

export type EstadoReserva = 'Pendiente' | 'Confirmada' | 'Cancelada' | 'Finalizada'
export type EstadoPago = 'Pendiente' | 'Pagado'

export interface ApiErrorBody {
  code?: string
  detail?: unknown
  errors?: Record<string, unknown>
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly errors: Record<string, unknown>

  constructor(status: number, code: string, message: string, errors: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.errors = errors
  }

  /** Mensaje orientado al usuario según el código de negocio. */
  get mensajeUsuario(): string {
    switch (this.code) {
      case 'admin_sin_cancha':
        return 'Tu cuenta de administrador no tiene una cancha asignada. Contacta al soporte.'
      case 'rol_requerido':
        return 'Esta sección es exclusiva para administradores.'
      case 'perfil_no_sincronizado':
        return 'Tu perfil aún no está sincronizado. Vuelve a iniciar sesión.'
      case 'cuenta_desactivada':
        return 'Tu cuenta está desactivada.'
      case 'token_expirado':
        return 'Tu sesión expiró. Inicia sesión de nuevo.'
      case 'horario_solapado':
        return 'Esa franja se solapa con otra que ya tienes configurada.'
      case 'tarifa_solapada':
        return 'Esa tarifa se solapa con otra activa del mismo tipo y hora.'
      case 'horario_no_disponible':
        return 'El horario ya no está disponible.'
      case 'estado_invalido':
        return 'La reserva cambió de estado; actualiza la lista.'
      case 'reserva_ya_pagada':
        return 'La reserva ya está registrada como pagada.'
      case 'telefono_invalido':
        return 'El teléfono no es válido (celular colombiano de 10 dígitos).'
      case 'bloque_no_alineado':
        return 'Las horas deben estar en punto (por ejemplo 08:00, no 08:30).'
      case 'fuera_de_horario':
        return 'El rango incluye un bloque fuera del horario de atención.'
      default:
        return this.message || 'Ocurrió un error inesperado.'
    }
  }
}

type TokenProvider = () => Promise<string | null>

let tokenProvider: TokenProvider = async () => null

/** El `AuthProvider` registra aquí cómo obtener (y refrescar) el token. */
export function setTokenProvider(provider: TokenProvider): void {
  tokenProvider = provider
}

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api/v1'

async function parseError(res: Response): Promise<ApiError> {
  let body: ApiErrorBody = {}
  try {
    body = (await res.json()) as ApiErrorBody
  } catch {
    /* respuesta sin JSON */
  }
  const detalle =
    typeof body.detail === 'string'
      ? body.detail
      : body.detail
        ? JSON.stringify(body.detail)
        : `Error ${res.status}`
  return new ApiError(res.status, body.code ?? 'error', detalle, body.errors ?? {})
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = await tokenProvider()
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${BASE}${path}`, { ...init, headers })

  if (res.status === 401 && retry) {
    // El proveedor ya refresca el token; se reintenta una sola vez.
    return request<T>(path, init, false)
  }
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => {
    const qs = params
      ? '?' +
        new URLSearchParams(
          Object.entries(params)
            .filter(([, v]) => v !== undefined && v !== null && v !== '')
            .map(([k, v]) => [k, String(v)]),
        ).toString()
      : ''
    return request<T>(`${path}${qs}`)
  },
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

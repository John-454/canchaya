/** Acceso tipado a los endpoints del panel (§5.2 – §5.4). */

import { api } from '../lib/api'
import type {
  Cancha,
  Dashboard,
  Horario,
  Imagen,
  Paginado,
  PreviewPrecios,
  Reserva,
  ResumenFinanciero,
  Tarifa,
  Usuario,
} from './types'

const FIELD = '/admin/field'
const BOOKINGS = '/admin/bookings'
const FINANCE = '/admin/finance'

export const authApi = {
  sync: () => api.post<Usuario>('/auth/sync/'),
  me: () => api.get<Usuario>('/auth/me/'),
  updatePerfil: (datos: { nombre?: string; telefono?: string }) =>
    api.patch<Usuario>('/auth/me/', datos),
}

export const canchaApi = {
  get: () => api.get<Cancha>(`${FIELD}/`),
  update: (datos: Partial<Cancha>) => api.patch<Cancha>(`${FIELD}/`, datos),
}

export const imagenesApi = {
  listar: () => api.get<Imagen[]>(`${FIELD}/images/`),
  crear: (datos: { url_imagen: string; descripcion?: string; imagen_principal?: boolean }) =>
    api.post<Imagen>(`${FIELD}/images/`, datos),
  actualizar: (id: number, datos: { descripcion?: string; imagen_principal?: boolean }) =>
    api.patch<Imagen>(`${FIELD}/images/${id}/`, datos),
  eliminar: (id: number) => api.delete<void>(`${FIELD}/images/${id}/`),
}

export const horariosApi = {
  listar: () => api.get<Horario[]>(`${FIELD}/schedules/`),
  crear: (datos: Omit<Horario, 'id_horario'>) => api.post<Horario>(`${FIELD}/schedules/`, datos),
  actualizar: (id: number, datos: Partial<Horario>) =>
    api.put<Horario>(`${FIELD}/schedules/${id}/`, datos),
  eliminar: (id: number) => api.delete<void>(`${FIELD}/schedules/${id}/`),
}

export const tarifasApi = {
  listar: () => api.get<Tarifa[]>(`${FIELD}/rates/`),
  crear: (datos: {
    dia_semana?: number | null
    fecha_especial?: string | null
    hora_inicio: string
    hora_fin: string
    precio_hora: string
    activo?: boolean
  }) => api.post<Tarifa>(`${FIELD}/rates/`, datos),
  actualizar: (id: number, datos: Partial<Tarifa>) =>
    api.patch<Tarifa>(`${FIELD}/rates/${id}/`, datos),
  eliminar: (id: number) => api.delete<void>(`${FIELD}/rates/${id}/`),
  preview: (fecha: string) => api.get<PreviewPrecios>(`${FIELD}/rates/preview/`, { fecha }),
}

export interface FiltrosReserva {
  fecha?: string
  estado_reserva?: string
  estado_pago?: string
  cliente?: string
  codigo_reserva?: string
  ordering?: string
  page?: number
}

export const reservasApi = {
  listar: (filtros: FiltrosReserva = {}) =>
    api.get<Paginado<Reserva>>(`${BOOKINGS}/`, { ...filtros }),
  detalle: (id: number) => api.get<Reserva>(`${BOOKINGS}/${id}/`),
  aprobar: (id: number) => api.post<Reserva>(`${BOOKINGS}/${id}/approve/`),
  cancelar: (id: number, motivo?: string) =>
    api.post<Reserva>(`${BOOKINGS}/${id}/cancel/`, motivo ? { motivo } : undefined),
  marcarPagado: (id: number) => api.post<Reserva>(`${BOOKINGS}/${id}/mark-paid/`),
}

export const finanzasApi = {
  dashboard: () => api.get<Dashboard>(`${FINANCE}/dashboard/`),
  summary: (params: { period: string; start?: string; end?: string }) =>
    api.get<ResumenFinanciero>(`${FINANCE}/summary/`, params),
}

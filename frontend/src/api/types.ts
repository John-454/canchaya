/** Tipos alineados con los serializers del backend (§5). */

export type Rol = 'cliente' | 'administrador'

export interface Usuario {
  id_usuario: number
  supabase_uid: string
  nombre: string
  correo: string
  telefono: string | null
  rol: Rol
  activo: boolean
  requiere_telefono: boolean
  fecha_creacion: string
}

export interface PerfilSync extends Usuario {
  creado: boolean
}

export interface Cancha {
  id_cancha: number
  nombre: string
  direccion: string
  zona: string | null
  descripcion: string
  precio_base: string
  estado: boolean
  fecha_creacion: string
}

export interface Imagen {
  id_imagen: number
  url_imagen: string
  descripcion: string
  imagen_principal: boolean
  fecha_creacion: string
}

export interface Horario {
  id_horario: number
  dia_semana: number
  hora_apertura: string
  hora_cierre: string
  activo: boolean
}

export type OrigenPrecio = 'base' | 'semanal' | 'especial'

export interface Tarifa {
  id_tarifa: number
  dia_semana: number | null
  fecha_especial: string | null
  hora_inicio: string
  hora_fin: string
  precio_hora: string
  activo: boolean
  origen: 'semanal' | 'especial'
}

export interface BloquePrecio {
  hora_inicio: string
  hora_fin: string
  precio: string
  origen: OrigenPrecio
}

export interface PreviewPrecios {
  fecha: string
  dia_semana: number
  precio_base: string
  bloques: BloquePrecio[]
}

export interface ClienteReserva {
  id_cliente: number
  nombre: string
  correo: string
  telefono: string
}

export interface Reserva {
  id_reserva: number
  codigo_reserva: string
  fecha_reserva: string
  hora_inicio: string
  hora_fin: string
  precio_total: string
  estado_reserva: 'Pendiente' | 'Confirmada' | 'Cancelada' | 'Finalizada'
  estado_pago: 'Pendiente' | 'Pagado'
  fecha_pago: string | null
  observaciones: string
  fecha_creacion: string
  cliente: ClienteReserva
}

export interface Paginado<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Kpis {
  reservas_hoy: number
  pendientes_hoy: number
  confirmadas_hoy: number
  canceladas_hoy: number
  por_aprobar: number
  ingresos_recibidos: string
  dinero_pendiente: string
}

export interface Dashboard {
  kpis: Kpis
  serie_actividad: { fecha: string; reservas: number }[]
  serie_ingresos: { mes: string; ingresos_recibidos: string }[]
  solicitudes_por_aprobar: {
    id_reserva: number
    codigo_reserva: string
    fecha_reserva: string
    hora_inicio: string
    hora_fin: string
    nombre_cliente: string
    precio_total: string
  }[]
  proximos_partidos: {
    id_reserva: number
    codigo_reserva: string
    fecha_reserva: string
    hora_inicio: string
    hora_fin: string
    nombre_cliente: string
    estado_pago: string
  }[]
}

export interface ResumenFinanciero {
  periodo: 'day' | 'week' | 'month' | 'custom'
  inicio: string
  fin: string
  ingresos_recibidos: string
  dinero_pendiente: string
  total_reservas: number
  reservas_pagadas: number
  reservas_pendientes_pago: number
  por_dia: {
    fecha: string
    ingresos_recibidos: string
    dinero_pendiente: string
    reservas: number
  }[]
  historial: {
    id_reserva: number
    codigo_reserva: string
    fecha_reserva: string
    hora_inicio: string
    hora_fin: string
    nombre_cliente: string
    precio_total: string
    estado_reserva: string
    estado_pago: string
    fecha_pago: string | null
  }[]
}

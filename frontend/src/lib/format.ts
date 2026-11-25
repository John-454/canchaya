/** Formato de moneda COP y utilidades de fecha (es-CO). */

const cop = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
})

export function formatoCOP(valor: string | number): string {
  const n = typeof valor === 'string' ? Number(valor) : valor
  if (Number.isNaN(n)) return '—'
  return cop.format(n)
}

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export function nombreDia(dia: number): string {
  return DIAS[dia - 1] ?? `Día ${dia}`
}

export const DIAS_SEMANA = DIAS.map((nombre, i) => ({ valor: i + 1, nombre }))

export function hoyISO(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function fechaLarga(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })
}

export function fechaCorta(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('es-CO', {
    day: '2-digit',
    month: 'short',
  })
}

/** "HH:MM:SS" -> "HH:MM" */
export function hhmm(hora: string): string {
  return hora.slice(0, 5)
}

export function sumarDias(iso: string, dias: number): string {
  const [y, m, d] = iso.split('-').map(Number)
  const fecha = new Date(y, m - 1, d + dias)
  return `${fecha.getFullYear()}-${String(fecha.getMonth() + 1).padStart(2, '0')}-${String(fecha.getDate()).padStart(2, '0')}`
}

/** Inicio de semana (lunes) para la vista de calendario. */
export function lunesDe(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  const fecha = new Date(y, m - 1, d)
  const desplazamiento = (fecha.getDay() + 6) % 7
  return sumarDias(iso, -desplazamiento)
}

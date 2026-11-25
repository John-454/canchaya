/** Claves de caché de React Query (un solo lugar para invalidar). */

export const queryKeys = {
  perfil: ['perfil'] as const,
  cancha: ['cancha'] as const,
  imagenes: ['imagenes'] as const,
  horarios: ['horarios'] as const,
  tarifas: ['tarifas'] as const,
  preview: (fecha: string) => ['preview', fecha] as const,
  reservas: (filtros: unknown) => ['reservas', filtros] as const,
  reserva: (id: number) => ['reserva', id] as const,
  dashboard: ['dashboard'] as const,
  summary: (params: unknown) => ['summary', params] as const,
  calendario: (lunes: string) => ['calendario', lunes] as const,
}

/** Datos que cambian cuando se mueve una reserva. */
export const KEYS_AFECTADAS_POR_RESERVA = [
  queryKeys.dashboard,
  ['reservas'],
  ['summary'],
] as const

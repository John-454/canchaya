/** Calendario semanal: 7 consultas en paralelo (una por día). */

import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { reservasApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import type { Reserva } from '../api/types'
import { fechaLarga, formatoCOP, hhmm, hoyISO, lunesDe, nombreDia, sumarDias } from '../lib/format'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Card } from '../components/ui'

const COLORES: Record<string, string> = {
  Pendiente: 'bg-amber-100 border-amber-300 text-amber-900',
  Confirmada: 'bg-brand-actionSoft border-brand-action/40 text-brand-actionHover',
  Cancelada: 'bg-slate-100 border-slate-300 text-slate-600 line-through',
  Finalizada: 'bg-sky-50 border-sky-200 text-sky-900',
}

export function CalendarioPage() {
  const [lunes, setLunes] = useState(lunesDe(hoyISO()))
  const [seleccionada, setSeleccionada] = useState<Reserva | null>(null)

  const dias = useMemo(() => Array.from({ length: 7 }, (_, i) => sumarDias(lunes, i)), [lunes])

  const semana = useQuery({
    queryKey: queryKeys.calendario(lunes),
    queryFn: async () => {
      const respuestas = await Promise.all(
        dias.map((fecha) =>
          reservasApi.listar({ fecha, page: 1, ordering: 'hora_inicio' }),
        ),
      )
      return respuestas.flatMap((r) => r.results)
    },
  })

  const porFecha = (fecha: string) =>
    (semana.data ?? [])
      .filter((r) => r.fecha_reserva === fecha)
      .sort((a, b) => a.hora_inicio.localeCompare(b.hora_inicio))

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-brand-dark">Calendario</h1>
          <p className="text-sm text-brand-muted">Semana del {fechaLarga(lunes)}.</p>
        </div>
        <div className="flex gap-2">
          <Boton variante="secundario" onClick={() => setLunes(sumarDias(lunes, -7))}>
            ← Anterior
          </Boton>
          <Boton variante="secundario" onClick={() => setLunes(lunesDe(hoyISO()))}>
            Hoy
          </Boton>
          <Boton variante="secundario" onClick={() => setLunes(sumarDias(lunes, 7))}>
            Siguiente →
          </Boton>
        </div>
      </header>

      {semana.isLoading ? <Cargando mensaje="Cargando calendario…" /> : null}
      {semana.error ? (
        <ErrorApi error={semana.error} onReintentar={() => void semana.refetch()} />
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
        {dias.map((dia, i) => {
          const reservas = porFecha(dia)
          const esHoy = dia === hoyISO()
          return (
            <Card
              key={dia}
              className={esHoy ? 'ring-2 ring-brand-action' : ''}
              titulo={`${nombreDia(i + 1)} ${dia.slice(8)}`}
            >
              {reservas.length === 0 ? (
                <p className="text-xs text-brand-muted">Sin reservas</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {reservas.map((r) => (
                    <li key={r.id_reserva}>
                      <button
                        type="button"
                        onClick={() => setSeleccionada(r)}
                        className={`w-full rounded-lg border px-2 py-1.5 text-left text-xs ${COLORES[r.estado_reserva]}`}
                      >
                        <span className="block font-medium">
                          {hhmm(r.hora_inicio)}–{hhmm(r.hora_fin)}
                        </span>
                        <span className="block truncate">{r.cliente.nombre}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )
        })}
      </div>

      <div className="flex flex-wrap gap-3 text-xs text-brand-muted">
        {Object.keys(COLORES).map((estado) => (
          <span key={estado} className="flex items-center gap-1">
            <span className={`inline-block h-3 w-3 rounded border ${COLORES[estado]}`} />
            {estado}
          </span>
        ))}
      </div>

      {seleccionada ? (
        <Card titulo={`Reserva ${seleccionada.codigo_reserva}`}>
          <p className="text-sm text-brand-dark">
            {seleccionada.cliente.nombre} · {fechaLarga(seleccionada.fecha_reserva)} ·{' '}
            {hhmm(seleccionada.hora_inicio)}–{hhmm(seleccionada.hora_fin)} ·{' '}
            {formatoCOP(seleccionada.precio_total)}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <Badge>{seleccionada.estado_reserva}</Badge>
            <Badge>{seleccionada.estado_pago}</Badge>
            <Boton variante="secundario" onClick={() => setSeleccionada(null)}>
              Cerrar
            </Boton>
          </div>
        </Card>
      ) : null}

      {!semana.isLoading && (semana.data ?? []).length === 0 ? (
        <Vacio titulo="No hay reservas en esta semana" />
      ) : null}
    </div>
  )
}

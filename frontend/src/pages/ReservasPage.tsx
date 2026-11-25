/** Reservas: listado filtrable, detalle en panel lateral y acciones de estado. */

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { reservasApi, type FiltrosReserva } from '../api/endpoints'
import { KEYS_AFECTADAS_POR_RESERVA, queryKeys } from '../api/queryKeys'
import type { Reserva } from '../api/types'
import { ApiError } from '../lib/api'
import { fechaCorta, formatoCOP, hhmm } from '../lib/format'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

const ESTADOS = ['Pendiente', 'Confirmada', 'Cancelada', 'Finalizada']
const PAGOS = ['Pendiente', 'Pagado']

export function ReservasPage() {
  const queryClient = useQueryClient()
  const [filtros, setFiltros] = useState<FiltrosReserva>({ page: 1 })
  const [seleccionada, setSeleccionada] = useState<Reserva | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.reservas(filtros),
    queryFn: () => reservasApi.listar(filtros),
  })

  const invalidar = () => {
    for (const clave of KEYS_AFECTADAS_POR_RESERVA) {
      void queryClient.invalidateQueries({ queryKey: clave as readonly unknown[] })
    }
  }

  const aprobar = useMutation({
    mutationFn: reservasApi.aprobar,
    onSuccess: (r) => {
      setSeleccionada(r)
      invalidar()
    },
  })
  const cancelar = useMutation({
    mutationFn: (id: number) => reservasApi.cancelar(id),
    onSuccess: (r) => {
      setSeleccionada(r)
      invalidar()
    },
  })
  const pagar = useMutation({
    mutationFn: reservasApi.marcarPagado,
    onSuccess: (r) => {
      setSeleccionada(r)
      invalidar()
    },
  })

  const errorAccion = [aprobar.error, cancelar.error, pagar.error].find(
    (e): e is ApiError => e instanceof ApiError,
  )

  const filtro = (campo: keyof FiltrosReserva, valor: string) =>
    setFiltros((f) => ({ ...f, [campo]: valor || undefined, page: 1 }))

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-brand-dark">Reservas</h1>
        <p className="text-sm text-brand-muted">
          Aprueba solicitudes, registra pagos presenciales o cancela reservas.
        </p>
      </header>

      <Card>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Campo etiqueta="Fecha">
            <input
              type="date"
              className={clasesInput}
              onChange={(e) => filtro('fecha', e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Estado">
            <select className={clasesInput} onChange={(e) => filtro('estado_reserva', e.target.value)}>
              <option value="">Todos</option>
              {ESTADOS.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="Pago">
            <select className={clasesInput} onChange={(e) => filtro('estado_pago', e.target.value)}>
              <option value="">Todos</option>
              {PAGOS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </Campo>
          <Campo etiqueta="Cliente">
            <input
              className={clasesInput}
              placeholder="Nombre, correo o teléfono"
              onChange={(e) => filtro('cliente', e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Código">
            <input
              className={clasesInput}
              placeholder="CY-261201-"
              onChange={(e) => filtro('codigo_reserva', e.target.value)}
            />
          </Campo>
        </div>
      </Card>

      {errorAccion ? <ErrorApi error={errorAccion} /> : null}

      {isLoading ? (
        <Cargando mensaje="Cargando reservas…" />
      ) : error ? (
        <ErrorApi error={error} onReintentar={() => void refetch()} />
      ) : !data || data.results.length === 0 ? (
        <Vacio titulo="No hay reservas con estos filtros" />
      ) : (
        <Card titulo={`Resultados (${data.count})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-brand-muted">
                <tr className="border-b border-brand-line">
                  <th className="py-2 pr-3">Código</th>
                  <th className="py-2 pr-3">Fecha</th>
                  <th className="py-2 pr-3">Hora</th>
                  <th className="py-2 pr-3">Cliente</th>
                  <th className="py-2 pr-3">Total</th>
                  <th className="py-2 pr-3">Reserva</th>
                  <th className="py-2 pr-3">Pago</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-line">
                {data.results.map((r) => (
                  <tr key={r.id_reserva} className="align-middle">
                    <td className="py-2 pr-3 font-mono text-xs">{r.codigo_reserva}</td>
                    <td className="py-2 pr-3">{fechaCorta(r.fecha_reserva)}</td>
                    <td className="py-2 pr-3">
                      {hhmm(r.hora_inicio)}–{hhmm(r.hora_fin)}
                    </td>
                    <td className="max-w-[14rem] truncate py-2 pr-3">{r.cliente.nombre}</td>
                    <td className="py-2 pr-3">{formatoCOP(r.precio_total)}</td>
                    <td className="py-2 pr-3">
                      <Badge>{r.estado_reserva}</Badge>
                    </td>
                    <td className="py-2 pr-3">
                      <Badge>{r.estado_pago}</Badge>
                    </td>
                    <td className="py-2 text-right">
                      <Boton variante="fantasma" onClick={() => setSeleccionada(r)}>
                        Ver
                      </Boton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <span className="text-brand-muted">
              Página {filtros.page ?? 1} · {data.count} reservas
            </span>
            <div className="flex gap-2">
              <Boton
                variante="secundario"
                disabled={!data.previous}
                onClick={() => setFiltros((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
              >
                Anterior
              </Boton>
              <Boton
                variante="secundario"
                disabled={!data.next}
                onClick={() => setFiltros((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
              >
                Siguiente
              </Boton>
            </div>
          </div>
        </Card>
      )}

      {seleccionada ? (
        <DetalleReserva
          reserva={seleccionada}
          onCerrar={() => setSeleccionada(null)}
          onAprobar={() => aprobar.mutate(seleccionada.id_reserva)}
          onCancelar={() => cancelar.mutate(seleccionada.id_reserva)}
          onPagar={() => pagar.mutate(seleccionada.id_reserva)}
          ocupado={aprobar.isPending || cancelar.isPending || pagar.isPending}
        />
      ) : null}
    </div>
  )
}

function DetalleReserva({
  reserva,
  onCerrar,
  onAprobar,
  onCancelar,
  onPagar,
  ocupado,
}: {
  reserva: Reserva
  onCerrar: () => void
  onAprobar: () => void
  onCancelar: () => void
  onPagar: () => void
  ocupado: boolean
}) {
  const puedeAprobar = reserva.estado_reserva === 'Pendiente'
  const puedeCancelar = ['Pendiente', 'Confirmada'].includes(reserva.estado_reserva)
  const puedePagar = reserva.estado_pago === 'Pendiente' && reserva.estado_reserva !== 'Cancelada'

  return (
    <div
      className="fixed inset-0 z-20 flex justify-end bg-black/30"
      role="dialog"
      aria-modal="true"
      aria-label={`Detalle de la reserva ${reserva.codigo_reserva}`}
      onClick={onCerrar}
    >
      <div
        className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-mono text-sm text-brand-muted">{reserva.codigo_reserva}</h2>
            <p className="text-lg font-semibold text-brand-dark">{reserva.cliente.nombre}</p>
          </div>
          <Boton variante="secundario" onClick={onCerrar} aria-label="Cerrar">
            Cerrar
          </Boton>
        </div>

        <dl className="mt-6 grid grid-cols-2 gap-3 text-sm">
          <Dato etiqueta="Fecha" valor={fechaCorta(reserva.fecha_reserva)} />
          <Dato
            etiqueta="Horario"
            valor={`${hhmm(reserva.hora_inicio)}–${hhmm(reserva.hora_fin)}`}
          />
          <Dato etiqueta="Total" valor={formatoCOP(reserva.precio_total)} />
          <Dato etiqueta="Reserva" valor={<Badge>{reserva.estado_reserva}</Badge>} />
          <Dato etiqueta="Pago" valor={<Badge>{reserva.estado_pago}</Badge>} />
          <Dato etiqueta="Correo" valor={reserva.cliente.correo} />
          <Dato etiqueta="Teléfono" valor={reserva.cliente.telefono} />
        </dl>

        {reserva.observaciones ? (
          <p className="mt-4 whitespace-pre-line rounded-lg bg-brand-bg p-3 text-sm text-brand-muted">
            {reserva.observaciones}
          </p>
        ) : null}

        <div className="mt-6 flex flex-wrap gap-2">
          {puedeAprobar ? (
            <Boton onClick={onAprobar} cargando={ocupado}>
              Aprobar
            </Boton>
          ) : null}
          {puedePagar ? (
            <Boton variante="secundario" onClick={onPagar} cargando={ocupado}>
              Marcar pagado
            </Boton>
          ) : null}
          {puedeCancelar ? (
            <Boton variante="peligro" onClick={onCancelar} cargando={ocupado}>
              Cancelar reserva
            </Boton>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-brand-muted">{etiqueta}</dt>
      <dd className="mt-0.5 text-brand-dark">{valor}</dd>
    </div>
  )
}

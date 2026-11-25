/** Contabilidad: ingresos recibidos, dinero pendiente e historial por rango. */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { finanzasApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import { fechaCorta, formatoCOP, hhmm, hoyISO } from '../lib/format'
import { BarChart } from '../components/BarChart'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

type Periodo = 'day' | 'week' | 'month' | 'custom'

const PERIODOS: { valor: Periodo; etiqueta: string }[] = [
  { valor: 'day', etiqueta: 'Hoy' },
  { valor: 'week', etiqueta: 'Semana' },
  { valor: 'month', etiqueta: 'Mes' },
  { valor: 'custom', etiqueta: 'Personalizado' },
]

export function ContabilidadPage() {
  const [periodo, setPeriodo] = useState<Periodo>('month')
  const [desde, setDesde] = useState(hoyISO())
  const [hasta, setHasta] = useState(hoyISO())

  const params =
    periodo === 'custom'
      ? { period: periodo, start: desde, end: hasta }
      : { period: periodo }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.summary(params),
    queryFn: () => finanzasApi.summary(params),
    enabled: periodo !== 'custom' || Boolean(desde && hasta),
  })

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-brand-dark">Contabilidad</h1>
          <p className="text-sm text-brand-muted">
            Solo reservas confirmadas o finalizadas. No incluye gastos ni utilidad.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Periodo">
          {PERIODOS.map((p) => (
            <Boton
              key={p.valor}
              variante={periodo === p.valor ? 'primario' : 'secundario'}
              onClick={() => setPeriodo(p.valor)}
            >
              {p.etiqueta}
            </Boton>
          ))}
        </div>
      </header>

      {periodo === 'custom' ? (
        <Card titulo="Rango personalizado">
          <div className="flex flex-wrap items-end gap-3">
            <Campo etiqueta="Desde">
              <input
                type="date"
                className={clasesInput}
                value={desde}
                onChange={(e) => setDesde(e.target.value)}
              />
            </Campo>
            <Campo etiqueta="Hasta">
              <input
                type="date"
                className={clasesInput}
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
              />
            </Campo>
            <Boton onClick={() => void refetch()}>Aplicar</Boton>
          </div>
        </Card>
      ) : null}

      {isLoading ? (
        <Cargando mensaje="Calculando cifras…" />
      ) : error ? (
        <ErrorApi error={error} onReintentar={() => void refetch()} />
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Tarjeta titulo="Ingresos recibidos" valor={formatoCOP(data.ingresos_recibidos)} destacado />
            <Tarjeta titulo="Dinero pendiente" valor={formatoCOP(data.dinero_pendiente)} />
            <Tarjeta titulo="Reservas" valor={String(data.total_reservas)} />
            <Tarjeta
              titulo="Pagadas / por cobrar"
              valor={`${data.reservas_pagadas} / ${data.reservas_pendientes_pago}`}
            />
          </div>

          <p className="text-xs text-brand-muted">
            Periodo: {data.periodo} · {data.inicio} → {data.fin}
          </p>

          <Card titulo="Ingresos por día">
            {data.por_dia.length === 0 ? (
              <Vacio titulo="Sin movimientos en el rango" />
            ) : (
              <BarChart
                etiqueta="Ingresos por día"
                moneda
                datos={data.por_dia.map((d) => ({
                  clave: fechaCorta(d.fecha),
                  valor: Number(d.ingresos_recibidos),
                }))}
              />
            )}
          </Card>

          <Card titulo={`Historial (${data.historial.length})`}>
            {data.historial.length === 0 ? (
              <Vacio titulo="Sin reservas en el rango" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-brand-muted">
                    <tr className="border-b border-brand-line">
                      <th className="py-2 pr-3">Código</th>
                      <th className="py-2 pr-3">Fecha</th>
                      <th className="py-2 pr-3">Cliente</th>
                      <th className="py-2 pr-3">Total</th>
                      <th className="py-2 pr-3">Reserva</th>
                      <th className="py-2">Pago</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-brand-line">
                    {data.historial.map((h) => (
                      <tr key={h.id_reserva}>
                        <td className="py-2 pr-3 font-mono text-xs">{h.codigo_reserva}</td>
                        <td className="py-2 pr-3">
                          {fechaCorta(h.fecha_reserva)} · {hhmm(h.hora_inicio)}
                        </td>
                        <td className="py-2 pr-3">{h.nombre_cliente}</td>
                        <td className="py-2 pr-3">{formatoCOP(h.precio_total)}</td>
                        <td className="py-2 pr-3">
                          <Badge>{h.estado_reserva}</Badge>
                        </td>
                        <td className="py-2">
                          <Badge>{h.estado_pago}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      ) : null}
    </div>
  )
}

function Tarjeta({
  titulo,
  valor,
  destacado,
}: {
  titulo: string
  valor: string
  destacado?: boolean
}) {
  return (
    <div className="rounded-card border border-brand-line bg-white p-4 shadow-card">
      <p className="text-xs uppercase tracking-wide text-brand-muted">{titulo}</p>
      <p className={`mt-1 text-xl font-semibold ${destacado ? 'text-brand-action' : 'text-brand-dark'}`}>
        {valor}
      </p>
    </div>
  )
}

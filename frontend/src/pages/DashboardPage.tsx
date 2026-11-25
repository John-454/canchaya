/** Dashboard: KPIs, series, solicitudes por aprobar y próximos partidos. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { finanzasApi, reservasApi } from '../api/endpoints'
import { KEYS_AFECTADAS_POR_RESERVA, queryKeys } from '../api/queryKeys'
import type { ApiError } from '../lib/api'
import { fechaCorta, formatoCOP, hhmm } from '../lib/format'
import { BarChart } from '../components/BarChart'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Card } from '../components/ui'

function Kpi({ etiqueta, valor, destacado }: { etiqueta: string; valor: string; destacado?: boolean }) {
  return (
    <div className="rounded-card border border-brand-line bg-white p-4 shadow-card">
      <p className="text-xs uppercase tracking-wide text-brand-muted">{etiqueta}</p>
      <p className={`mt-1 text-2xl font-semibold ${destacado ? 'text-brand-action' : 'text-brand-dark'}`}>
        {valor}
      </p>
    </div>
  )
}

export function DashboardPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: finanzasApi.dashboard,
  })

  const invalidar = () => {
    for (const clave of KEYS_AFECTADAS_POR_RESERVA) {
      void queryClient.invalidateQueries({ queryKey: clave as readonly unknown[] })
    }
  }

  const aprobar = useMutation({
    mutationFn: reservasApi.aprobar,
    onSuccess: invalidar,
  })
  const cancelar = useMutation({
    mutationFn: (id: number) => reservasApi.cancelar(id, 'Cancelada desde el dashboard'),
    onSuccess: invalidar,
  })

  if (isLoading) return <Cargando mensaje="Cargando dashboard…" />
  if (error) return <ErrorApi error={error} onReintentar={() => void refetch()} />
  if (!data) return null

  const { kpis, serie_actividad, serie_ingresos } = data
  const errorAccion = (aprobar.error ?? cancelar.error) as ApiError | null

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-brand-dark">Dashboard</h1>
        <p className="text-sm text-brand-muted">Resumen de tu cancha.</p>
      </header>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Kpi etiqueta="Reservas hoy" valor={String(kpis.reservas_hoy)} />
        <Kpi etiqueta="Pendientes hoy" valor={String(kpis.pendientes_hoy)} />
        <Kpi etiqueta="Por aprobar" valor={String(kpis.por_aprobar)} destacado={kpis.por_aprobar > 0} />
        <Kpi etiqueta="Confirmadas hoy" valor={String(kpis.confirmadas_hoy)} />
        <Kpi etiqueta="Ingresos recibidos" valor={formatoCOP(kpis.ingresos_recibidos)} destacado />
        <Kpi etiqueta="Dinero pendiente" valor={formatoCOP(kpis.dinero_pendiente)} />
      </div>

      {errorAccion ? <ErrorApi error={errorAccion} /> : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card titulo="Actividad (30 días)">
          <BarChart
            etiqueta="Reservas por día"
            datos={serie_actividad.map((d) => ({ clave: fechaCorta(d.fecha), valor: d.reservas }))}
          />
        </Card>
        <Card titulo="Ingresos recibidos (6 meses)">
          <BarChart
            etiqueta="Ingresos por mes"
            moneda
            datos={serie_ingresos.map((d) => ({
              clave: d.mes,
              valor: Number(d.ingresos_recibidos),
            }))}
          />
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card titulo="Solicitudes por aprobar">
          {data.solicitudes_por_aprobar.length === 0 ? (
            <Vacio titulo="No hay solicitudes pendientes" />
          ) : (
            <ul className="divide-y divide-brand-line">
              {data.solicitudes_por_aprobar.map((s) => (
                <li key={s.id_reserva} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-brand-dark">{s.nombre_cliente}</p>
                    <p className="text-xs text-brand-muted">
                      {fechaCorta(s.fecha_reserva)} · {hhmm(s.hora_inicio)}–{hhmm(s.hora_fin)} ·{' '}
                      {formatoCOP(s.precio_total)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Boton onClick={() => aprobar.mutate(s.id_reserva)} cargando={aprobar.isPending}>
                      Aprobar
                    </Boton>
                    <Boton
                      variante="secundario"
                      onClick={() => cancelar.mutate(s.id_reserva)}
                      cargando={cancelar.isPending}
                    >
                      Rechazar
                    </Boton>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card titulo="Próximos partidos">
          {data.proximos_partidos.length === 0 ? (
            <Vacio titulo="No hay partidos confirmados próximos" />
          ) : (
            <ul className="divide-y divide-brand-line">
              {data.proximos_partidos.map((p) => (
                <li key={p.id_reserva} className="flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-brand-dark">{p.nombre_cliente}</p>
                    <p className="text-xs text-brand-muted">
                      {fechaCorta(p.fecha_reserva)} · {hhmm(p.hora_inicio)}–{hhmm(p.hora_fin)}
                    </p>
                  </div>
                  <Badge>{p.estado_pago}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}

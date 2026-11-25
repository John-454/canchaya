/** Tarifas: semanales, fecha especial y vista previa de precios del día. */

import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { tarifasApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import { ApiError } from '../lib/api'
import { DIAS_SEMANA, fechaLarga, formatoCOP, hhmm, hoyISO, nombreDia } from '../lib/format'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

const ORIGEN_TEXTO: Record<string, string> = {
  base: 'Precio base',
  semanal: 'Tarifa semanal',
  especial: 'Fecha especial',
}

export function TarifasPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.tarifas,
    queryFn: tarifasApi.listar,
  })

  const [tipo, setTipo] = useState<'semanal' | 'especial'>('semanal')
  const [dia, setDia] = useState(1)
  const [fecha, setFecha] = useState(hoyISO())
  const [inicio, setInicio] = useState('08:00')
  const [fin, setFin] = useState('22:00')
  const [precio, setPrecio] = useState('')
  const [fechaPreview, setFechaPreview] = useState(hoyISO())

  const [previewActiva, setPreviewActiva] = useState(false)
  const preview = useQuery({
    queryKey: queryKeys.preview(fechaPreview),
    queryFn: () => tarifasApi.preview(fechaPreview),
    enabled: previewActiva,
    retry: false,
  })

  const refrescar = () => void queryClient.invalidateQueries({ queryKey: queryKeys.tarifas })

  const crear = useMutation({
    mutationFn: () =>
      tarifasApi.crear({
        dia_semana: tipo === 'semanal' ? dia : null,
        fecha_especial: tipo === 'especial' ? fecha : null,
        hora_inicio: inicio,
        hora_fin: fin,
        precio_hora: precio,
      }),
    onSuccess: () => {
      setPrecio('')
      refrescar()
    },
  })
  const eliminar = useMutation({
    mutationFn: (id: number) => tarifasApi.eliminar(id),
    onSuccess: refrescar,
  })

  if (isLoading) return <Cargando mensaje="Cargando tarifas…" />
  if (error) return <ErrorApi error={error} onReintentar={() => void refetch()} />

  const enviar = (evento: FormEvent) => {
    evento.preventDefault()
    crear.mutate()
  }

  const semanales = (data ?? []).filter((t) => t.dia_semana !== null)
  const especiales = (data ?? []).filter((t) => t.fecha_especial !== null)

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-brand-dark">Tarifas</h1>
        <p className="text-sm text-brand-muted">
          Prioridad aplicada por bloque de 60 minutos: fecha especial &gt; tarifa semanal &gt; precio
          base.
        </p>
      </header>

      <Card titulo="Nueva tarifa">
        <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6 lg:items-end">
          <Campo etiqueta="Tipo">
            <select
              className={clasesInput}
              value={tipo}
              onChange={(e) => setTipo(e.target.value as 'semanal' | 'especial')}
            >
              <option value="semanal">Semanal</option>
              <option value="especial">Fecha especial</option>
            </select>
          </Campo>

          {tipo === 'semanal' ? (
            <Campo etiqueta="Día">
              <select
                className={clasesInput}
                value={dia}
                onChange={(e) => setDia(Number(e.target.value))}
              >
                {DIAS_SEMANA.map((d) => (
                  <option key={d.valor} value={d.valor}>
                    {d.nombre}
                  </option>
                ))}
              </select>
            </Campo>
          ) : (
            <Campo etiqueta="Fecha">
              <input
                type="date"
                className={clasesInput}
                value={fecha}
                onChange={(e) => setFecha(e.target.value)}
              />
            </Campo>
          )}

          <Campo etiqueta="Inicio">
            <input
              type="time"
              step={3600}
              className={clasesInput}
              value={inicio}
              onChange={(e) => setInicio(e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Fin">
            <input
              type="time"
              step={3600}
              className={clasesInput}
              value={fin}
              onChange={(e) => setFin(e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Precio/hora (COP)">
            <input
              type="number"
              min={1}
              step="1000"
              required
              className={clasesInput}
              value={precio}
              onChange={(e) => setPrecio(e.target.value)}
            />
          </Campo>
          <Boton tipo="submit" cargando={crear.isPending}>
            Crear
          </Boton>
        </form>
        {crear.error instanceof ApiError ? <ErrorApi error={crear.error} /> : null}
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card titulo="Semanales">
          {semanales.length === 0 ? (
            <Vacio titulo="Sin tarifas semanales" />
          ) : (
            <ul className="divide-y divide-brand-line">
              {semanales.map((t) => (
                <li key={t.id_tarifa} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-brand-dark">
                    {nombreDia(t.dia_semana ?? 0)} · {hhmm(t.hora_inicio)}–{hhmm(t.hora_fin)}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{formatoCOP(t.precio_hora)}</span>
                    {!t.activo ? <Badge>Inactiva</Badge> : null}
                    <Boton variante="peligro" onClick={() => eliminar.mutate(t.id_tarifa)}>
                      Eliminar
                    </Boton>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card titulo="Fechas especiales">
          {especiales.length === 0 ? (
            <Vacio titulo="Sin fechas especiales" />
          ) : (
            <ul className="divide-y divide-brand-line">
              {especiales.map((t) => (
                <li key={t.id_tarifa} className="flex items-center justify-between gap-3 py-2">
                  <span className="text-sm text-brand-dark">
                    {t.fecha_especial} · {hhmm(t.hora_inicio)}–{hhmm(t.hora_fin)}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{formatoCOP(t.precio_hora)}</span>
                    <Boton variante="peligro" onClick={() => eliminar.mutate(t.id_tarifa)}>
                      Eliminar
                    </Boton>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card
        titulo="Vista previa de precios"
        acciones={
          <div className="flex items-end gap-2">
            <input
              type="date"
              className={clasesInput}
              value={fechaPreview}
              onChange={(e) => setFechaPreview(e.target.value)}
              aria-label="Fecha de la vista previa"
            />
            <Boton onClick={() => setPreviewActiva(true)} cargando={preview.isFetching}>
              Consultar
            </Boton>
          </div>
        }
      >
        {!previewActiva ? (
          <p className="text-sm text-brand-muted">
            Elige una fecha y consulta el precio que se cobraría en cada bloque de 60 minutos.
          </p>
        ) : preview.isLoading ? (
          <Cargando mensaje="Calculando precios…" />
        ) : preview.error ? (
          <ErrorApi error={preview.error} onReintentar={() => void preview.refetch()} />
        ) : preview.data && preview.data.bloques.length === 0 ? (
          <Vacio titulo="No hay horario configurado para ese día" />
        ) : preview.data ? (
          <div>
            <p className="mb-3 text-sm text-brand-muted">{fechaLarga(preview.data.fecha)}</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
              {preview.data.bloques.map((b) => (
                <div
                  key={b.hora_inicio}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    b.origen === 'especial'
                      ? 'border-purple-200 bg-purple-50'
                      : b.origen === 'semanal'
                        ? 'border-brand-action/30 bg-brand-actionSoft'
                        : 'border-brand-line bg-white'
                  }`}
                >
                  <p className="font-medium text-brand-dark">{b.hora_inicio}</p>
                  <p className="text-xs text-brand-muted">{ORIGEN_TEXTO[b.origen]}</p>
                  <p className="mt-1 font-semibold">{formatoCOP(b.precio)}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </Card>

      {eliminar.error instanceof ApiError ? <ErrorApi error={eliminar.error} /> : null}
    </div>
  )
}

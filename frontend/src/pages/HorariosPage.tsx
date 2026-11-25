/** Horarios: franjas semanales por día, con detección de solapes (409). */

import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { horariosApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import { ApiError } from '../lib/api'
import { DIAS_SEMANA, hhmm, nombreDia } from '../lib/format'
import { Cargando, ErrorApi } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

export function HorariosPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.horarios,
    queryFn: horariosApi.listar,
  })

  const [dia, setDia] = useState(1)
  const [apertura, setApertura] = useState('08:00')
  const [cierre, setCierre] = useState('22:00')

  const refrescar = () => void queryClient.invalidateQueries({ queryKey: queryKeys.horarios })

  const crear = useMutation({
    mutationFn: () =>
      horariosApi.crear({
        dia_semana: dia,
        hora_apertura: apertura,
        hora_cierre: cierre,
        activo: true,
      }),
    onSuccess: refrescar,
  })
  const eliminar = useMutation({
    mutationFn: (id: number) => horariosApi.eliminar(id),
    onSuccess: refrescar,
  })
  const alternar = useMutation({
    mutationFn: (h: { id: number; activo: boolean; dia_semana: number; hora_apertura: string; hora_cierre: string }) =>
      horariosApi.actualizar(h.id, {
        dia_semana: h.dia_semana,
        hora_apertura: h.hora_apertura,
        hora_cierre: h.hora_cierre,
        activo: !h.activo,
      }),
    onSuccess: refrescar,
  })

  if (isLoading) return <Cargando mensaje="Cargando horarios…" />
  if (error) return <ErrorApi error={error} onReintentar={() => void refetch()} />

  const enviar = (evento: FormEvent) => {
    evento.preventDefault()
    crear.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-brand-dark">Horarios de atención</h1>
        <p className="text-sm text-brand-muted">
          Puedes tener varias franjas por día (por ejemplo 08:00–12:00 y 13:00–22:00). Las horas
          deben ser en punto.
        </p>
      </header>

      <Card titulo="Agregar franja">
        <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-4 sm:items-end">
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
          <Campo etiqueta="Apertura">
            <input
              type="time"
              step={3600}
              className={clasesInput}
              value={apertura}
              onChange={(e) => setApertura(e.target.value)}
            />
          </Campo>
          <Campo etiqueta="Cierre">
            <input
              type="time"
              step={3600}
              className={clasesInput}
              value={cierre}
              onChange={(e) => setCierre(e.target.value)}
            />
          </Campo>
          <Boton tipo="submit" cargando={crear.isPending}>
            Agregar
          </Boton>
        </form>
        {crear.error instanceof ApiError ? <ErrorApi error={crear.error} /> : null}
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {DIAS_SEMANA.map((d) => {
          const franjas = (data ?? []).filter((h) => h.dia_semana === d.valor)
          return (
            <Card key={d.valor} titulo={d.nombre}>
              {franjas.length === 0 ? (
                <p className="text-sm text-brand-muted">Cerrado</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {franjas.map((h) => (
                    <li key={h.id_horario} className="flex items-center justify-between gap-2">
                      <span className="text-sm text-brand-dark">
                        {hhmm(h.hora_apertura)} – {hhmm(h.hora_cierre)}
                      </span>
                      <div className="flex items-center gap-1">
                        {h.activo ? <Badge>Activa</Badge> : <Badge>Inactiva</Badge>}
                        <Boton
                          variante="fantasma"
                          onClick={() =>
                            alternar.mutate({
                              id: h.id_horario,
                              activo: h.activo,
                              dia_semana: h.dia_semana,
                              hora_apertura: h.hora_apertura,
                              hora_cierre: h.hora_cierre,
                            })
                          }
                        >
                          {h.activo ? 'Desactivar' : 'Activar'}
                        </Boton>
                        <Boton variante="peligro" onClick={() => eliminar.mutate(h.id_horario)}>
                          Eliminar
                        </Boton>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )
        })}
      </div>

      {eliminar.error instanceof ApiError ? <ErrorApi error={eliminar.error} /> : null}
      {alternar.error instanceof ApiError ? <ErrorApi error={alternar.error} /> : null}

      <p className="text-xs text-brand-muted">
        {nombreDia(1)} a {nombreDia(7)} · las franjas contiguas (12:00 fin / 12:00 inicio) están
        permitidas.
      </p>
    </div>
  )
}

/** Mi cancha: datos generales, precio base y estado de publicación. */

import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { canchaApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import { ApiError } from '../lib/api'
import { formatoCOP } from '../lib/format'
import { Cargando, ErrorApi } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

interface Formulario {
  nombre: string
  direccion: string
  zona: string
  descripcion: string
  precio_base: string
  estado: boolean
}

export function MiCanchaPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.cancha,
    queryFn: canchaApi.get,
  })

  const [formulario, setFormulario] = useState<Formulario | null>(null)
  const [mensaje, setMensaje] = useState<string | null>(null)

  useEffect(() => {
    if (data) {
      setFormulario({
        nombre: data.nombre,
        direccion: data.direccion,
        zona: data.zona ?? '',
        descripcion: data.descripcion ?? '',
        precio_base: data.precio_base,
        estado: data.estado,
      })
    }
  }, [data])

  const guardar = useMutation({
    mutationFn: (datos: Partial<Formulario>) => canchaApi.update(datos),
    onSuccess: () => {
      setMensaje('Cambios guardados.')
      void queryClient.invalidateQueries({ queryKey: queryKeys.cancha })
    },
    onError: () => setMensaje(null),
  })

  if (isLoading) return <Cargando mensaje="Cargando tu cancha…" />
  if (error) return <ErrorApi error={error} onReintentar={() => void refetch()} />
  if (!data || !formulario) return null

  const errorGuardado = guardar.error instanceof ApiError ? guardar.error : null
  const campo = (nombre: keyof Formulario) => formulario[nombre]

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-brand-dark">Mi cancha</h1>
          <p className="text-sm text-brand-muted">
            Precio base actual: {formatoCOP(data.precio_base)}
          </p>
        </div>
        <Badge>{data.estado ? 'true' : 'false'}</Badge>
      </header>

      <Card>
        <form
          className="grid gap-4 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault()
            guardar.mutate(formulario)
          }}
        >
          <Campo etiqueta="Nombre">
            <input
              className={clasesInput}
              value={String(campo('nombre'))}
              onChange={(e) => setFormulario({ ...formulario, nombre: e.target.value })}
              required
            />
          </Campo>
          <Campo etiqueta="Dirección">
            <input
              className={clasesInput}
              value={String(campo('direccion'))}
              onChange={(e) => setFormulario({ ...formulario, direccion: e.target.value })}
            />
          </Campo>
          <Campo etiqueta="Zona (opcional)">
            <input
              className={clasesInput}
              value={String(campo('zona'))}
              onChange={(e) => setFormulario({ ...formulario, zona: e.target.value })}
            />
          </Campo>
          <Campo etiqueta="Precio base por hora (COP)">
            <input
              type="number"
              min={0}
              step="1000"
              className={clasesInput}
              value={String(campo('precio_base'))}
              onChange={(e) => setFormulario({ ...formulario, precio_base: e.target.value })}
            />
          </Campo>
          <Campo etiqueta="Descripción">
            <textarea
              rows={4}
              className={clasesInput}
              value={String(campo('descripcion'))}
              onChange={(e) => setFormulario({ ...formulario, descripcion: e.target.value })}
            />
          </Campo>
          <label className="flex items-center gap-2 self-end text-sm text-brand-dark">
            <input
              type="checkbox"
              checked={Boolean(campo('estado'))}
              onChange={(e) => setFormulario({ ...formulario, estado: e.target.checked })}
            />
            Cancha publicada (visible en el catálogo)
          </label>

          <div className="sm:col-span-2">
            {errorGuardado ? <ErrorApi error={errorGuardado} /> : null}
            {mensaje ? (
              <p className="text-sm text-brand-action" role="status">
                {mensaje}
              </p>
            ) : null}
            <Boton tipo="submit" cargando={guardar.isPending} className="mt-2">
              Guardar cambios
            </Boton>
          </div>
        </form>
      </Card>
    </div>
  )
}

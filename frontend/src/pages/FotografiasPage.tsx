/** Fotografías: registro de URLs, marca de principal y borrado. */

import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { imagenesApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import { ApiError } from '../lib/api'
import { Cargando, ErrorApi, Vacio } from '../components/estados'
import { Badge, Boton, Campo, clasesInput, Card } from '../components/ui'

export function FotografiasPage() {
  const queryClient = useQueryClient()
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.imagenes,
    queryFn: imagenesApi.listar,
  })

  const [url, setUrl] = useState('')
  const [descripcion, setDescripcion] = useState('')

  const refrescar = () => void queryClient.invalidateQueries({ queryKey: queryKeys.imagenes })

  const crear = useMutation({
    mutationFn: () => imagenesApi.crear({ url_imagen: url.trim(), descripcion }),
    onSuccess: () => {
      setUrl('')
      setDescripcion('')
      refrescar()
    },
  })
  const marcarPrincipal = useMutation({
    mutationFn: (id: number) => imagenesApi.actualizar(id, { imagen_principal: true }),
    onSuccess: refrescar,
  })
  const eliminar = useMutation({
    mutationFn: (id: number) => imagenesApi.eliminar(id),
    onSuccess: refrescar,
  })

  if (isLoading) return <Cargando mensaje="Cargando fotografías…" />
  if (error) return <ErrorApi error={error} onReintentar={() => void refetch()} />

  const errorAccion = [crear.error, marcarPrincipal.error, eliminar.error].find(
    (e): e is ApiError => e instanceof ApiError,
  )

  const enviar = (evento: FormEvent) => {
    evento.preventDefault()
    if (url.trim()) crear.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold text-brand-dark">Fotografías</h1>
        <p className="text-sm text-brand-muted">
          Sube las imágenes a Supabase Storage y pega aquí la URL pública. Solo una puede ser
          principal.
        </p>
      </header>

      <Card titulo="Agregar fotografía">
        <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-[2fr_2fr_auto] sm:items-end">
          <Campo etiqueta="URL de la imagen">
            <input
              className={clasesInput}
              placeholder="https://…/cancha.jpg"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
          </Campo>
          <Campo etiqueta="Descripción (opcional)">
            <input
              className={clasesInput}
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
            />
          </Campo>
          <Boton tipo="submit" cargando={crear.isPending}>
            Agregar
          </Boton>
        </form>
        {crear.error instanceof ApiError ? <ErrorApi error={crear.error} /> : null}
      </Card>

      <Card titulo={`Galería (${data?.length ?? 0})`}>
        {errorAccion && !(crear.error instanceof ApiError) ? <ErrorApi error={errorAccion} /> : null}
        {!data || data.length === 0 ? (
          <Vacio titulo="Aún no tienes fotografías">Agrega la primera para mostrarla en el catálogo.</Vacio>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.map((imagen) => (
              <li
                key={imagen.id_imagen}
                className="overflow-hidden rounded-card border border-brand-line"
              >
                <img
                  src={imagen.url_imagen}
                  alt={imagen.descripcion || 'Fotografía de la cancha'}
                  className="aspect-video w-full object-cover"
                  loading="lazy"
                />
                <div className="flex items-center justify-between gap-2 p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-brand-dark">
                      {imagen.descripcion || 'Sin descripción'}
                    </p>
                    {imagen.imagen_principal ? <Badge>Principal</Badge> : null}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {!imagen.imagen_principal ? (
                      <Boton
                        variante="fantasma"
                        onClick={() => marcarPrincipal.mutate(imagen.id_imagen)}
                      >
                        Principal
                      </Boton>
                    ) : null}
                    <Boton
                      variante="peligro"
                      onClick={() => {
                        if (window.confirm('¿Eliminar esta fotografía?')) {
                          eliminar.mutate(imagen.id_imagen)
                        }
                      }}
                    >
                      Eliminar
                    </Boton>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

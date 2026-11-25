/** Gráfico de barras simple (sin dependencias) con etiquetas accesibles. */

import { formatoCOP } from '../lib/format'

interface Dato {
  clave: string
  valor: number
}

export function BarChart({
  datos,
  moneda = false,
  etiqueta,
}: {
  datos: Dato[]
  moneda?: boolean
  etiqueta: string
}) {
  const maximo = Math.max(1, ...datos.map((d) => d.valor))
  return (
    <figure aria-label={etiqueta}>
      <div className="flex h-40 items-end gap-1" role="img" aria-label={etiqueta}>
        {datos.map((d) => (
          <div
            key={d.clave}
            className="group relative flex-1 rounded-t bg-brand-action/80 hover:bg-brand-action"
            style={{ height: `${Math.max(2, (d.valor / maximo) * 100)}%` }}
            title={`${d.clave}: ${moneda ? formatoCOP(d.valor) : d.valor}`}
          >
            <span className="sr-only">
              {d.clave}: {moneda ? formatoCOP(d.valor) : d.valor}
            </span>
          </div>
        ))}
      </div>
      <figcaption className="mt-2 flex justify-between text-xs text-brand-muted">
        <span>{datos[0]?.clave}</span>
        <span>{datos[datos.length - 1]?.clave}</span>
      </figcaption>
    </figure>
  )
}

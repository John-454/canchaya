/** Helper de tests: render con QueryClient/Router y mock de fetch. */

import { render, type RenderOptions } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement, ReactNode } from 'react'
import { vi } from 'vitest'

export function renderConProviders(
  ui: ReactElement,
  { ruta = '/', ...opciones }: RenderOptions & { ruta?: string } = {},
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const Envoltorio = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>{children}</MemoryRouter>
    </QueryClientProvider>
  )
  return render(ui, { wrapper: Envoltorio, ...opciones })
}

/** Respuesta JSON simulada del backend. */
export function respuestaJson(cuerpo: unknown, status = 200): Response {
  return new Response(status === 204 ? null : JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

/** Instala `fetch` con una cola de respuestas por ruta. */
export function mockFetch(rutas: Record<string, { status?: number; body: unknown }>) {
  const espia = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    const clave = Object.keys(rutas).find((k) => url.includes(k))
    if (!clave) return respuestaJson({ code: 'no_encontrado', detail: 'sin mock' }, 404)
    const { status = 200, body } = rutas[clave]
    return respuestaJson(body, status)
  })
  vi.stubGlobal('fetch', espia)
  return espia
}

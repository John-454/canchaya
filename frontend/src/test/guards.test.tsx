import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import { SinPermiso } from '../components/SinPermiso'

// Se aísla `SinPermiso` con un mock del hook de sesión para probar la rama de rol.
vi.mock('../auth/AuthProvider', () => ({
  useAuth: () => ({
    perfil: { nombre: 'Cliente', correo: 'cli@canchaya.test', rol: 'cliente' },
    logout: vi.fn(),
  }),
}))

describe('SinPermiso', () => {
  it('informa el rol requerido y el rol actual', () => {
    render(
      <MemoryRouter>
        <Routes>
          <Route path="*" element={<SinPermiso rolRequerido="administrador" />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/administrador/)
    expect(screen.getByRole('alert')).toHaveTextContent(/Tu cuenta es\s*cliente/)
    expect(screen.getByRole('button', { name: /cerrar sesión/i })).toBeInTheDocument()
  })
})

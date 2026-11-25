/** Pantalla de inicio de sesión (email/contraseña + Google). */

import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import { Boton, Campo, clasesInput, Card } from '../components/ui'

export function LoginPage() {
  const { estado, login, loginGoogle } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (estado === 'lista') return <Navigate to="/panel" replace />

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await login(email.trim(), password)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo iniciar sesión.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-brand-dark p-4">
      <div className="w-full max-w-sm">
        <p className="mb-6 text-center text-2xl font-bold text-white">
          canchaya<span className="text-brand-action">.</span>
        </p>
        <Card>
          <h1 className="mb-1 text-lg font-semibold text-brand-dark">Panel del propietario</h1>
          <p className="mb-5 text-sm text-brand-muted">Ingresa con tu cuenta para administrar tu cancha.</p>

          <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
            <Campo etiqueta="Correo">
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={clasesInput}
                placeholder="dueno@cancha.com"
              />
            </Campo>
            <Campo etiqueta="Contraseña">
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={clasesInput}
                placeholder="••••••••"
              />
            </Campo>

            {error ? (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                {error}
              </p>
            ) : null}

            <Boton tipo="submit" cargando={enviando} className="w-full">
              Entrar
            </Boton>
            <Boton variante="secundario" onClick={() => void loginGoogle()} className="w-full">
              Continuar con Google
            </Boton>
          </form>
        </Card>
      </div>
    </div>
  )
}

/**
 * Sesión de Supabase + perfil del backend.
 *
 * Flujo:
 *  1. Supabase entrega la sesión (`onAuthStateChange`).
 *  2. Con sesión, se llama a `POST /auth/sync/` para crear/vincular el perfil
 *     y obtener el `rol`.
 *  3. El `api.ts` pide el token al provider registrado aquí.
 *
 * Guardas: `administrador` entra al panel; `cliente` ve un aviso; si falta el
 * teléfono (R1) se ofrece completarlo, aunque a un admin no se le exige.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Session } from '@supabase/supabase-js'

import { authApi } from '../api/endpoints'
import { queryKeys } from '../api/queryKeys'
import type { Usuario } from '../api/types'
import { setTokenProvider } from '../lib/api'
import { getAccessToken, signInWithGoogle, signInWithPassword, signOut, supabase } from '../lib/supabase'

type EstadoSesion = 'cargando' | 'anonimo' | 'lista' | 'error'

interface AuthContextValue {
  estado: EstadoSesion
  perfil: Usuario | null
  error: string | null
  login: (email: string, password: string) => Promise<void>
  loginGoogle: () => Promise<void>
  logout: () => Promise<void>
  recargarPerfil: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoSesion>('cargando')
  const [perfil, setPerfil] = useState<Usuario | null>(null)
  const [error, setError] = useState<string | null>(null)

  // El cliente HTTP siempre obtiene un token fresco de Supabase.
  useEffect(() => {
    setTokenProvider(async () => {
      const { data } = await supabase.auth.getSession()
      return data.session?.access_token ?? null
    })
  }, [])

  const sincronizar = useCallback(async () => {
    try {
      setError(null)
      const usuario = await authApi.sync()
      setPerfil(usuario)
      setEstado('lista')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo cargar tu perfil.')
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    let activo = true

    const manejar = async (session: Session | null) => {
      if (!activo) return
      if (!session) {
        setPerfil(null)
        setEstado('anonimo')
        return
      }
      await sincronizar()
    }

    supabase.auth.getSession().then(({ data }) => manejar(data.session))
    const { data: sub } = supabase.auth.onAuthStateChange((_evento, session) => {
      void manejar(session)
    })

    return () => {
      activo = false
      sub.subscription.unsubscribe()
    }
  }, [sincronizar])

  const login = useCallback(async (email: string, password: string) => {
    setEstado('cargando')
    try {
      await signInWithPassword(email, password)
    } catch (e) {
      setEstado('anonimo')
      throw e
    }
  }, [])

  const loginGoogle = useCallback(async () => {
    await signInWithGoogle()
  }, [])

  const logout = useCallback(async () => {
    await signOut()
    setPerfil(null)
    setEstado('anonimo')
  }, [])

  const recargarPerfil = useCallback(async () => {
    const usuario = await authApi.me()
    setPerfil(usuario)
  }, [])

  const value = useMemo(
    () => ({ estado, perfil, error, login, loginGoogle, logout, recargarPerfil }),
    [estado, perfil, error, login, loginGoogle, logout, recargarPerfil],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}

/** Solo para tests: expone las query keys que dependen de la sesión. */
export const CLAVES_SESION = [queryKeys.perfil]

export { getAccessToken }

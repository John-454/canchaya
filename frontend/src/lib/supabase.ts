/** Cliente de Supabase (solo Auth). La sesión persiste en localStorage. */

import { createClient, type Session } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

export const supabaseConfigurado = Boolean(url && anonKey)

export const supabase = createClient(url ?? 'http://localhost', anonKey ?? 'anon', {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
})

export type { Session }

/** Inicia sesión con email/contraseña. */
export async function signInWithPassword(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw new Error(traducirErrorSupabase(error.message))
  return data.session
}

/** Inicia sesión con Google (OAuth). */
export async function signInWithGoogle() {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
  if (error) throw new Error(traducirErrorSupabase(error.message))
}

export async function signOut() {
  await supabase.auth.signOut()
}

/** Devuelve un access token válido (refresca si está por expirar). */
export async function getAccessToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession()
  if (!data.session) return null
  const expiraEn = (data.session.expires_at ?? 0) * 1000
  if (Date.now() > expiraEn - 30_000) {
    const { data: refresco, error } = await supabase.auth.refreshSession()
    if (error) return null
    return refresco.session?.access_token ?? null
  }
  return data.session.access_token
}

function traducirErrorSupabase(mensaje: string): string {
  if (/invalid login credentials/i.test(mensaje)) return 'Correo o contraseña incorrectos.'
  if (/email not confirmed/i.test(mensaje)) return 'Debes confirmar tu correo antes de entrar.'
  return mensaje
}

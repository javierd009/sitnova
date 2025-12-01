import { createClient } from '@/shared/lib/supabase'
import type { User, Condominium } from '@/shared/types/database'
import type { LoginCredentials, SignUpData } from '../types'

const supabase = createClient()

export const authService = {
  async login({ email, password }: LoginCredentials) {
    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (authError) throw authError
    if (!authData.user) throw new Error('No se pudo iniciar sesion')

    // Obtener datos del usuario y condominio
    const { data: userData, error: userError } = await supabase
      .from('users')
      .select(`
        *,
        condominium:condominiums(*)
      `)
      .eq('id', authData.user.id)
      .single()

    if (userError) throw userError
    if (!userData) throw new Error('Usuario no encontrado en el sistema')

    return {
      user: userData as User,
      condominium: userData.condominium as Condominium,
    }
  },

  async signup(data: SignUpData) {
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email: data.email,
      password: data.password,
    })

    if (authError) throw authError
    if (!authData.user) throw new Error('No se pudo crear la cuenta')

    // Crear registro en tabla users
    const { data: userData, error: userError } = await supabase
      .from('users')
      .insert({
        id: authData.user.id,
        email: data.email,
        full_name: data.fullName,
        phone: data.phone || null,
        condominium_id: data.condominiumId,
        role: 'operator', // Por defecto operador, admin cambia luego
      })
      .select(`
        *,
        condominium:condominiums(*)
      `)
      .single()

    if (userError) throw userError

    return {
      user: userData as User,
      condominium: userData.condominium as Condominium,
    }
  },

  async logout() {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
  },

  async getSession() {
    const { data: { session }, error } = await supabase.auth.getSession()

    if (error) throw error
    if (!session) return null

    const { data: userData, error: userError } = await supabase
      .from('users')
      .select(`
        *,
        condominium:condominiums(*)
      `)
      .eq('id', session.user.id)
      .single()

    if (userError || !userData) return null

    return {
      user: userData as User,
      condominium: userData.condominium as Condominium,
    }
  },

  async resetPassword(email: string) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    })
    if (error) throw error
  },

  async updatePassword(newPassword: string) {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    })
    if (error) throw error
  },

  onAuthStateChange(callback: (event: string, session: unknown) => void) {
    return supabase.auth.onAuthStateChange(callback)
  },
}

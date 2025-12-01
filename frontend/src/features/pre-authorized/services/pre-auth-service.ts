import { createClient } from '@/shared/lib/supabase'
import type { PreAuthorizedVisitor } from '@/shared/types/database'

const supabase = createClient()

export interface CreatePreAuthData {
  condominium_id: string
  resident_id: string
  visitor_name: string
  cedula?: string
  license_plate?: string
  valid_from: string
  valid_until: string
  single_use: boolean
  notes?: string
}

export const preAuthService = {
  async getAll(condominiumId: string): Promise<(PreAuthorizedVisitor & { resident: { full_name: string; apartment: string } })[]> {
    const { data, error } = await supabase
      .from('pre_authorized_visitors')
      .select(`
        *,
        resident:residents(full_name, apartment)
      `)
      .eq('condominium_id', condominiumId)
      .order('valid_until', { ascending: false })

    if (error) throw error
    return data || []
  },

  async getActive(condominiumId: string): Promise<(PreAuthorizedVisitor & { resident: { full_name: string; apartment: string } })[]> {
    const now = new Date().toISOString()

    const { data, error } = await supabase
      .from('pre_authorized_visitors')
      .select(`
        *,
        resident:residents(full_name, apartment)
      `)
      .eq('condominium_id', condominiumId)
      .lte('valid_from', now)
      .gte('valid_until', now)
      .eq('used', false)
      .order('valid_until', { ascending: true })

    if (error) throw error
    return data || []
  },

  async create(preAuth: CreatePreAuthData): Promise<PreAuthorizedVisitor> {
    const { data, error } = await supabase
      .from('pre_authorized_visitors')
      .insert({
        ...preAuth,
        license_plate: preAuth.license_plate?.toUpperCase() || null,
      })
      .select()
      .single()

    if (error) throw error
    return data
  },

  async delete(id: string): Promise<void> {
    const { error } = await supabase
      .from('pre_authorized_visitors')
      .delete()
      .eq('id', id)

    if (error) throw error
  },

  async markAsUsed(id: string): Promise<PreAuthorizedVisitor> {
    const { data, error } = await supabase
      .from('pre_authorized_visitors')
      .update({ used: true })
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  },
}

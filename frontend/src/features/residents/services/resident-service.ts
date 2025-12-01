import { createClient } from '@/shared/lib/supabase'
import type { Resident, Vehicle } from '@/shared/types/database'

const supabase = createClient()

export interface CreateResidentData {
  condominium_id: string
  full_name: string
  apartment: string
  phone: string
  phone_secondary?: string
  email?: string
  notification_preference: 'whatsapp' | 'call' | 'both'
}

export interface UpdateResidentData extends Partial<CreateResidentData> {
  is_active?: boolean
}

export const residentService = {
  async getAll(condominiumId: string): Promise<Resident[]> {
    const { data, error } = await supabase
      .from('residents')
      .select('*')
      .eq('condominium_id', condominiumId)
      .order('apartment', { ascending: true })

    if (error) throw error
    return data || []
  },

  async getById(id: string): Promise<Resident & { vehicles: Vehicle[] }> {
    const { data, error } = await supabase
      .from('residents')
      .select(`
        *,
        vehicles(*)
      `)
      .eq('id', id)
      .single()

    if (error) throw error
    return data
  },

  async search(condominiumId: string, query: string): Promise<Resident[]> {
    const { data, error } = await supabase
      .from('residents')
      .select('*')
      .eq('condominium_id', condominiumId)
      .or(`full_name.ilike.%${query}%,apartment.ilike.%${query}%,phone.ilike.%${query}%`)
      .limit(20)

    if (error) throw error
    return data || []
  },

  async create(resident: CreateResidentData): Promise<Resident> {
    const { data, error } = await supabase
      .from('residents')
      .insert(resident)
      .select()
      .single()

    if (error) throw error
    return data
  },

  async update(id: string, resident: UpdateResidentData): Promise<Resident> {
    const { data, error } = await supabase
      .from('residents')
      .update(resident)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  },

  async delete(id: string): Promise<void> {
    const { error } = await supabase
      .from('residents')
      .delete()
      .eq('id', id)

    if (error) throw error
  },

  async toggleActive(id: string, isActive: boolean): Promise<Resident> {
    return this.update(id, { is_active: isActive })
  },
}

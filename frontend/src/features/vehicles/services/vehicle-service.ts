import { createClient } from '@/shared/lib/supabase'
import type { Vehicle } from '@/shared/types/database'

const supabase = createClient()

export interface CreateVehicleData {
  condominium_id: string
  resident_id: string
  license_plate: string
  vehicle_type: 'auto' | 'moto' | 'camion' | 'otro'
  brand?: string
  model?: string
  color?: string
  notes?: string
}

export interface UpdateVehicleData extends Partial<CreateVehicleData> {
  is_authorized?: boolean
}

export const vehicleService = {
  async getAll(condominiumId: string): Promise<(Vehicle & { resident: { full_name: string; apartment: string } })[]> {
    const { data, error } = await supabase
      .from('vehicles')
      .select(`
        *,
        resident:residents(full_name, apartment)
      `)
      .eq('condominium_id', condominiumId)
      .order('license_plate', { ascending: true })

    if (error) throw error
    return data || []
  },

  async getByResident(residentId: string): Promise<Vehicle[]> {
    const { data, error } = await supabase
      .from('vehicles')
      .select('*')
      .eq('resident_id', residentId)
      .order('created_at', { ascending: false })

    if (error) throw error
    return data || []
  },

  async getByPlate(condominiumId: string, plate: string): Promise<Vehicle | null> {
    const { data, error } = await supabase
      .from('vehicles')
      .select(`
        *,
        resident:residents(full_name, apartment, phone)
      `)
      .eq('condominium_id', condominiumId)
      .eq('license_plate', plate.toUpperCase())
      .single()

    if (error && error.code !== 'PGRST116') throw error
    return data
  },

  async create(vehicle: CreateVehicleData): Promise<Vehicle> {
    const { data, error } = await supabase
      .from('vehicles')
      .insert({
        ...vehicle,
        license_plate: vehicle.license_plate.toUpperCase(),
        is_authorized: true,
      })
      .select()
      .single()

    if (error) throw error
    return data
  },

  async update(id: string, vehicle: UpdateVehicleData): Promise<Vehicle> {
    const updateData = { ...vehicle }
    if (vehicle.license_plate) {
      updateData.license_plate = vehicle.license_plate.toUpperCase()
    }

    const { data, error } = await supabase
      .from('vehicles')
      .update(updateData)
      .eq('id', id)
      .select()
      .single()

    if (error) throw error
    return data
  },

  async delete(id: string): Promise<void> {
    const { error } = await supabase
      .from('vehicles')
      .delete()
      .eq('id', id)

    if (error) throw error
  },

  async toggleAuthorized(id: string, isAuthorized: boolean): Promise<Vehicle> {
    return this.update(id, { is_authorized: isAuthorized })
  },
}

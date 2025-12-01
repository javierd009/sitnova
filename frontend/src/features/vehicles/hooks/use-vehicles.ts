'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/features/auth/store/auth-store'
import { vehicleService, type CreateVehicleData, type UpdateVehicleData } from '../services/vehicle-service'
import type { Vehicle } from '@/shared/types/database'

type VehicleWithResident = Vehicle & { resident: { full_name: string; apartment: string } }

export function useVehicles() {
  const { condominium } = useAuthStore()
  const [vehicles, setVehicles] = useState<VehicleWithResident[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadVehicles = useCallback(async () => {
    if (!condominium?.id) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await vehicleService.getAll(condominium.id)
      setVehicles(data)
    } catch (err) {
      console.error('Error loading vehicles:', err)
      setError(err instanceof Error ? err.message : 'Error al cargar vehiculos')
    } finally {
      setIsLoading(false)
    }
  }, [condominium?.id])

  useEffect(() => {
    loadVehicles()
  }, [loadVehicles])

  const createVehicle = async (data: Omit<CreateVehicleData, 'condominium_id'>) => {
    if (!condominium?.id) throw new Error('No condominium selected')

    const newVehicle = await vehicleService.create({
      ...data,
      condominium_id: condominium.id,
    })

    await loadVehicles()
    return newVehicle
  }

  const updateVehicle = async (id: string, data: UpdateVehicleData) => {
    const updated = await vehicleService.update(id, data)
    await loadVehicles()
    return updated
  }

  const deleteVehicle = async (id: string) => {
    await vehicleService.delete(id)
    setVehicles(prev => prev.filter(v => v.id !== id))
  }

  const toggleAuthorized = async (id: string, isAuthorized: boolean) => {
    await vehicleService.toggleAuthorized(id, isAuthorized)
    await loadVehicles()
  }

  return {
    vehicles,
    isLoading,
    error,
    refresh: loadVehicles,
    createVehicle,
    updateVehicle,
    deleteVehicle,
    toggleAuthorized,
  }
}

'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { VehicleForm, type VehicleFormData } from '@/features/vehicles/components/vehicle-form'
import { vehicleService } from '@/features/vehicles/services/vehicle-service'
import type { Vehicle } from '@/shared/types/database'

export default function EditVehiclePage() {
  const params = useParams()
  const vehicleId = params.id as string

  const [vehicle, setVehicle] = useState<Vehicle | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadVehicle = async () => {
      try {
        // For now we'll load from the list and find by id
        // In a real app, you'd have a getById method
        setError('Cargando...')
        setIsLoading(false)
      } catch (err) {
        setError('No se pudo cargar el vehiculo')
        setIsLoading(false)
      }
    }

    loadVehicle()
  }, [vehicleId])

  const handleSubmit = async (data: VehicleFormData) => {
    setIsSaving(true)
    try {
      await vehicleService.update(vehicleId, data)
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Cargando...</div>
      </div>
    )
  }

  return (
    <VehicleForm
      vehicle={vehicle || undefined}
      onSubmit={handleSubmit}
      isLoading={isSaving}
    />
  )
}

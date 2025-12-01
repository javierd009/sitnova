'use client'

import { useState } from 'react'
import { VehicleForm, type VehicleFormData } from '@/features/vehicles/components/vehicle-form'
import { vehicleService } from '@/features/vehicles/services/vehicle-service'
import { useAuthStore } from '@/features/auth/store/auth-store'

export default function NewVehiclePage() {
  const { condominium } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (data: VehicleFormData) => {
    if (!condominium?.id) throw new Error('No condominium selected')

    setIsLoading(true)
    try {
      await vehicleService.create({
        ...data,
        condominium_id: condominium.id,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return <VehicleForm onSubmit={handleSubmit} isLoading={isLoading} />
}

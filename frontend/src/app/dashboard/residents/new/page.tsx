'use client'

import { useState } from 'react'
import { ResidentForm, type ResidentFormData } from '@/features/residents/components/resident-form'
import { residentService } from '@/features/residents/services/resident-service'
import { useAuthStore } from '@/features/auth/store/auth-store'

export default function NewResidentPage() {
  const { condominium } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (data: ResidentFormData) => {
    if (!condominium?.id) throw new Error('No condominium selected')

    setIsLoading(true)
    try {
      await residentService.create({
        ...data,
        condominium_id: condominium.id,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return <ResidentForm onSubmit={handleSubmit} isLoading={isLoading} />
}

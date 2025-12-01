'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { ResidentForm, type ResidentFormData } from '@/features/residents/components/resident-form'
import { residentService } from '@/features/residents/services/resident-service'
import type { Resident } from '@/shared/types/database'

export default function EditResidentPage() {
  const params = useParams()
  const residentId = params.id as string

  const [resident, setResident] = useState<Resident | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadResident = async () => {
      try {
        const data = await residentService.getById(residentId)
        setResident(data)
      } catch (err) {
        setError('No se pudo cargar el residente')
      } finally {
        setIsLoading(false)
      }
    }

    loadResident()
  }, [residentId])

  const handleSubmit = async (data: ResidentFormData) => {
    setIsSaving(true)
    try {
      await residentService.update(residentId, data)
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

  if (error || !resident) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded-lg">
        {error || 'Residente no encontrado'}
      </div>
    )
  }

  return (
    <ResidentForm
      resident={resident}
      onSubmit={handleSubmit}
      isLoading={isSaving}
    />
  )
}

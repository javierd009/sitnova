'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/features/auth/store/auth-store'
import { residentService, type CreateResidentData, type UpdateResidentData } from '../services/resident-service'
import type { Resident } from '@/shared/types/database'

export function useResidents() {
  const { condominium } = useAuthStore()
  const [residents, setResidents] = useState<Resident[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadResidents = useCallback(async () => {
    if (!condominium?.id) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await residentService.getAll(condominium.id)
      setResidents(data)
    } catch (err) {
      console.error('Error loading residents:', err)
      setError(err instanceof Error ? err.message : 'Error al cargar residentes')
    } finally {
      setIsLoading(false)
    }
  }, [condominium?.id])

  useEffect(() => {
    loadResidents()
  }, [loadResidents])

  const createResident = async (data: Omit<CreateResidentData, 'condominium_id'>) => {
    if (!condominium?.id) throw new Error('No condominium selected')

    const newResident = await residentService.create({
      ...data,
      condominium_id: condominium.id,
    })
    setResidents(prev => [...prev, newResident])
    return newResident
  }

  const updateResident = async (id: string, data: UpdateResidentData) => {
    const updated = await residentService.update(id, data)
    setResidents(prev => prev.map(r => r.id === id ? updated : r))
    return updated
  }

  const deleteResident = async (id: string) => {
    await residentService.delete(id)
    setResidents(prev => prev.filter(r => r.id !== id))
  }

  const searchResidents = async (query: string) => {
    if (!condominium?.id) return []
    return residentService.search(condominium.id, query)
  }

  return {
    residents,
    isLoading,
    error,
    refresh: loadResidents,
    createResident,
    updateResident,
    deleteResident,
    searchResidents,
  }
}

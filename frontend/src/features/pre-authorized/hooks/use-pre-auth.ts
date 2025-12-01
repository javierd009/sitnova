'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/features/auth/store/auth-store'
import { preAuthService, type CreatePreAuthData } from '../services/pre-auth-service'
import type { PreAuthorizedVisitor } from '@/shared/types/database'

type PreAuthWithResident = PreAuthorizedVisitor & { resident: { full_name: string; apartment: string } }

export function usePreAuth(activeOnly = false) {
  const { condominium } = useAuthStore()
  const [preAuths, setPreAuths] = useState<PreAuthWithResident[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadPreAuths = useCallback(async () => {
    if (!condominium?.id) return

    setIsLoading(true)
    setError(null)

    try {
      const data = activeOnly
        ? await preAuthService.getActive(condominium.id)
        : await preAuthService.getAll(condominium.id)
      setPreAuths(data)
    } catch (err) {
      console.error('Error loading pre-authorizations:', err)
      setError(err instanceof Error ? err.message : 'Error al cargar pre-autorizaciones')
    } finally {
      setIsLoading(false)
    }
  }, [condominium?.id, activeOnly])

  useEffect(() => {
    loadPreAuths()
  }, [loadPreAuths])

  const createPreAuth = async (data: Omit<CreatePreAuthData, 'condominium_id'>) => {
    if (!condominium?.id) throw new Error('No condominium selected')

    const newPreAuth = await preAuthService.create({
      ...data,
      condominium_id: condominium.id,
    })

    await loadPreAuths()
    return newPreAuth
  }

  const deletePreAuth = async (id: string) => {
    await preAuthService.delete(id)
    setPreAuths(prev => prev.filter(p => p.id !== id))
  }

  return {
    preAuths,
    isLoading,
    error,
    refresh: loadPreAuths,
    createPreAuth,
    deletePreAuth,
  }
}

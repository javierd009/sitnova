'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/features/auth/store/auth-store'
import { dashboardService } from '../services/dashboard-service'
import type { AccessLog, AccessStats } from '@/shared/types/database'

export function useDashboard() {
  const { condominium } = useAuthStore()
  const [stats, setStats] = useState<AccessStats | null>(null)
  const [recentLogs, setRecentLogs] = useState<AccessLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    if (!condominium?.id) return

    setIsLoading(true)
    setError(null)

    try {
      const [statsData, logsData] = await Promise.all([
        dashboardService.getStats(condominium.id),
        dashboardService.getRecentAccess(condominium.id, 10),
      ])

      setStats(statsData)
      setRecentLogs(logsData)
    } catch (err) {
      console.error('Error loading dashboard:', err)
      setError(err instanceof Error ? err.message : 'Error al cargar datos')
    } finally {
      setIsLoading(false)
    }
  }, [condominium?.id])

  useEffect(() => {
    loadData()

    // Actualizar cada 30 segundos
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  return {
    stats,
    recentLogs,
    isLoading,
    error,
    refresh: loadData,
  }
}

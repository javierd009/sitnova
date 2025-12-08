'use client'

import { useState, useEffect, useCallback } from 'react'
import { monitoringService, type DashboardData } from '../services/monitoring-service'

export function useMonitoring(refreshInterval = 30000) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    try {
      const result = await monitoringService.getDashboard()
      setData(result)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error loading monitoring data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()

    // Auto-refresh
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [fetchData, refreshInterval])

  const resolveAlert = async (alertId: string) => {
    try {
      await monitoringService.resolveAlert(alertId)
      await fetchData() // Refresh after resolving
    } catch (err) {
      throw err
    }
  }

  return {
    data,
    isLoading,
    error,
    refresh: fetchData,
    resolveAlert,
  }
}

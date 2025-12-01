'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuthStore } from '@/features/auth/store/auth-store'
import { accessLogService, type AccessLogFilters } from '../services/access-log-service'
import type { AccessLog } from '@/shared/types/database'

export function useAccessLogs() {
  const { condominium } = useAuthStore()
  const [logs, setLogs] = useState<AccessLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<AccessLogFilters>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const limit = 50

  const loadLogs = useCallback(async () => {
    if (!condominium?.id) return

    setIsLoading(true)
    setError(null)

    try {
      const { data, total: totalCount } = await accessLogService.getAll(
        condominium.id,
        filters,
        page,
        limit
      )
      setLogs(data)
      setTotal(totalCount)
    } catch (err) {
      console.error('Error loading access logs:', err)
      setError(err instanceof Error ? err.message : 'Error al cargar historial')
    } finally {
      setIsLoading(false)
    }
  }, [condominium?.id, filters, page])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  const updateFilters = (newFilters: AccessLogFilters) => {
    setFilters(newFilters)
    setPage(1)
  }

  const exportCSV = async () => {
    if (!condominium?.id) return

    try {
      const csv = await accessLogService.exportToCSV(condominium.id, filters)
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `accesos_${new Date().toISOString().split('T')[0]}.csv`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error exporting CSV:', err)
      alert('Error al exportar')
    }
  }

  return {
    logs,
    total,
    page,
    totalPages: Math.ceil(total / limit),
    filters,
    isLoading,
    error,
    setPage,
    updateFilters,
    refresh: loadLogs,
    exportCSV,
  }
}

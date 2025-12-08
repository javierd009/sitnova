/**
 * useBitacora Hook
 *
 * Hook for managing bitácora data fetching with polling support.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  fetchBitacora,
  fetchUltimosAccesos,
  fetchEstadisticas,
  BitacoraResponse,
  BitacoraEntry,
  EstadisticasDiarias,
  BitacoraFilters,
} from '../services/bitacora-service'

interface UseBitacoraResult {
  data: BitacoraResponse | null
  ultimos: BitacoraEntry[]
  estadisticas: EstadisticasDiarias[]
  isLoading: boolean
  error: string | null
  filters: BitacoraFilters
  setFilters: (filters: BitacoraFilters) => void
  refresh: () => Promise<void>
  nextPage: () => void
  prevPage: () => void
}

export function useBitacora(
  initialFilters: BitacoraFilters = {},
  pollingInterval: number = 30000
): UseBitacoraResult {
  const [data, setData] = useState<BitacoraResponse | null>(null)
  const [ultimos, setUltimos] = useState<BitacoraEntry[]>([])
  const [estadisticas, setEstadisticas] = useState<EstadisticasDiarias[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<BitacoraFilters>({
    page: 1,
    page_size: 20,
    ...initialFilters,
  })

  const fetchData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [bitacoraData, ultimosData, estadisticasData] = await Promise.all([
        fetchBitacora(filters),
        fetchUltimosAccesos(5),
        fetchEstadisticas(7),
      ])

      setData(bitacoraData)
      setUltimos(ultimosData)
      setEstadisticas(estadisticasData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setIsLoading(false)
    }
  }, [filters])

  // Initial fetch and polling
  useEffect(() => {
    fetchData()

    if (pollingInterval > 0) {
      const interval = setInterval(fetchData, pollingInterval)
      return () => clearInterval(interval)
    }
  }, [fetchData, pollingInterval])

  const refresh = useCallback(async () => {
    await fetchData()
  }, [fetchData])

  const nextPage = useCallback(() => {
    if (data?.has_more) {
      setFilters((prev) => ({
        ...prev,
        page: (prev.page || 1) + 1,
      }))
    }
  }, [data?.has_more])

  const prevPage = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      page: Math.max(1, (prev.page || 1) - 1),
    }))
  }, [])

  return {
    data,
    ultimos,
    estadisticas,
    isLoading,
    error,
    filters,
    setFilters,
    refresh,
    nextPage,
    prevPage,
  }
}

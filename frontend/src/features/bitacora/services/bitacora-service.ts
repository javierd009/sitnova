/**
 * Bitácora Service
 *
 * Service for interacting with bitácora data via Supabase directly.
 * This eliminates the dependency on the backend API for read operations.
 */

import { createClient } from '@/shared/lib/supabase'

export interface BitacoraEntry {
  id: string
  condominium_id?: string
  visitor_name?: string
  visitor_cedula?: string
  visitor_type?: string
  vehicle_plate?: string
  resident_name?: string
  apartment?: string
  visit_reason?: string
  access_result: string
  authorization_method?: string
  call_duration_seconds?: number
  created_at: string
}

export interface BitacoraResponse {
  entries: BitacoraEntry[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface EstadisticasDiarias {
  fecha: string
  total_accesos: number
  autorizados: number
  denegados: number
  pre_autorizados: number
  sin_respuesta: number
  transferidos: number
  vehiculos: number
  deliveries: number
  duracion_promedio_llamada?: number
}

export interface BitacoraFilters {
  page?: number
  page_size?: number
  condominium_id?: string
  access_result?: string
  visitor_type?: string
  apartment?: string
  search?: string
  date_from?: string
  date_to?: string
}

export async function fetchBitacora(filters: BitacoraFilters = {}): Promise<BitacoraResponse> {
  const supabase = createClient()
  const page = filters.page || 1
  const pageSize = filters.page_size || 20
  const offset = (page - 1) * pageSize

  // Build query
  let query = supabase
    .from('bitacora_accesos')
    .select('*', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + pageSize - 1)

  // Apply filters
  if (filters.condominium_id) {
    query = query.eq('condominium_id', filters.condominium_id)
  }
  if (filters.access_result) {
    query = query.eq('access_result', filters.access_result)
  }
  if (filters.visitor_type) {
    query = query.eq('visitor_type', filters.visitor_type)
  }
  if (filters.apartment) {
    query = query.eq('apartment', filters.apartment)
  }
  if (filters.date_from) {
    query = query.gte('created_at', filters.date_from)
  }
  if (filters.date_to) {
    query = query.lte('created_at', filters.date_to)
  }
  if (filters.search) {
    // Search in multiple fields using OR
    query = query.or(
      `visitor_name.ilike.%${filters.search}%,visitor_cedula.ilike.%${filters.search}%,vehicle_plate.ilike.%${filters.search}%,resident_name.ilike.%${filters.search}%,apartment.ilike.%${filters.search}%`
    )
  }

  const { data, error, count } = await query

  if (error) {
    throw new Error(`Error fetching bitácora: ${error.message}`)
  }

  const total = count || 0
  return {
    entries: data || [],
    total,
    page,
    page_size: pageSize,
    has_more: offset + pageSize < total,
  }
}

export async function fetchUltimosAccesos(limit: number = 10): Promise<BitacoraEntry[]> {
  const supabase = createClient()

  const { data, error } = await supabase
    .from('bitacora_accesos')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(limit)

  if (error) {
    throw new Error(`Error fetching últimos accesos: ${error.message}`)
  }

  return data || []
}

export async function fetchEstadisticas(days: number = 7): Promise<EstadisticasDiarias[]> {
  const supabase = createClient()

  // Calculate date range
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)

  // Use the view for daily statistics
  const { data, error } = await supabase
    .from('bitacora_estadisticas_diarias')
    .select('*')
    .gte('fecha', startDate.toISOString().split('T')[0])
    .lte('fecha', endDate.toISOString().split('T')[0])
    .order('fecha', { ascending: false })

  if (error) {
    // If view doesn't exist, calculate manually
    console.warn('Vista bitacora_estadisticas_diarias no disponible, calculando manualmente')
    return calculateEstadisticasManually(supabase, startDate, endDate)
  }

  return data || []
}

async function calculateEstadisticasManually(
  supabase: ReturnType<typeof createClient>,
  startDate: Date,
  endDate: Date
): Promise<EstadisticasDiarias[]> {
  const { data, error } = await supabase
    .from('bitacora_accesos')
    .select('*')
    .gte('created_at', startDate.toISOString())
    .lte('created_at', endDate.toISOString())

  if (error || !data) {
    return []
  }

  // Group by date using object (avoids Map iteration issues)
  const byDate: Record<string, BitacoraEntry[]> = {}
  for (const entry of data) {
    const fecha = new Date(entry.created_at).toISOString().split('T')[0]
    if (!byDate[fecha]) {
      byDate[fecha] = []
    }
    byDate[fecha].push(entry)
  }

  // Calculate statistics for each day
  const stats: EstadisticasDiarias[] = Object.entries(byDate).map(([fecha, entries]) => ({
    fecha,
    total_accesos: entries.length,
    autorizados: entries.filter((e) => e.access_result === 'autorizado').length,
    denegados: entries.filter((e) => e.access_result === 'denegado').length,
    pre_autorizados: entries.filter((e) => e.access_result === 'pre_autorizado').length,
    sin_respuesta: entries.filter((e) => e.access_result === 'timeout').length,
    transferidos: entries.filter((e) => e.access_result === 'transferido').length,
    vehiculos: entries.filter((e) => e.visitor_type === 'vehiculo').length,
    deliveries: entries.filter((e) => e.visitor_type === 'delivery').length,
    duracion_promedio_llamada: calculateAvgDuration(entries),
  }))

  return stats.sort((a, b) => b.fecha.localeCompare(a.fecha))
}

function calculateAvgDuration(entries: BitacoraEntry[]): number | undefined {
  const durations = entries
    .map((e) => e.call_duration_seconds)
    .filter((d): d is number => d !== null && d !== undefined)

  if (durations.length === 0) return undefined
  return Math.round(durations.reduce((a, b) => a + b, 0) / durations.length)
}

export function getAccessResultColor(result: string): string {
  switch (result) {
    case 'autorizado':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'denegado':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'pre_autorizado':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'timeout':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'transferido':
      return 'bg-purple-100 text-purple-800 border-purple-200'
    case 'error':
      return 'bg-gray-100 text-gray-800 border-gray-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

export function getAccessResultLabel(result: string): string {
  switch (result) {
    case 'autorizado':
      return 'Autorizado'
    case 'denegado':
      return 'Denegado'
    case 'pre_autorizado':
      return 'Pre-autorizado'
    case 'timeout':
      return 'Sin respuesta'
    case 'transferido':
      return 'Transferido'
    case 'error':
      return 'Error'
    default:
      return result
  }
}

export function getVisitorTypeLabel(type: string): string {
  switch (type) {
    case 'persona':
      return 'Persona'
    case 'vehiculo':
      return 'Vehículo'
    case 'delivery':
      return 'Delivery'
    case 'servicio':
      return 'Servicio'
    case 'otro':
      return 'Otro'
    default:
      return type
  }
}

export function formatDuration(seconds?: number): string {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

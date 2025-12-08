/**
 * Bitácora Service
 *
 * Service for interacting with the bitácora API endpoints.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
  const params = new URLSearchParams()

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, String(value))
    }
  })

  const response = await fetch(`${API_BASE}/bitacora?${params.toString()}`)

  if (!response.ok) {
    throw new Error(`Error fetching bitácora: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchUltimosAccesos(limit: number = 10): Promise<BitacoraEntry[]> {
  const response = await fetch(`${API_BASE}/bitacora/ultimos?limit=${limit}`)

  if (!response.ok) {
    throw new Error(`Error fetching últimos accesos: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchEstadisticas(days: number = 7): Promise<EstadisticasDiarias[]> {
  const response = await fetch(`${API_BASE}/bitacora/estadisticas?days=${days}`)

  if (!response.ok) {
    throw new Error(`Error fetching estadísticas: ${response.statusText}`)
  }

  return response.json()
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

/**
 * Monitoring Service
 *
 * Service for fetching system health and monitoring data.
 * Uses the backend API for health checks (cannot be replaced with Supabase).
 *
 * IMPORTANT: Requires NEXT_PUBLIC_API_URL environment variable in Vercel:
 * NEXT_PUBLIC_API_URL=https://api.sitnova.integratec-ia.com
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.sitnova.integratec-ia.com'

export interface ServiceHealth {
  name: string
  display_name: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  response_time_ms: number | null
  message: string | null
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  uptime_percentage: number
  services_total: number
  services_healthy: number
}

export interface AccessStats {
  total_today: number
  granted_today: number
  denied_today: number
  pending_today: number
  success_rate: number
}

export interface Alert {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  service: string
  message: string
  timestamp: string
}

export interface DashboardData {
  timestamp: string
  system: SystemHealth
  services: ServiceHealth[]
  access_stats: AccessStats
  alerts: {
    count: number
    items: Alert[]
  }
}

export const monitoringService = {
  async getDashboard(): Promise<DashboardData> {
    const response = await fetch(`${API_BASE}/monitoring/dashboard`, {
      headers: {
        'Content-Type': 'application/json',
      },
      // Add timeout and better error handling
      signal: AbortSignal.timeout(10000),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
  },

  async getServices(): Promise<{ overall_status: string; services: Record<string, ServiceHealth> }> {
    const response = await fetch(`${API_BASE}/monitoring/services`, {
      signal: AbortSignal.timeout(10000),
    })
    if (!response.ok) throw new Error('Failed to fetch services')
    return response.json()
  },

  async getAlerts(): Promise<{ count: number; alerts: Alert[] }> {
    const response = await fetch(`${API_BASE}/monitoring/alerts`, {
      signal: AbortSignal.timeout(10000),
    })
    if (!response.ok) throw new Error('Failed to fetch alerts')
    return response.json()
  },

  async resolveAlert(alertId: string): Promise<void> {
    const response = await fetch(`${API_BASE}/monitoring/alerts/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ alert_id: alertId }),
      signal: AbortSignal.timeout(10000),
    })
    if (!response.ok) throw new Error('Failed to resolve alert')
  },
}

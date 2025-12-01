import { createClient } from '@/shared/lib/supabase'
import type { AccessLog, AccessStats } from '@/shared/types/database'

const supabase = createClient()

export const dashboardService = {
  async getStats(condominiumId: string): Promise<AccessStats> {
    const today = new Date().toISOString().split('T')[0]

    // Obtener accesos de hoy
    const { data: todayLogs, error: logsError } = await supabase
      .from('access_logs')
      .select('access_decision')
      .eq('condominium_id', condominiumId)
      .gte('created_at', `${today}T00:00:00`)
      .lte('created_at', `${today}T23:59:59`)

    if (logsError) throw logsError

    // Contar vehiculos autorizados
    const { count: vehiclesCount, error: vehiclesError } = await supabase
      .from('vehicles')
      .select('*', { count: 'exact', head: true })
      .eq('condominium_id', condominiumId)
      .eq('is_authorized', true)

    if (vehiclesError) throw vehiclesError

    // Contar pre-autorizados activos
    const now = new Date().toISOString()
    const { count: preAuthCount, error: preAuthError } = await supabase
      .from('pre_authorized_visitors')
      .select('*', { count: 'exact', head: true })
      .eq('condominium_id', condominiumId)
      .lte('valid_from', now)
      .gte('valid_until', now)
      .eq('used', false)

    if (preAuthError) throw preAuthError

    const total = todayLogs?.length || 0
    const granted = todayLogs?.filter(l => l.access_decision === 'granted').length || 0
    const denied = todayLogs?.filter(l => l.access_decision === 'denied').length || 0
    const pending = todayLogs?.filter(l => l.access_decision === 'pending').length || 0

    return {
      total_today: total,
      granted_today: granted,
      denied_today: denied,
      pending_today: pending,
      vehicles_authorized: vehiclesCount || 0,
      pre_authorized_active: preAuthCount || 0,
    }
  },

  async getRecentAccess(condominiumId: string, limit = 10): Promise<AccessLog[]> {
    const { data, error } = await supabase
      .from('access_logs')
      .select('*')
      .eq('condominium_id', condominiumId)
      .order('created_at', { ascending: false })
      .limit(limit)

    if (error) throw error
    return data || []
  },

  async getAccessByHour(condominiumId: string): Promise<{ hour: number; count: number }[]> {
    const today = new Date().toISOString().split('T')[0]

    const { data, error } = await supabase
      .from('access_logs')
      .select('created_at')
      .eq('condominium_id', condominiumId)
      .gte('created_at', `${today}T00:00:00`)

    if (error) throw error

    // Agrupar por hora
    const hourCounts: Record<number, number> = {}
    for (let i = 0; i < 24; i++) {
      hourCounts[i] = 0
    }

    data?.forEach(log => {
      const hour = new Date(log.created_at).getHours()
      hourCounts[hour]++
    })

    return Object.entries(hourCounts).map(([hour, count]) => ({
      hour: parseInt(hour),
      count,
    }))
  },
}

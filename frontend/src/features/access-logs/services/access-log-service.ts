import { createClient } from '@/shared/lib/supabase'
import type { AccessLog } from '@/shared/types/database'

const supabase = createClient()

export interface AccessLogFilters {
  startDate?: string
  endDate?: string
  decision?: 'granted' | 'denied' | 'pending'
  entryType?: 'vehicle' | 'pedestrian' | 'delivery'
  plate?: string
  apartment?: string
}

export const accessLogService = {
  async getAll(
    condominiumId: string,
    filters?: AccessLogFilters,
    page = 1,
    limit = 50
  ): Promise<{ data: AccessLog[]; total: number }> {
    let query = supabase
      .from('access_logs')
      .select('*', { count: 'exact' })
      .eq('condominium_id', condominiumId)

    if (filters?.startDate) {
      query = query.gte('created_at', `${filters.startDate}T00:00:00`)
    }
    if (filters?.endDate) {
      query = query.lte('created_at', `${filters.endDate}T23:59:59`)
    }
    if (filters?.decision) {
      query = query.eq('access_decision', filters.decision)
    }
    if (filters?.entryType) {
      query = query.eq('entry_type', filters.entryType)
    }
    if (filters?.plate) {
      query = query.ilike('license_plate', `%${filters.plate}%`)
    }
    if (filters?.apartment) {
      query = query.ilike('apartment', `%${filters.apartment}%`)
    }

    const offset = (page - 1) * limit
    query = query
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    const { data, count, error } = await query

    if (error) throw error

    return {
      data: data || [],
      total: count || 0,
    }
  },

  async getById(id: string): Promise<AccessLog> {
    const { data, error } = await supabase
      .from('access_logs')
      .select('*')
      .eq('id', id)
      .single()

    if (error) throw error
    return data
  },

  async exportToCSV(condominiumId: string, filters?: AccessLogFilters): Promise<string> {
    const { data } = await this.getAll(condominiumId, filters, 1, 10000)

    const headers = [
      'Fecha',
      'Hora',
      'Tipo',
      'Placa',
      'Cedula',
      'Visitante',
      'Residente',
      'Casa',
      'Decision',
      'Tipo Autorizacion',
      'Razon Denegacion',
    ]

    const rows = data.map(log => [
      new Date(log.created_at).toLocaleDateString('es-CR'),
      new Date(log.created_at).toLocaleTimeString('es-CR'),
      log.entry_type,
      log.license_plate || '',
      log.cedula || '',
      log.visitor_name || '',
      log.resident_name || '',
      log.apartment || '',
      log.access_decision,
      log.authorization_type || '',
      log.denial_reason || '',
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
    ].join('\n')

    return csvContent
  },
}

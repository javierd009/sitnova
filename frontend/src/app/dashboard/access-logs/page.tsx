'use client'

import { useState } from 'react'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import {
  Download,
  Filter,
  ChevronLeft,
  ChevronRight,
  Car,
  User,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table'
import { useAccessLogs } from '@/features/access-logs/hooks/use-access-logs'
import { cn } from '@/shared/utils/cn'

export default function AccessLogsPage() {
  const {
    logs,
    total,
    page,
    totalPages,
    filters,
    isLoading,
    error,
    setPage,
    updateFilters,
    exportCSV,
  } = useAccessLogs()

  const [showFilters, setShowFilters] = useState(false)
  const [localFilters, setLocalFilters] = useState(filters)

  const applyFilters = () => {
    updateFilters(localFilters)
    setShowFilters(false)
  }

  const clearFilters = () => {
    setLocalFilters({})
    updateFilters({})
    setShowFilters(false)
  }

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'granted':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-green-50 text-green-700">
            <CheckCircle className="w-3 h-3" />
            Autorizado
          </span>
        )
      case 'denied':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700">
            <XCircle className="w-3 h-3" />
            Denegado
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700">
            <Clock className="w-3 h-3" />
            Pendiente
          </span>
        )
    }
  }

  const authTypeLabels: Record<string, string> = {
    auto_placa: 'Placa Autorizada',
    residente: 'Residente',
    admin: 'Admin',
    pre_autorizado: 'Pre-autorizado',
    protocolo: 'Protocolo',
    delivery: 'Delivery',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Historial de Accesos</h1>
          <p className="text-gray-500">Registro de todos los eventos de acceso</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <Filter size={16} />
            Filtros
          </Button>
          <Button variant="outline" onClick={exportCSV} className="gap-2">
            <Download size={16} />
            Exportar CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Filtros</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <Input
                label="Fecha Inicio"
                type="date"
                value={localFilters.startDate || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, startDate: e.target.value })}
              />
              <Input
                label="Fecha Fin"
                type="date"
                value={localFilters.endDate || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, endDate: e.target.value })}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Decision</label>
                <select
                  value={localFilters.decision || ''}
                  onChange={(e) => setLocalFilters({ ...localFilters, decision: e.target.value as AccessLogFilters['decision'] })}
                  className="block w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Todas</option>
                  <option value="granted">Autorizados</option>
                  <option value="denied">Denegados</option>
                  <option value="pending">Pendientes</option>
                </select>
              </div>
              <Input
                label="Placa"
                placeholder="ABC-123"
                value={localFilters.plate || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, plate: e.target.value })}
              />
              <Input
                label="Casa/Apto"
                placeholder="101"
                value={localFilters.apartment || ''}
                onChange={(e) => setLocalFilters({ ...localFilters, apartment: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button variant="ghost" onClick={clearFilters}>Limpiar</Button>
              <Button onClick={applyFilters}>Aplicar Filtros</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Eventos ({total})</CardTitle>
          <div className="text-sm text-gray-500">
            Pagina {page} de {totalPages || 1}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : logs.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No hay registros</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha/Hora</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Placa/Visitante</TableHead>
                  <TableHead>Residente</TableHead>
                  <TableHead>Casa</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Autorizacion</TableHead>
                  <TableHead className="text-right">Ver</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="whitespace-nowrap">
                      <div className="text-sm">
                        {format(new Date(log.created_at), 'dd/MM/yyyy', { locale: es })}
                      </div>
                      <div className="text-xs text-gray-500">
                        {format(new Date(log.created_at), 'HH:mm:ss', { locale: es })}
                      </div>
                    </TableCell>
                    <TableCell>
                      {log.entry_type === 'vehicle' ? (
                        <span className="inline-flex items-center gap-1 text-gray-600">
                          <Car className="w-4 h-4" />
                          Vehiculo
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-gray-600">
                          <User className="w-4 h-4" />
                          Peaton
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="font-mono font-medium">
                        {log.license_plate || log.visitor_name || '-'}
                      </div>
                      {log.cedula && (
                        <div className="text-xs text-gray-500">CI: {log.cedula}</div>
                      )}
                    </TableCell>
                    <TableCell>{log.resident_name || '-'}</TableCell>
                    <TableCell>{log.apartment || '-'}</TableCell>
                    <TableCell>{getDecisionBadge(log.access_decision)}</TableCell>
                    <TableCell>
                      <span className="text-xs text-gray-600">
                        {log.authorization_type
                          ? authTypeLabels[log.authorization_type] || log.authorization_type
                          : '-'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" asChild href={`/dashboard/access-logs/${log.id}`}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="border-t border-gray-200 px-4 py-3 flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page - 1)}
              disabled={page <= 1}
              className="gap-1"
            >
              <ChevronLeft size={16} />
              Anterior
            </Button>
            <span className="text-sm text-gray-500">
              Pagina {page} de {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(page + 1)}
              disabled={page >= totalPages}
              className="gap-1"
            >
              Siguiente
              <ChevronRight size={16} />
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}

interface AccessLogFilters {
  startDate?: string
  endDate?: string
  decision?: 'granted' | 'denied' | 'pending'
  entryType?: 'vehicle' | 'pedestrian' | 'delivery'
  plate?: string
  apartment?: string
}

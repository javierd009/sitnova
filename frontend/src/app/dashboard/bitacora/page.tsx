'use client'

import { useState } from 'react'
import {
  RefreshCw,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  User,
  Car,
  Package,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Phone,
} from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { useBitacora } from '@/features/bitacora/hooks/use-bitacora'
import {
  getAccessResultColor,
  getAccessResultLabel,
  getVisitorTypeLabel,
  formatDuration,
} from '@/features/bitacora/services/bitacora-service'
import { cn } from '@/shared/utils/cn'

const visitorTypeIcons: Record<string, React.ReactNode> = {
  persona: <User className="w-4 h-4" />,
  vehiculo: <Car className="w-4 h-4" />,
  delivery: <Package className="w-4 h-4" />,
  servicio: <User className="w-4 h-4" />,
  otro: <User className="w-4 h-4" />,
}

const accessResultIcons: Record<string, React.ReactNode> = {
  autorizado: <CheckCircle className="w-4 h-4 text-green-600" />,
  denegado: <XCircle className="w-4 h-4 text-red-600" />,
  pre_autorizado: <CheckCircle className="w-4 h-4 text-blue-600" />,
  timeout: <Clock className="w-4 h-4 text-yellow-600" />,
  transferido: <Phone className="w-4 h-4 text-purple-600" />,
  error: <AlertTriangle className="w-4 h-4 text-gray-600" />,
}

export default function BitacoraPage() {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedResult, setSelectedResult] = useState<string>('')
  const [selectedType, setSelectedType] = useState<string>('')

  const {
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
  } = useBitacora({}, 30000)

  const handleSearch = () => {
    setFilters({
      ...filters,
      search: searchTerm,
      access_result: selectedResult || undefined,
      visitor_type: selectedType || undefined,
      page: 1,
    })
  }

  const todayStats = estadisticas[0] || {
    total_accesos: 0,
    autorizados: 0,
    denegados: 0,
    pre_autorizados: 0,
  }

  if (isLoading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="p-6 bg-red-50 text-red-700 rounded-lg">
        <h3 className="font-bold">Error cargando bitácora</h3>
        <p className="text-sm mt-1">{error}</p>
        <Button onClick={refresh} className="mt-4" variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Reintentar
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Bitácora de Accesos</h1>
          <p className="text-gray-500">Registro de todos los intentos de acceso</p>
        </div>
        <Button onClick={refresh} variant="outline" size="sm">
          <RefreshCw className={cn("w-4 h-4 mr-2", isLoading && "animate-spin")} />
          Actualizar
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Hoy</p>
                <p className="text-2xl font-bold">{todayStats.total_accesos}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <User className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Autorizados</p>
                <p className="text-2xl font-bold text-green-600">{todayStats.autorizados}</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Denegados</p>
                <p className="text-2xl font-bold text-red-600">{todayStats.denegados}</p>
              </div>
              <div className="p-3 bg-red-100 rounded-full">
                <XCircle className="w-6 h-6 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Pre-autorizados</p>
                <p className="text-2xl font-bold text-blue-600">{todayStats.pre_autorizados}</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <CheckCircle className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Últimos Accesos (Real-time) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Últimos Accesos (Tiempo Real)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {ultimos.map((entry) => (
              <div
                key={entry.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded-full shadow-sm">
                    {visitorTypeIcons[entry.visitor_type || 'persona']}
                  </div>
                  <div>
                    <p className="font-medium">{entry.visitor_name || 'Visitante'}</p>
                    <p className="text-sm text-gray-500">
                      {entry.apartment} - {entry.visit_reason || 'Sin motivo'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={cn(
                      'px-2 py-1 text-xs font-medium rounded-full border',
                      getAccessResultColor(entry.access_result)
                    )}
                  >
                    {getAccessResultLabel(entry.access_result)}
                  </span>
                  <span className="text-sm text-gray-500">
                    {new Date(entry.created_at).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input
                  type="text"
                  placeholder="Buscar por nombre, cédula, placa..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                />
              </div>
            </div>

            <select
              value={selectedResult}
              onChange={(e) => setSelectedResult(e.target.value)}
              className="px-4 py-2 border rounded-lg"
            >
              <option value="">Todos los resultados</option>
              <option value="autorizado">Autorizado</option>
              <option value="denegado">Denegado</option>
              <option value="pre_autorizado">Pre-autorizado</option>
              <option value="timeout">Sin respuesta</option>
              <option value="transferido">Transferido</option>
            </select>

            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-4 py-2 border rounded-lg"
            >
              <option value="">Todos los tipos</option>
              <option value="persona">Persona</option>
              <option value="vehiculo">Vehículo</option>
              <option value="delivery">Delivery</option>
              <option value="servicio">Servicio</option>
            </select>

            <Button onClick={handleSearch}>
              <Filter className="w-4 h-4 mr-2" />
              Filtrar
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Fecha/Hora
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Visitante
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Cédula
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Destino
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Motivo
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Tipo
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Resultado
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    Duración
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data?.entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm">
                      <div>
                        <p className="font-medium">
                          {new Date(entry.created_at).toLocaleDateString()}
                        </p>
                        <p className="text-gray-500">
                          {new Date(entry.created_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        {visitorTypeIcons[entry.visitor_type || 'persona']}
                        <span>{entry.visitor_name || '-'}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">
                      {entry.visitor_cedula || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div>
                        <p className="font-medium">{entry.apartment || '-'}</p>
                        <p className="text-gray-500 text-xs">{entry.resident_name || ''}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm max-w-[200px] truncate">
                      {entry.visit_reason || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="inline-flex items-center gap-1">
                        {visitorTypeIcons[entry.visitor_type || 'persona']}
                        {getVisitorTypeLabel(entry.visitor_type || 'persona')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full border',
                          getAccessResultColor(entry.access_result)
                        )}
                      >
                        {accessResultIcons[entry.access_result]}
                        {getAccessResultLabel(entry.access_result)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {formatDuration(entry.call_duration_seconds)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && (
            <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <p className="text-sm text-gray-500">
                Mostrando {((filters.page || 1) - 1) * (filters.page_size || 20) + 1} -{' '}
                {Math.min(
                  (filters.page || 1) * (filters.page_size || 20),
                  data.total
                )}{' '}
                de {data.total} registros
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={prevPage}
                  disabled={(filters.page || 1) <= 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-gray-600">
                  Página {filters.page || 1}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={nextPage}
                  disabled={!data.has_more}
                >
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

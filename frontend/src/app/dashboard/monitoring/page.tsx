'use client'

import { RefreshCw, CheckCircle, AlertTriangle, XCircle, Clock, Activity, Shield, Bell } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { useMonitoring } from '@/features/monitoring/hooks/use-monitoring'
import { cn } from '@/shared/utils/cn'

const statusColors = {
  healthy: 'bg-green-500',
  degraded: 'bg-yellow-500',
  unhealthy: 'bg-red-500',
  unknown: 'bg-gray-400',
}

const statusBgColors = {
  healthy: 'bg-green-50 text-green-700 border-green-200',
  degraded: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  unhealthy: 'bg-red-50 text-red-700 border-red-200',
  unknown: 'bg-gray-50 text-gray-700 border-gray-200',
}

const alertLevelColors = {
  info: 'bg-blue-50 text-blue-700 border-blue-200',
  warning: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  error: 'bg-orange-50 text-orange-700 border-orange-200',
  critical: 'bg-red-50 text-red-700 border-red-200',
}

const serviceIcons: Record<string, React.ReactNode> = {
  'Base de Datos': <Shield className="w-5 h-5" />,
  'Voice AI': <Activity className="w-5 h-5" />,
  'Control de Acceso': <Shield className="w-5 h-5" />,
  'WhatsApp': <Bell className="w-5 h-5" />,
  'Agente IA': <Activity className="w-5 h-5" />,
}

export default function MonitoringPage() {
  const { data, isLoading, error, refresh, resolveAlert } = useMonitoring(30000)

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
        <h3 className="font-bold">Error cargando datos de monitoreo</h3>
        <p className="text-sm mt-1">{error}</p>
        <Button onClick={refresh} className="mt-4" variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Reintentar
        </Button>
      </div>
    )
  }

  if (!data) return null

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'degraded':
        return <AlertTriangle className="w-5 h-5 text-yellow-600" />
      case 'unhealthy':
        return <XCircle className="w-5 h-5 text-red-600" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monitoreo del Sistema</h1>
          <p className="text-gray-500">Estado en tiempo real de todos los servicios</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            Actualizado: {new Date(data.timestamp).toLocaleTimeString()}
          </span>
          <Button onClick={refresh} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualizar
          </Button>
        </div>
      </div>

      {/* System Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className={cn('border-2', statusBgColors[data.system.status])}>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              {getStatusIcon(data.system.status)}
              <div>
                <p className="text-sm font-medium">Estado General</p>
                <p className="text-lg font-bold capitalize">{data.system.status}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Activity className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Uptime</p>
                <p className="text-lg font-bold">{data.system.uptime_percentage}%</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Servicios Activos</p>
                <p className="text-lg font-bold">
                  {data.system.services_healthy} / {data.system.services_total}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                'p-2 rounded-lg',
                data.alerts.count > 0 ? 'bg-red-50' : 'bg-gray-50'
              )}>
                <Bell className={cn(
                  'w-5 h-5',
                  data.alerts.count > 0 ? 'text-red-600' : 'text-gray-400'
                )} />
              </div>
              <div>
                <p className="text-sm text-gray-500">Alertas Activas</p>
                <p className="text-lg font-bold">{data.alerts.count}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Services Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Estado de Servicios</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.services.map((service) => (
              <div
                key={service.name}
                className={cn(
                  'p-4 rounded-lg border-2 transition-all',
                  statusBgColors[service.status]
                )}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-white/50 rounded-lg">
                      {serviceIcons[service.display_name] || <Activity className="w-5 h-5" />}
                    </div>
                    <div>
                      <p className="font-medium">{service.display_name}</p>
                      <p className="text-sm opacity-75">{service.message || 'Sin datos'}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end">
                    <div className={cn('w-3 h-3 rounded-full', statusColors[service.status])} />
                    {service.response_time_ms && (
                      <span className="text-xs mt-1">{Math.round(service.response_time_ms)}ms</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Access Stats */}
        <Card>
          <CardHeader>
            <CardTitle>Estadisticas de Acceso Hoy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-gray-600">Total de Accesos</span>
                <span className="text-xl font-bold">{data.access_stats.total_today}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <span className="text-green-700">Autorizados</span>
                <span className="text-xl font-bold text-green-700">{data.access_stats.granted_today}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                <span className="text-red-700">Denegados</span>
                <span className="text-xl font-bold text-red-700">{data.access_stats.denied_today}</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                <span className="text-yellow-700">Pendientes</span>
                <span className="text-xl font-bold text-yellow-700">{data.access_stats.pending_today}</span>
              </div>
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Tasa de Exito</span>
                  <span className="text-2xl font-bold text-primary-600">
                    {data.access_stats.success_rate}%
                  </span>
                </div>
                <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-600 rounded-full transition-all"
                    style={{ width: `${data.access_stats.success_rate}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Alertas Recientes</span>
              {data.alerts.count > 0 && (
                <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">
                  {data.alerts.count} activas
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.alerts.items.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
                <p>No hay alertas activas</p>
                <p className="text-sm">El sistema funciona correctamente</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data.alerts.items.map((alert) => (
                  <div
                    key={alert.id}
                    className={cn(
                      'p-3 rounded-lg border',
                      alertLevelColors[alert.level]
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium">{alert.service}</p>
                        <p className="text-sm">{alert.message}</p>
                        <p className="text-xs mt-1 opacity-75">
                          {new Date(alert.timestamp).toLocaleString()}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => resolveAlert(alert.id)}
                        className="text-xs"
                      >
                        Resolver
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

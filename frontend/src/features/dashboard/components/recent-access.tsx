'use client'

import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { cn } from '@/shared/utils/cn'
import { CheckCircle, XCircle, Clock, Car, User } from 'lucide-react'
import type { AccessLog } from '@/shared/types/database'

interface RecentAccessProps {
  logs: AccessLog[]
  isLoading: boolean
}

export function RecentAccess({ logs, isLoading }: RecentAccessProps) {
  const getStatusIcon = (decision: string) => {
    switch (decision) {
      case 'granted':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'denied':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />
    }
  }

  const getStatusColor = (decision: string) => {
    switch (decision) {
      case 'granted':
        return 'bg-green-50 text-green-700'
      case 'denied':
        return 'bg-red-50 text-red-700'
      default:
        return 'bg-yellow-50 text-yellow-700'
    }
  }

  const getStatusText = (decision: string) => {
    switch (decision) {
      case 'granted':
        return 'Autorizado'
      case 'denied':
        return 'Denegado'
      default:
        return 'Pendiente'
    }
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Accesos Recientes</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 animate-pulse">
                <div className="w-10 h-10 bg-gray-200 rounded-full" />
                <div className="flex-1">
                  <div className="h-4 w-32 bg-gray-200 rounded mb-2" />
                  <div className="h-3 w-24 bg-gray-200 rounded" />
                </div>
                <div className="h-6 w-20 bg-gray-200 rounded" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Accesos Recientes</CardTitle>
      </CardHeader>
      <CardContent>
        {logs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No hay accesos registrados</p>
        ) : (
          <div className="space-y-4">
            {logs.map((log) => (
              <div
                key={log.id}
                className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                  {log.entry_type === 'vehicle' ? (
                    <Car className="w-5 h-5 text-gray-600" />
                  ) : (
                    <User className="w-5 h-5 text-gray-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {log.license_plate || log.visitor_name || 'Sin identificar'}
                  </p>
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <span>{log.apartment || 'N/A'}</span>
                    <span>-</span>
                    <span>
                      {format(new Date(log.created_at), "HH:mm 'hrs'", { locale: es })}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusIcon(log.access_decision)}
                  <span className={cn('text-xs font-medium px-2 py-1 rounded-full', getStatusColor(log.access_decision))}>
                    {getStatusText(log.access_decision)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

'use client'

import { RefreshCw } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { StatsCards } from '@/features/dashboard/components/stats-cards'
import { RecentAccess } from '@/features/dashboard/components/recent-access'
import { useDashboard } from '@/features/dashboard/hooks/use-dashboard'
import { useAuthStore } from '@/features/auth/store/auth-store'

export default function DashboardPage() {
  const { condominium } = useAuthStore()
  const { stats, recentLogs, isLoading, error, refresh } = useDashboard()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">
            Bienvenido al panel de control de {condominium?.name || 'SITNOVA'}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={refresh}
          disabled={isLoading}
          className="gap-2"
        >
          <RefreshCw className={isLoading ? 'animate-spin' : ''} size={16} />
          Actualizar
        </Button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Stats */}
      <StatsCards stats={stats} isLoading={isLoading} />

      {/* Recent Access */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentAccess logs={recentLogs} isLoading={isLoading} />

        {/* Quick Actions */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Acciones Rapidas</h3>
          <div className="grid grid-cols-2 gap-3">
            <Button variant="outline" className="justify-start" asChild href="/dashboard/residents/new">
              + Nuevo Residente
            </Button>
            <Button variant="outline" className="justify-start" asChild href="/dashboard/vehicles/new">
              + Nuevo Vehiculo
            </Button>
            <Button variant="outline" className="justify-start" asChild href="/dashboard/pre-authorized/new">
              + Pre-autorizar Visita
            </Button>
            <Button variant="outline" className="justify-start" asChild href="/dashboard/access-logs">
              Ver Historial
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

'use client'

import { Card, CardContent } from '@/shared/components/ui/card'
import { cn } from '@/shared/utils/cn'
import { Car, CheckCircle, XCircle, Clock, Users, Shield } from 'lucide-react'
import type { AccessStats } from '@/shared/types/database'

interface StatsCardsProps {
  stats: AccessStats | null
  isLoading: boolean
}

export function StatsCards({ stats, isLoading }: StatsCardsProps) {
  const cards = [
    {
      title: 'Accesos Hoy',
      value: stats?.total_today || 0,
      icon: Car,
      color: 'bg-blue-500',
      textColor: 'text-blue-600',
      bgLight: 'bg-blue-50',
    },
    {
      title: 'Autorizados',
      value: stats?.granted_today || 0,
      icon: CheckCircle,
      color: 'bg-green-500',
      textColor: 'text-green-600',
      bgLight: 'bg-green-50',
    },
    {
      title: 'Denegados',
      value: stats?.denied_today || 0,
      icon: XCircle,
      color: 'bg-red-500',
      textColor: 'text-red-600',
      bgLight: 'bg-red-50',
    },
    {
      title: 'Pendientes',
      value: stats?.pending_today || 0,
      icon: Clock,
      color: 'bg-yellow-500',
      textColor: 'text-yellow-600',
      bgLight: 'bg-yellow-50',
    },
    {
      title: 'Vehiculos',
      value: stats?.vehicles_authorized || 0,
      icon: Users,
      color: 'bg-purple-500',
      textColor: 'text-purple-600',
      bgLight: 'bg-purple-50',
    },
    {
      title: 'Pre-autorizados',
      value: stats?.pre_authorized_active || 0,
      icon: Shield,
      color: 'bg-indigo-500',
      textColor: 'text-indigo-600',
      bgLight: 'bg-indigo-50',
    },
  ]

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-4">
              <div className="h-10 w-10 bg-gray-200 rounded-lg mb-3" />
              <div className="h-8 w-16 bg-gray-200 rounded mb-1" />
              <div className="h-4 w-24 bg-gray-200 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardContent className="p-4">
            <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center mb-3', card.bgLight)}>
              <card.icon className={cn('w-5 h-5', card.textColor)} />
            </div>
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            <p className="text-sm text-gray-500">{card.title}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

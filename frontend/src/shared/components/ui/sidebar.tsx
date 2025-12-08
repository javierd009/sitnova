'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/shared/utils/cn'
import { useAuthStore } from '@/features/auth/store/auth-store'
import {
  Home,
  Users,
  Car,
  ClipboardList,
  Settings,
  LogOut,
  Shield,
  Activity,
  BookOpen,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Residentes', href: '/dashboard/residents', icon: Users },
  { name: 'Vehiculos', href: '/dashboard/vehicles', icon: Car },
  { name: 'Accesos', href: '/dashboard/access-logs', icon: ClipboardList },
  { name: 'Bitacora', href: '/dashboard/bitacora', icon: BookOpen },
  { name: 'Pre-autorizados', href: '/dashboard/pre-authorized', icon: Shield },
  { name: 'Monitoreo', href: '/dashboard/monitoring', icon: Activity },
  { name: 'Configuracion', href: '/dashboard/settings', icon: Settings },
]

interface SidebarProps {
  onLogout: () => void
}

export function Sidebar({ onLogout }: SidebarProps) {
  const pathname = usePathname()
  const { condominium, user } = useAuthStore()

  return (
    <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg text-gray-900">SITNOVA</span>
        </div>
      </div>

      {/* Condominium Info */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <p className="text-xs text-gray-500 uppercase tracking-wider">Condominio</p>
        <p className="font-medium text-gray-900 truncate">
          {condominium?.name || 'Sin asignar'}
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              )}
            >
              <item.icon className={cn('w-5 h-5', isActive ? 'text-primary-600' : 'text-gray-400')} />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {/* User Info & Logout */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 bg-gray-200 rounded-full flex items-center justify-center">
            <span className="text-sm font-medium text-gray-600">
              {user?.full_name?.charAt(0).toUpperCase() || 'U'}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {user?.full_name || 'Usuario'}
            </p>
            <p className="text-xs text-gray-500 truncate">
              {user?.role || 'Sin rol'}
            </p>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Cerrar sesion
        </button>
      </div>
    </aside>
  )
}

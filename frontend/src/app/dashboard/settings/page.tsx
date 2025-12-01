'use client'

import { useState } from 'react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/shared/components/ui/card'
import { Save, Building, Bell, Shield, Clock } from 'lucide-react'
import { useAuthStore } from '@/features/auth/store/auth-store'

export default function SettingsPage() {
  const { condominium, user } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  const [settings, setSettings] = useState({
    name: condominium?.name || '',
    address: condominium?.address || '',
    timezone: condominium?.timezone || 'America/Costa_Rica',
    auto_open_authorized: true,
    require_cedula: false,
    notify_on_access: true,
    notify_on_denied: true,
    call_timeout: 30,
    max_retries: 3,
  })

  const handleSave = async () => {
    setIsLoading(true)
    setSaved(false)

    // Simulate save
    await new Promise(resolve => setTimeout(resolve, 1000))

    setIsLoading(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configuracion</h1>
        <p className="text-gray-500">Configuracion del sistema y del condominio</p>
      </div>

      {saved && (
        <div className="p-4 bg-green-50 text-green-700 rounded-lg">
          Configuracion guardada exitosamente
        </div>
      )}

      {/* Condominium Info */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Building className="w-5 h-5 text-gray-400" />
            <div>
              <CardTitle>Informacion del Condominio</CardTitle>
              <CardDescription>Datos generales del condominio</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Nombre"
              value={settings.name}
              onChange={(e) => setSettings({ ...settings, name: e.target.value })}
              disabled={!isAdmin}
            />
            <Input
              label="Direccion"
              value={settings.address}
              onChange={(e) => setSettings({ ...settings, address: e.target.value })}
              disabled={!isAdmin}
            />
          </div>
        </CardContent>
      </Card>

      {/* Access Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-gray-400" />
            <div>
              <CardTitle>Control de Acceso</CardTitle>
              <CardDescription>Configuracion del sistema de acceso</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Apertura automatica</p>
              <p className="text-sm text-gray-500">Abrir automaticamente para vehiculos autorizados</p>
            </div>
            <input
              type="checkbox"
              checked={settings.auto_open_authorized}
              onChange={(e) => setSettings({ ...settings, auto_open_authorized: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded"
              disabled={!isAdmin}
            />
          </label>

          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Requerir cedula</p>
              <p className="text-sm text-gray-500">Solicitar cedula a todos los visitantes</p>
            </div>
            <input
              type="checkbox"
              checked={settings.require_cedula}
              onChange={(e) => setSettings({ ...settings, require_cedula: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded"
              disabled={!isAdmin}
            />
          </label>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-gray-400" />
            <div>
              <CardTitle>Notificaciones</CardTitle>
              <CardDescription>Configuracion de alertas y notificaciones</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Notificar accesos</p>
              <p className="text-sm text-gray-500">Enviar notificacion cuando alguien accede</p>
            </div>
            <input
              type="checkbox"
              checked={settings.notify_on_access}
              onChange={(e) => setSettings({ ...settings, notify_on_access: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded"
              disabled={!isAdmin}
            />
          </label>

          <label className="flex items-center justify-between">
            <div>
              <p className="font-medium">Notificar denegaciones</p>
              <p className="text-sm text-gray-500">Enviar alerta cuando se deniega un acceso</p>
            </div>
            <input
              type="checkbox"
              checked={settings.notify_on_denied}
              onChange={(e) => setSettings({ ...settings, notify_on_denied: e.target.checked })}
              className="w-5 h-5 text-primary-600 rounded"
              disabled={!isAdmin}
            />
          </label>
        </CardContent>
      </Card>

      {/* Timeout Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-gray-400" />
            <div>
              <CardTitle>Tiempos de Espera</CardTitle>
              <CardDescription>Configuracion de timeouts del sistema</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Timeout de llamada (segundos)"
              type="number"
              value={settings.call_timeout}
              onChange={(e) => setSettings({ ...settings, call_timeout: parseInt(e.target.value) })}
              min={10}
              max={120}
              disabled={!isAdmin}
            />
            <Input
              label="Reintentos maximos"
              type="number"
              value={settings.max_retries}
              onChange={(e) => setSettings({ ...settings, max_retries: parseInt(e.target.value) })}
              min={1}
              max={5}
              disabled={!isAdmin}
            />
          </div>
        </CardContent>
      </Card>

      {isAdmin && (
        <div className="flex justify-end">
          <Button onClick={handleSave} isLoading={isLoading}>
            <Save className="w-4 h-4 mr-2" />
            Guardar Configuracion
          </Button>
        </div>
      )}

      {!isAdmin && (
        <div className="p-4 bg-yellow-50 text-yellow-700 rounded-lg">
          Solo los administradores pueden modificar la configuracion
        </div>
      )}
    </div>
  )
}

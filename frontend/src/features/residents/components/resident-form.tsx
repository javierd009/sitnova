'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Select } from '@/shared/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { ArrowLeft, Save } from 'lucide-react'
import type { Resident } from '@/shared/types/database'

interface ResidentFormProps {
  resident?: Resident
  onSubmit: (data: ResidentFormData) => Promise<void>
  isLoading?: boolean
}

export interface ResidentFormData {
  full_name: string
  apartment: string
  phone: string
  phone_secondary?: string
  email?: string
  address?: string
  address_instructions?: string
  notification_preference: 'whatsapp' | 'call' | 'both'
}

const notificationOptions = [
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'call', label: 'Llamada' },
  { value: 'both', label: 'Ambos' },
]

export function ResidentForm({ resident, onSubmit, isLoading }: ResidentFormProps) {
  const router = useRouter()
  const [error, setError] = useState('')
  const [formData, setFormData] = useState<ResidentFormData>({
    full_name: resident?.full_name || '',
    apartment: resident?.apartment || '',
    phone: resident?.phone || '',
    phone_secondary: resident?.phone_secondary || '',
    email: resident?.email || '',
    address: resident?.address || '',
    address_instructions: resident?.address_instructions || '',
    notification_preference: resident?.notification_preference || 'whatsapp',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.full_name.trim()) {
      setError('El nombre es requerido')
      return
    }
    if (!formData.apartment.trim()) {
      setError('La casa/apartamento es requerido')
      return
    }
    if (!formData.phone.trim()) {
      setError('El telefono es requerido')
      return
    }

    try {
      await onSubmit(formData)
      router.push('/dashboard/residents')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    }
  }

  const handleChange = (field: keyof ResidentFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver
        </Button>
        <h1 className="text-2xl font-bold text-gray-900">
          {resident ? 'Editar Residente' : 'Nuevo Residente'}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informacion del Residente</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Nombre Completo *"
                value={formData.full_name}
                onChange={(e) => handleChange('full_name', e.target.value)}
                placeholder="Juan Perez"
                required
              />

              <Input
                label="Casa/Apartamento *"
                value={formData.apartment}
                onChange={(e) => handleChange('apartment', e.target.value)}
                placeholder="101"
                required
              />

              <Input
                label="Telefono Principal *"
                type="tel"
                value={formData.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="+506 8888-8888"
                required
              />

              <Input
                label="Telefono Secundario"
                type="tel"
                value={formData.phone_secondary}
                onChange={(e) => handleChange('phone_secondary', e.target.value)}
                placeholder="+506 8888-8888"
              />

              <Input
                label="Email"
                type="email"
                value={formData.email}
                onChange={(e) => handleChange('email', e.target.value)}
                placeholder="juan@email.com"
              />

              <Select
                label="Preferencia de Notificacion"
                value={formData.notification_preference}
                onChange={(e) => handleChange('notification_preference', e.target.value as ResidentFormData['notification_preference'])}
                options={notificationOptions}
              />
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-medium text-gray-700">Ubicacion de la Casa</h3>
              <p className="text-xs text-gray-500">
                Estas indicaciones se le daran al visitante cuando pregunte como llegar a su casa.
              </p>

              <Input
                label="Direccion"
                value={formData.address}
                onChange={(e) => handleChange('address', e.target.value)}
                placeholder="Ej: Condominio Las Palmas, Bloque 3"
              />

              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700">
                  Instrucciones para llegar
                </label>
                <textarea
                  value={formData.address_instructions}
                  onChange={(e) => handleChange('address_instructions', e.target.value)}
                  placeholder="Ej: Segunda casa a la derecha despues de la piscina, porton verde"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
                <p className="text-xs text-gray-400">
                  El portero virtual leera estas indicaciones al visitante autorizado.
                </p>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
              >
                Cancelar
              </Button>
              <Button type="submit" isLoading={isLoading}>
                <Save className="w-4 h-4 mr-2" />
                {resident ? 'Guardar Cambios' : 'Crear Residente'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

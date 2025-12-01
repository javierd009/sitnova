'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Select } from '@/shared/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { ArrowLeft, Save, Search } from 'lucide-react'
import { residentService } from '@/features/residents/services/resident-service'
import { useAuthStore } from '@/features/auth/store/auth-store'
import type { Vehicle, Resident } from '@/shared/types/database'

interface VehicleFormProps {
  vehicle?: Vehicle
  onSubmit: (data: VehicleFormData) => Promise<void>
  isLoading?: boolean
}

export interface VehicleFormData {
  resident_id: string
  license_plate: string
  vehicle_type: 'auto' | 'moto' | 'camion' | 'otro'
  brand?: string
  model?: string
  color?: string
  notes?: string
}

const vehicleTypeOptions = [
  { value: 'auto', label: 'Automovil' },
  { value: 'moto', label: 'Motocicleta' },
  { value: 'camion', label: 'Camion' },
  { value: 'otro', label: 'Otro' },
]

export function VehicleForm({ vehicle, onSubmit, isLoading }: VehicleFormProps) {
  const router = useRouter()
  const { condominium } = useAuthStore()
  const [error, setError] = useState('')
  const [residents, setResidents] = useState<Resident[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showResidentSearch, setShowResidentSearch] = useState(false)
  const [selectedResident, setSelectedResident] = useState<Resident | null>(null)

  const [formData, setFormData] = useState<VehicleFormData>({
    resident_id: vehicle?.resident_id || '',
    license_plate: vehicle?.license_plate || '',
    vehicle_type: vehicle?.vehicle_type || 'auto',
    brand: vehicle?.brand || '',
    model: vehicle?.model || '',
    color: vehicle?.color || '',
    notes: vehicle?.notes || '',
  })

  useEffect(() => {
    const searchResidents = async () => {
      if (!condominium?.id || searchQuery.length < 2) {
        setResidents([])
        return
      }

      try {
        const results = await residentService.search(condominium.id, searchQuery)
        setResidents(results)
      } catch (err) {
        console.error('Error searching residents:', err)
      }
    }

    const debounce = setTimeout(searchResidents, 300)
    return () => clearTimeout(debounce)
  }, [searchQuery, condominium?.id])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.resident_id) {
      setError('Debe seleccionar un residente')
      return
    }
    if (!formData.license_plate.trim()) {
      setError('La placa es requerida')
      return
    }

    try {
      await onSubmit(formData)
      router.push('/dashboard/vehicles')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    }
  }

  const handleChange = (field: keyof VehicleFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const selectResident = (resident: Resident) => {
    setSelectedResident(resident)
    setFormData(prev => ({ ...prev, resident_id: resident.id }))
    setShowResidentSearch(false)
    setSearchQuery('')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Volver
        </Button>
        <h1 className="text-2xl font-bold text-gray-900">
          {vehicle ? 'Editar Vehiculo' : 'Nuevo Vehiculo'}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informacion del Vehiculo</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">
                {error}
              </div>
            )}

            {/* Resident Selection */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Residente *
              </label>
              {selectedResident ? (
                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">{selectedResident.full_name}</p>
                    <p className="text-sm text-gray-500">Casa {selectedResident.apartment}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedResident(null)
                      setFormData(prev => ({ ...prev, resident_id: '' }))
                      setShowResidentSearch(true)
                    }}
                  >
                    Cambiar
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="Buscar residente por nombre o casa..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value)
                      setShowResidentSearch(true)
                    }}
                    onFocus={() => setShowResidentSearch(true)}
                    className="pl-10"
                  />
                  {showResidentSearch && residents.length > 0 && (
                    <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto">
                      {residents.map((resident) => (
                        <button
                          key={resident.id}
                          type="button"
                          onClick={() => selectResident(resident)}
                          className="w-full px-4 py-2 text-left hover:bg-gray-50"
                        >
                          <p className="font-medium">{resident.full_name}</p>
                          <p className="text-sm text-gray-500">Casa {resident.apartment}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input
                label="Placa *"
                value={formData.license_plate}
                onChange={(e) => handleChange('license_plate', e.target.value.toUpperCase())}
                placeholder="ABC-123"
                required
              />

              <Select
                label="Tipo de Vehiculo"
                value={formData.vehicle_type}
                onChange={(e) => handleChange('vehicle_type', e.target.value)}
                options={vehicleTypeOptions}
              />

              <Input
                label="Marca"
                value={formData.brand}
                onChange={(e) => handleChange('brand', e.target.value)}
                placeholder="Toyota"
              />

              <Input
                label="Modelo"
                value={formData.model}
                onChange={(e) => handleChange('model', e.target.value)}
                placeholder="Corolla"
              />

              <Input
                label="Color"
                value={formData.color}
                onChange={(e) => handleChange('color', e.target.value)}
                placeholder="Blanco"
              />

              <Input
                label="Notas"
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                placeholder="Notas adicionales..."
              />
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
                {vehicle ? 'Guardar Cambios' : 'Crear Vehiculo'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

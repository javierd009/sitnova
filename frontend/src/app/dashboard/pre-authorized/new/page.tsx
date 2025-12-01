'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { ArrowLeft, Save, Search } from 'lucide-react'
import { preAuthService } from '@/features/pre-authorized/services/pre-auth-service'
import { residentService } from '@/features/residents/services/resident-service'
import { useAuthStore } from '@/features/auth/store/auth-store'
import type { Resident } from '@/shared/types/database'

export default function NewPreAuthPage() {
  const router = useRouter()
  const { condominium } = useAuthStore()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const [residents, setResidents] = useState<Resident[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showResidentSearch, setShowResidentSearch] = useState(false)
  const [selectedResident, setSelectedResident] = useState<Resident | null>(null)

  const [formData, setFormData] = useState({
    visitor_name: '',
    cedula: '',
    license_plate: '',
    valid_from: new Date().toISOString().slice(0, 16),
    valid_until: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 16),
    single_use: true,
    notes: '',
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

    if (!selectedResident) {
      setError('Debe seleccionar un residente')
      return
    }
    if (!formData.visitor_name.trim()) {
      setError('El nombre del visitante es requerido')
      return
    }

    setIsLoading(true)
    try {
      await preAuthService.create({
        condominium_id: condominium!.id,
        resident_id: selectedResident.id,
        visitor_name: formData.visitor_name,
        cedula: formData.cedula || undefined,
        license_plate: formData.license_plate || undefined,
        valid_from: new Date(formData.valid_from).toISOString(),
        valid_until: new Date(formData.valid_until).toISOString(),
        single_use: formData.single_use,
        notes: formData.notes || undefined,
      })
      router.push('/dashboard/pre-authorized')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear pre-autorizacion')
    } finally {
      setIsLoading(false)
    }
  }

  const selectResident = (resident: Resident) => {
    setSelectedResident(resident)
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
        <h1 className="text-2xl font-bold text-gray-900">Nueva Pre-autorizacion</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Informacion del Visitante</CardTitle>
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
                Residente que Autoriza *
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
                    onClick={() => setSelectedResident(null)}
                  >
                    Cambiar
                  </Button>
                </div>
              ) : (
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="Buscar residente..."
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
                label="Nombre del Visitante *"
                value={formData.visitor_name}
                onChange={(e) => setFormData({ ...formData, visitor_name: e.target.value })}
                placeholder="Juan Perez"
                required
              />

              <Input
                label="Cedula (opcional)"
                value={formData.cedula}
                onChange={(e) => setFormData({ ...formData, cedula: e.target.value })}
                placeholder="1-2345-6789"
              />

              <Input
                label="Placa del Vehiculo (opcional)"
                value={formData.license_plate}
                onChange={(e) => setFormData({ ...formData, license_plate: e.target.value.toUpperCase() })}
                placeholder="ABC-123"
              />

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Autorizacion
                </label>
                <div className="flex gap-4 mt-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      checked={formData.single_use}
                      onChange={() => setFormData({ ...formData, single_use: true })}
                      className="text-primary-600"
                    />
                    <span className="text-sm">Una sola vez</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="radio"
                      checked={!formData.single_use}
                      onChange={() => setFormData({ ...formData, single_use: false })}
                      className="text-primary-600"
                    />
                    <span className="text-sm">Multiples visitas</span>
                  </label>
                </div>
              </div>

              <Input
                label="Valido Desde *"
                type="datetime-local"
                value={formData.valid_from}
                onChange={(e) => setFormData({ ...formData, valid_from: e.target.value })}
                required
              />

              <Input
                label="Valido Hasta *"
                type="datetime-local"
                value={formData.valid_until}
                onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                required
              />
            </div>

            <Input
              label="Notas (opcional)"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Informacion adicional..."
            />

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => router.back()}>
                Cancelar
              </Button>
              <Button type="submit" isLoading={isLoading}>
                <Save className="w-4 h-4 mr-2" />
                Crear Pre-autorizacion
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

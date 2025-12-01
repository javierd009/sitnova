'use client'

import { useState } from 'react'
import { Plus, Search, Edit, Trash2, Car, Home, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table'
import { useVehicles } from '@/features/vehicles/hooks/use-vehicles'
import { cn } from '@/shared/utils/cn'

const vehicleTypeLabels: Record<string, string> = {
  auto: 'Auto',
  moto: 'Moto',
  camion: 'Camion',
  otro: 'Otro',
}

export default function VehiclesPage() {
  const { vehicles, isLoading, error, deleteVehicle, toggleAuthorized } = useVehicles()
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filteredVehicles = vehicles.filter(vehicle =>
    vehicle.license_plate.toLowerCase().includes(searchQuery.toLowerCase()) ||
    vehicle.resident?.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    vehicle.resident?.apartment.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDelete = async (id: string) => {
    if (!confirm('Esta seguro de eliminar este vehiculo?')) return

    setDeletingId(id)
    try {
      await deleteVehicle(id)
    } catch (err) {
      alert('Error al eliminar vehiculo')
    } finally {
      setDeletingId(null)
    }
  }

  const handleToggleAuth = async (id: string, currentStatus: boolean) => {
    try {
      await toggleAuthorized(id, !currentStatus)
    } catch (err) {
      alert('Error al cambiar autorizacion')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Vehiculos</h1>
          <p className="text-gray-500">Gestiona los vehiculos autorizados</p>
        </div>
        <Button asChild href="/dashboard/vehicles/new" className="gap-2">
          <Plus size={16} />
          Nuevo Vehiculo
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Buscar por placa, residente o casa..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Vehiculos ({filteredVehicles.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : filteredVehicles.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {searchQuery ? 'No se encontraron resultados' : 'No hay vehiculos registrados'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Placa</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Marca/Modelo</TableHead>
                  <TableHead>Residente</TableHead>
                  <TableHead>Casa</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredVehicles.map((vehicle) => (
                  <TableRow key={vehicle.id}>
                    <TableCell>
                      <span className="inline-flex items-center gap-2 font-mono font-bold text-gray-900">
                        <Car className="w-4 h-4 text-gray-400" />
                        {vehicle.license_plate}
                      </span>
                    </TableCell>
                    <TableCell>{vehicleTypeLabels[vehicle.vehicle_type] || vehicle.vehicle_type}</TableCell>
                    <TableCell>
                      {vehicle.brand || vehicle.model ? (
                        `${vehicle.brand || ''} ${vehicle.model || ''}`.trim()
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>{vehicle.resident?.full_name || '-'}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1">
                        <Home className="w-4 h-4 text-gray-400" />
                        {vehicle.resident?.apartment || '-'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleToggleAuth(vehicle.id, vehicle.is_authorized)}
                        className={cn(
                          'inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full cursor-pointer transition-colors',
                          vehicle.is_authorized
                            ? 'bg-green-50 text-green-700 hover:bg-green-100'
                            : 'bg-red-50 text-red-700 hover:bg-red-100'
                        )}
                      >
                        {vehicle.is_authorized ? (
                          <>
                            <CheckCircle className="w-3 h-3" />
                            Autorizado
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3 h-3" />
                            No Autorizado
                          </>
                        )}
                      </button>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" asChild href={`/dashboard/vehicles/${vehicle.id}`}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(vehicle.id)}
                          disabled={deletingId === vehicle.id}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

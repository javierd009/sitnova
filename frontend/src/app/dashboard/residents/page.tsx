'use client'

import { useState } from 'react'
import { Plus, Search, Edit, Trash2, Phone, Mail, Home } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table'
import { useResidents } from '@/features/residents/hooks/use-residents'
import { cn } from '@/shared/utils/cn'

export default function ResidentsPage() {
  const { residents, isLoading, error, deleteResident } = useResidents()
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const filteredResidents = residents.filter(resident =>
    resident.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    resident.apartment.toLowerCase().includes(searchQuery.toLowerCase()) ||
    resident.phone.includes(searchQuery)
  )

  const handleDelete = async (id: string) => {
    if (!confirm('Esta seguro de eliminar este residente?')) return

    setDeletingId(id)
    try {
      await deleteResident(id)
    } catch (err) {
      alert('Error al eliminar residente')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Residentes</h1>
          <p className="text-gray-500">Gestiona los residentes del condominio</p>
        </div>
        <Button asChild href="/dashboard/residents/new" className="gap-2">
          <Plus size={16} />
          Nuevo Residente
        </Button>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Buscar por nombre, casa o telefono..."
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
          <CardTitle>Lista de Residentes ({filteredResidents.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : filteredResidents.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              {searchQuery ? 'No se encontraron resultados' : 'No hay residentes registrados'}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Casa/Apto</TableHead>
                  <TableHead>Telefono</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResidents.map((resident) => (
                  <TableRow key={resident.id}>
                    <TableCell className="font-medium">{resident.full_name}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1">
                        <Home className="w-4 h-4 text-gray-400" />
                        {resident.apartment}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1">
                        <Phone className="w-4 h-4 text-gray-400" />
                        {resident.phone}
                      </span>
                    </TableCell>
                    <TableCell>
                      {resident.email ? (
                        <span className="inline-flex items-center gap-1">
                          <Mail className="w-4 h-4 text-gray-400" />
                          {resident.email}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          'px-2 py-1 text-xs font-medium rounded-full',
                          resident.is_active
                            ? 'bg-green-50 text-green-700'
                            : 'bg-gray-100 text-gray-600'
                        )}
                      >
                        {resident.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" asChild href={`/dashboard/residents/${resident.id}`}>
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(resident.id)}
                          disabled={deletingId === resident.id}
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

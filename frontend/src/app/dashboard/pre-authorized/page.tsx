'use client'

import { useState } from 'react'
import { format, isPast, isFuture } from 'date-fns'
import { es } from 'date-fns/locale'
import { Plus, Trash2, Search, CheckCircle, Clock, XCircle, Home, User } from 'lucide-react'
import { Button } from '@/shared/components/ui/button'
import { Input } from '@/shared/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/components/ui/table'
import { usePreAuth } from '@/features/pre-authorized/hooks/use-pre-auth'
import { cn } from '@/shared/utils/cn'

export default function PreAuthorizedPage() {
  const { preAuths, isLoading, error, deletePreAuth } = usePreAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'expired' | 'used'>('all')

  const filteredPreAuths = preAuths.filter(preAuth => {
    const matchesSearch =
      preAuth.visitor_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      preAuth.resident?.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      preAuth.license_plate?.toLowerCase().includes(searchQuery.toLowerCase())

    if (!matchesSearch) return false

    const now = new Date()
    const validUntil = new Date(preAuth.valid_until)
    const validFrom = new Date(preAuth.valid_from)

    switch (filter) {
      case 'active':
        return !preAuth.used && validFrom <= now && validUntil >= now
      case 'expired':
        return isPast(validUntil)
      case 'used':
        return preAuth.used
      default:
        return true
    }
  })

  const handleDelete = async (id: string) => {
    if (!confirm('Esta seguro de eliminar esta pre-autorizacion?')) return

    setDeletingId(id)
    try {
      await deletePreAuth(id)
    } catch (err) {
      alert('Error al eliminar')
    } finally {
      setDeletingId(null)
    }
  }

  const getStatus = (preAuth: typeof preAuths[0]) => {
    const now = new Date()
    const validUntil = new Date(preAuth.valid_until)
    const validFrom = new Date(preAuth.valid_from)

    if (preAuth.used) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-700">
          <CheckCircle className="w-3 h-3" />
          Usado
        </span>
      )
    }

    if (isPast(validUntil)) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-red-50 text-red-700">
          <XCircle className="w-3 h-3" />
          Expirado
        </span>
      )
    }

    if (isFuture(validFrom)) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-yellow-50 text-yellow-700">
          <Clock className="w-3 h-3" />
          Programado
        </span>
      )
    }

    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded-full bg-green-50 text-green-700">
        <CheckCircle className="w-3 h-3" />
        Activo
      </span>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pre-autorizaciones</h1>
          <p className="text-gray-500">Visitantes pre-autorizados por residentes</p>
        </div>
        <Button asChild href="/dashboard/pre-authorized/new">
          <Plus size={16} className="mr-2" />
          Nueva Pre-autorizacion
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar por visitante, residente o placa..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              {(['all', 'active', 'expired', 'used'] as const).map((f) => (
                <Button
                  key={f}
                  variant={filter === f ? 'primary' : 'outline'}
                  size="sm"
                  onClick={() => setFilter(f)}
                >
                  {f === 'all' ? 'Todos' : f === 'active' ? 'Activos' : f === 'expired' ? 'Expirados' : 'Usados'}
                </Button>
              ))}
            </div>
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
          <CardTitle>Lista de Pre-autorizaciones ({filteredPreAuths.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Cargando...</div>
          ) : filteredPreAuths.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              No hay pre-autorizaciones
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Visitante</TableHead>
                  <TableHead>Residente</TableHead>
                  <TableHead>Placa</TableHead>
                  <TableHead>Valido</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPreAuths.map((preAuth) => (
                  <TableRow key={preAuth.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="font-medium">{preAuth.visitor_name}</p>
                          {preAuth.cedula && (
                            <p className="text-xs text-gray-500">CI: {preAuth.cedula}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Home className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="font-medium">{preAuth.resident?.full_name}</p>
                          <p className="text-xs text-gray-500">Casa {preAuth.resident?.apartment}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono">
                        {preAuth.license_plate || '-'}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <p>{format(new Date(preAuth.valid_from), 'dd/MM/yy HH:mm', { locale: es })}</p>
                        <p className="text-gray-500">
                          hasta {format(new Date(preAuth.valid_until), 'dd/MM/yy HH:mm', { locale: es })}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={cn(
                        'px-2 py-1 text-xs font-medium rounded-full',
                        preAuth.single_use
                          ? 'bg-orange-50 text-orange-700'
                          : 'bg-blue-50 text-blue-700'
                      )}>
                        {preAuth.single_use ? 'Una vez' : 'Multiple'}
                      </span>
                    </TableCell>
                    <TableCell>{getStatus(preAuth)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(preAuth.id)}
                        disabled={deletingId === preAuth.id}
                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
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

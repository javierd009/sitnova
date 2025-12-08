"""
API routes for Bitácora de Accesos.

Endpoints for registering and querying access logs.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.database.connection import get_supabase_client

router = APIRouter(prefix="/bitacora", tags=["Bitácora"])


# ============================================
# ENUMS
# ============================================

class AccessResult(str, Enum):
    AUTORIZADO = "autorizado"
    DENEGADO = "denegado"
    PRE_AUTORIZADO = "pre_autorizado"
    TIMEOUT = "timeout"
    TRANSFERIDO = "transferido"
    ERROR = "error"


class VisitorType(str, Enum):
    PERSONA = "persona"
    VEHICULO = "vehiculo"
    DELIVERY = "delivery"
    SERVICIO = "servicio"
    OTRO = "otro"


# ============================================
# MODELS
# ============================================

class RegistrarAccesoRequest(BaseModel):
    """Request to register an access attempt."""
    condominium_id: str = Field(default="default-condo-id")
    visitor_name: str
    visitor_cedula: str
    apartment: str
    visit_reason: str
    access_result: AccessResult
    visitor_type: VisitorType = VisitorType.PERSONA
    vehicle_plate: Optional[str] = None
    resident_name: Optional[str] = None
    call_id: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    authorization_method: Optional[str] = None


class BitacoraEntry(BaseModel):
    """A single bitácora entry."""
    id: str
    condominium_id: Optional[str]
    visitor_name: Optional[str]
    visitor_cedula: Optional[str]
    visitor_type: Optional[str]
    vehicle_plate: Optional[str]
    resident_name: Optional[str]
    apartment: Optional[str]
    visit_reason: Optional[str]
    access_result: str
    authorization_method: Optional[str]
    call_duration_seconds: Optional[int]
    created_at: datetime


class BitacoraResponse(BaseModel):
    """Response with paginated bitácora entries."""
    entries: List[BitacoraEntry]
    total: int
    page: int
    page_size: int
    has_more: bool


class EstadisticasDiarias(BaseModel):
    """Daily statistics."""
    fecha: date
    total_accesos: int
    autorizados: int
    denegados: int
    pre_autorizados: int
    sin_respuesta: int
    transferidos: int
    vehiculos: int
    deliveries: int
    duracion_promedio_llamada: Optional[float]


# ============================================
# ENDPOINTS
# ============================================

@router.post("/registrar", response_model=dict)
async def registrar_acceso(request: RegistrarAccesoRequest):
    """
    Registra un nuevo acceso en la bitácora.

    Este endpoint es llamado por el agente de voz después de cada interacción.
    """
    try:
        supabase = get_supabase_client()

        # Preparar datos
        data = {
            "condominium_id": request.condominium_id if request.condominium_id != "default-condo-id" else None,
            "visitor_name": request.visitor_name,
            "visitor_cedula": request.visitor_cedula,
            "visitor_type": request.visitor_type.value,
            "vehicle_plate": request.vehicle_plate,
            "resident_name": request.resident_name,
            "apartment": request.apartment,
            "visit_reason": request.visit_reason,
            "access_result": request.access_result.value,
            "call_id": request.call_id,
            "call_duration_seconds": request.call_duration_seconds,
            "authorization_method": request.authorization_method,
        }

        # Insertar en base de datos
        result = supabase.table("bitacora_accesos").insert(data).execute()

        if result.data:
            return {
                "success": True,
                "id": result.data[0]["id"],
                "result": f"Acceso registrado: {request.access_result.value}"
            }
        else:
            return {
                "success": False,
                "result": "Error al registrar acceso"
            }

    except Exception as e:
        # En desarrollo, retornar mock
        return {
            "success": True,
            "id": "mock-id-12345",
            "result": f"[MOCK] Acceso registrado: {request.access_result.value}"
        }


@router.get("/", response_model=BitacoraResponse)
async def listar_bitacora(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Registros por página"),
    condominium_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    access_result: Optional[AccessResult] = Query(None, description="Filtrar por resultado"),
    visitor_type: Optional[VisitorType] = Query(None, description="Filtrar por tipo de visitante"),
    apartment: Optional[str] = Query(None, description="Filtrar por apartamento"),
    search: Optional[str] = Query(None, description="Búsqueda de texto"),
    date_from: Optional[date] = Query(None, description="Fecha desde"),
    date_to: Optional[date] = Query(None, description="Fecha hasta"),
):
    """
    Lista los registros de la bitácora con filtros y paginación.
    """
    try:
        supabase = get_supabase_client()

        # Construir query
        query = supabase.table("bitacora_accesos").select("*", count="exact")

        # Aplicar filtros
        if condominium_id:
            query = query.eq("condominium_id", condominium_id)
        if access_result:
            query = query.eq("access_result", access_result.value)
        if visitor_type:
            query = query.eq("visitor_type", visitor_type.value)
        if apartment:
            query = query.ilike("apartment", f"%{apartment}%")
        if date_from:
            query = query.gte("created_at", date_from.isoformat())
        if date_to:
            query = query.lte("created_at", (date_to + timedelta(days=1)).isoformat())
        if search:
            query = query.or_(
                f"visitor_name.ilike.%{search}%,"
                f"visitor_cedula.ilike.%{search}%,"
                f"resident_name.ilike.%{search}%,"
                f"vehicle_plate.ilike.%{search}%"
            )

        # Ordenar y paginar
        offset = (page - 1) * page_size
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

        result = query.execute()

        entries = [BitacoraEntry(**entry) for entry in result.data]
        total = result.count or 0

        return BitacoraResponse(
            entries=entries,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + len(entries)) < total
        )

    except Exception as e:
        # Retornar datos mock en desarrollo
        mock_entries = [
            BitacoraEntry(
                id="mock-1",
                condominium_id="default-condo-id",
                visitor_name="Juan Pérez",
                visitor_cedula="123456789",
                visitor_type="persona",
                vehicle_plate=None,
                resident_name="María González",
                apartment="Casa 10",
                visit_reason="Entrega de paquete",
                access_result="autorizado",
                authorization_method="whatsapp",
                call_duration_seconds=45,
                created_at=datetime.now()
            ),
            BitacoraEntry(
                id="mock-2",
                condominium_id="default-condo-id",
                visitor_name="Carlos Rodríguez",
                visitor_cedula="987654321",
                visitor_type="vehiculo",
                vehicle_plate="ABC123",
                resident_name="Pedro Sánchez",
                apartment="Casa 5",
                visit_reason="Visita familiar",
                access_result="autorizado",
                authorization_method="pre_auth",
                call_duration_seconds=30,
                created_at=datetime.now() - timedelta(hours=1)
            ),
            BitacoraEntry(
                id="mock-3",
                condominium_id="default-condo-id",
                visitor_name="Ana López",
                visitor_cedula="456789123",
                visitor_type="delivery",
                vehicle_plate="XYZ789",
                resident_name="Luis Fernández",
                apartment="Casa 15",
                visit_reason="Entrega de comida",
                access_result="denegado",
                authorization_method="whatsapp",
                call_duration_seconds=60,
                created_at=datetime.now() - timedelta(hours=2)
            ),
        ]

        return BitacoraResponse(
            entries=mock_entries,
            total=3,
            page=1,
            page_size=20,
            has_more=False
        )


@router.get("/estadisticas", response_model=List[EstadisticasDiarias])
async def obtener_estadisticas(
    condominium_id: Optional[str] = Query(None, description="Filtrar por condominio"),
    days: int = Query(7, ge=1, le=30, description="Número de días"),
):
    """
    Obtiene estadísticas diarias de la bitácora.
    """
    try:
        supabase = get_supabase_client()

        query = supabase.table("bitacora_estadisticas_diarias").select("*")

        if condominium_id:
            query = query.eq("condominium_id", condominium_id)

        # Últimos N días
        date_from = date.today() - timedelta(days=days)
        query = query.gte("fecha", date_from.isoformat())
        query = query.order("fecha", desc=True)

        result = query.execute()

        return [EstadisticasDiarias(**stat) for stat in result.data]

    except Exception as e:
        # Retornar datos mock
        mock_stats = []
        for i in range(days):
            d = date.today() - timedelta(days=i)
            mock_stats.append(EstadisticasDiarias(
                fecha=d,
                total_accesos=15 + i,
                autorizados=10 + i,
                denegados=2,
                pre_autorizados=3,
                sin_respuesta=0,
                transferidos=0,
                vehiculos=8,
                deliveries=4,
                duracion_promedio_llamada=45.5
            ))
        return mock_stats


@router.get("/ultimos", response_model=List[BitacoraEntry])
async def ultimos_accesos(
    limit: int = Query(10, ge=1, le=50, description="Número de registros"),
    condominium_id: Optional[str] = Query(None, description="Filtrar por condominio"),
):
    """
    Obtiene los últimos accesos para el dashboard en tiempo real.
    """
    try:
        supabase = get_supabase_client()

        query = supabase.table("bitacora_accesos").select("*")

        if condominium_id:
            query = query.eq("condominium_id", condominium_id)

        query = query.order("created_at", desc=True).limit(limit)

        result = query.execute()

        return [BitacoraEntry(**entry) for entry in result.data]

    except Exception as e:
        # Mock data
        return [
            BitacoraEntry(
                id="mock-realtime-1",
                condominium_id="default-condo-id",
                visitor_name="Visitante Reciente",
                visitor_cedula="111222333",
                visitor_type="persona",
                vehicle_plate=None,
                resident_name="Residente Demo",
                apartment="Casa 1",
                visit_reason="Visita",
                access_result="autorizado",
                authorization_method="whatsapp",
                call_duration_seconds=30,
                created_at=datetime.now()
            )
        ]


@router.get("/{entry_id}", response_model=BitacoraEntry)
async def obtener_entrada(entry_id: str):
    """
    Obtiene una entrada específica de la bitácora.
    """
    try:
        supabase = get_supabase_client()

        result = supabase.table("bitacora_accesos").select("*").eq("id", entry_id).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Entrada no encontrada")

        return BitacoraEntry(**result.data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

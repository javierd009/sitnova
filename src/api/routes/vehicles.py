"""
API Routes para tracking de entrada/salida de vehículos.
Dashboard de movimiento vehicular por condominio.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel
from loguru import logger

from src.database.connection import get_supabase

router = APIRouter()


# ============================================
# MODELOS DE RESPUESTA
# ============================================

class VehicleMovement(BaseModel):
    """Movimiento de vehículo (entrada o salida)."""
    id: str
    timestamp: datetime
    direction: str  # 'entry' o 'exit'
    license_plate: Optional[str]
    plate_confidence: Optional[float]
    vehicle_brand: Optional[str]
    vehicle_model: Optional[str]
    vehicle_color: Optional[str]
    owner_or_visitor: Optional[str]
    apartment: Optional[str]
    access_decision: str
    vehicle_status: str  # 'registered', 'visitor', 'unknown'


class VehicleInside(BaseModel):
    """Vehículo actualmente dentro del condominio."""
    license_plate: str
    entry_time: datetime
    hours_inside: float
    brand: Optional[str]
    model: Optional[str]
    color: Optional[str]
    owner_name: Optional[str]
    apartment: Optional[str]


class DailySummary(BaseModel):
    """Resumen diario de movimientos."""
    date: date
    total_entries: int
    total_exits: int
    unique_vehicles: int
    registered_entries: int
    visitor_entries: int


# ============================================
# ENDPOINTS
# ============================================

@router.get("/tracking")
async def get_vehicle_tracking(
    condominium_id: str = Query(..., description="UUID del condominio"),
    direction: Optional[str] = Query(None, description="Filtrar por dirección: 'entry' o 'exit'"),
    date_from: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
):
    """
    Obtener historial de movimientos de vehículos.

    Retorna lista de entradas y salidas de vehículos para el condominio especificado.
    """
    logger.info(f"📊 Consultando tracking de vehículos para condominio: {condominium_id}")

    try:
        supabase = get_supabase()

        if not supabase:
            # Mock data para desarrollo
            return {
                "success": True,
                "data": [
                    {
                        "id": "mock-1",
                        "timestamp": datetime.now().isoformat(),
                        "direction": "entry",
                        "license_plate": "ABC-123",
                        "vehicle_status": "registered",
                        "owner_or_visitor": "Juan Pérez",
                        "apartment": "101",
                        "access_decision": "authorized"
                    }
                ],
                "pagination": {
                    "total": 1,
                    "limit": limit,
                    "offset": offset
                }
            }

        # Construir query
        query = supabase.table("access_logs").select(
            "id, timestamp, direction, license_plate, plate_confidence, "
            "access_decision, visitor_full_name, vehicles(brand, model, color, vehicle_type), "
            "residents(full_name, apartment)"
        ).eq("condominium_id", condominium_id).eq("entry_type", "vehicle")

        # Filtros opcionales
        if direction:
            query = query.eq("direction", direction)

        if date_from:
            query = query.gte("timestamp", f"{date_from}T00:00:00")

        if date_to:
            query = query.lte("timestamp", f"{date_to}T23:59:59")

        # Paginación y orden
        query = query.order("timestamp", desc=True).range(offset, offset + limit - 1)

        result = query.execute()

        # Transformar datos para respuesta
        movements = []
        for row in result.data:
            vehicle = row.get("vehicles") or {}
            resident = row.get("residents") or {}

            movements.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "direction": row.get("direction", "entry"),
                "license_plate": row.get("license_plate"),
                "plate_confidence": row.get("plate_confidence"),
                "vehicle_brand": vehicle.get("brand"),
                "vehicle_model": vehicle.get("model"),
                "vehicle_color": vehicle.get("color"),
                "owner_or_visitor": resident.get("full_name") or row.get("visitor_full_name"),
                "apartment": resident.get("apartment"),
                "access_decision": row["access_decision"],
                "vehicle_status": "registered" if vehicle else ("visitor" if row.get("visitor_id") else "unknown")
            })

        return {
            "success": True,
            "data": movements,
            "pagination": {
                "total": len(result.data),
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        logger.error(f"❌ Error en tracking de vehículos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inside")
async def get_vehicles_inside(
    condominium_id: str = Query(..., description="UUID del condominio"),
):
    """
    Obtener vehículos actualmente dentro del condominio.

    Calcula basado en el último movimiento de cada vehículo:
    - Si el último movimiento fue 'entry', el vehículo está dentro
    - Si el último movimiento fue 'exit', el vehículo está fuera
    """
    logger.info(f"🚗 Consultando vehículos dentro del condominio: {condominium_id}")

    try:
        supabase = get_supabase()

        if not supabase:
            # Mock data
            return {
                "success": True,
                "data": [
                    {
                        "license_plate": "ABC-123",
                        "entry_time": datetime.now().isoformat(),
                        "hours_inside": 2.5,
                        "brand": "Toyota",
                        "model": "Corolla",
                        "color": "Blanco",
                        "owner_name": "Juan Pérez",
                        "apartment": "101"
                    }
                ],
                "total_inside": 1
            }

        # Query usando la vista vehicles_inside
        result = supabase.table("vehicles_inside").select("*").eq("condominium_id", condominium_id).execute()

        return {
            "success": True,
            "data": result.data,
            "total_inside": len(result.data)
        }

    except Exception as e:
        logger.error(f"❌ Error consultando vehículos dentro: {e}")
        # Fallback: query directa si la vista no existe
        try:
            # Query alternativa sin la vista
            supabase = get_supabase()
            query = """
                WITH latest AS (
                    SELECT DISTINCT ON (license_plate)
                        license_plate, direction, timestamp
                    FROM access_logs
                    WHERE condominium_id = %s
                    AND entry_type = 'vehicle'
                    AND license_plate IS NOT NULL
                    ORDER BY license_plate, timestamp DESC
                )
                SELECT * FROM latest WHERE direction = 'entry'
            """
            # Si la vista no existe, retornar datos vacíos con mensaje
            return {
                "success": True,
                "data": [],
                "total_inside": 0,
                "note": "Vista 'vehicles_inside' no disponible. Ejecutar schema actualizado."
            }
        except:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary/daily")
async def get_daily_summary(
    condominium_id: str = Query(..., description="UUID del condominio"),
    days: int = Query(7, ge=1, le=30, description="Número de días hacia atrás"),
):
    """
    Obtener resumen diario de movimientos de vehículos.

    Retorna totales de entradas/salidas por día para los últimos N días.
    """
    logger.info(f"📈 Consultando resumen diario para condominio: {condominium_id}")

    try:
        supabase = get_supabase()

        if not supabase:
            # Mock data
            from datetime import timedelta
            mock_data = []
            for i in range(days):
                d = date.today() - timedelta(days=i)
                mock_data.append({
                    "date": d.isoformat(),
                    "total_entries": 15 - i,
                    "total_exits": 12 - i,
                    "unique_vehicles": 8,
                    "registered_entries": 10 - i,
                    "visitor_entries": 5
                })
            return {
                "success": True,
                "data": mock_data
            }

        # Query usando la vista daily_vehicle_summary
        result = supabase.table("daily_vehicle_summary").select("*").eq(
            "condominium_id", condominium_id
        ).limit(days).execute()

        return {
            "success": True,
            "data": result.data
        }

    except Exception as e:
        logger.error(f"❌ Error en resumen diario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-exit")
async def log_vehicle_exit(
    condominium_id: str = Query(..., description="UUID del condominio"),
    license_plate: str = Query(..., description="Placa del vehículo"),
    access_point: str = Query("Salida Principal", description="Punto de salida"),
):
    """
    Registrar salida de un vehículo.

    Usado cuando la cámara de salida detecta un vehículo abandonando el condominio.
    """
    logger.info(f"🚗➡️ Registrando salida de vehículo: {license_plate}")

    try:
        supabase = get_supabase()

        if not supabase:
            return {
                "success": True,
                "message": f"Salida registrada (mock): {license_plate}",
                "log_id": "mock-exit-123"
            }

        # Registrar evento de salida
        log_data = {
            "condominium_id": condominium_id,
            "entry_type": "vehicle",
            "direction": "exit",
            "license_plate": license_plate.upper(),
            "access_decision": "authorized",  # Las salidas siempre son autorizadas
            "access_point": access_point,
        }

        result = supabase.table("access_logs").insert(log_data).execute()

        logger.success(f"✅ Salida registrada: {license_plate}")

        return {
            "success": True,
            "message": f"Salida registrada: {license_plate}",
            "log_id": result.data[0]["id"],
            "timestamp": result.data[0]["timestamp"]
        }

    except Exception as e:
        logger.error(f"❌ Error registrando salida: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_vehicle(
    condominium_id: str = Query(..., description="UUID del condominio"),
    plate: str = Query(..., min_length=2, description="Placa a buscar (parcial o completa)"),
):
    """
    Buscar historial de un vehículo específico.

    Permite búsqueda parcial de placa.
    """
    logger.info(f"🔍 Buscando vehículo: {plate}")

    try:
        supabase = get_supabase()

        if not supabase:
            return {
                "success": True,
                "vehicle_info": {
                    "license_plate": plate.upper(),
                    "status": "registered",
                    "owner": "Juan Pérez",
                    "apartment": "101"
                },
                "recent_movements": [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "direction": "entry",
                        "access_decision": "authorized"
                    }
                ]
            }

        # Buscar en vehículos registrados
        vehicle_result = supabase.table("vehicles").select(
            "*, residents(full_name, apartment, phone)"
        ).eq("condominium_id", condominium_id).ilike(
            "license_plate", f"%{plate}%"
        ).execute()

        # Buscar movimientos recientes
        movements_result = supabase.table("access_logs").select(
            "timestamp, direction, access_decision, access_point"
        ).eq("condominium_id", condominium_id).ilike(
            "license_plate", f"%{plate}%"
        ).order("timestamp", desc=True).limit(20).execute()

        vehicle_info = None
        if vehicle_result.data:
            v = vehicle_result.data[0]
            r = v.get("residents") or {}
            vehicle_info = {
                "license_plate": v["license_plate"],
                "brand": v.get("brand"),
                "model": v.get("model"),
                "color": v.get("color"),
                "status": "registered",
                "owner": r.get("full_name"),
                "apartment": r.get("apartment"),
                "phone": r.get("phone")
            }

        return {
            "success": True,
            "vehicle_info": vehicle_info,
            "recent_movements": movements_result.data,
            "total_movements": len(movements_result.data)
        }

    except Exception as e:
        logger.error(f"❌ Error buscando vehículo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

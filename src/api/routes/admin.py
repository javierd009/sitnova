"""
Endpoints de administración:
- Gestión de sesiones activas
- Control manual de puertas
- Consulta de logs
- Estadísticas
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from src.config.settings import settings

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class ManualDoorControl(BaseModel):
    """Request para control manual de puerta"""
    door_id: int
    action: str  # "open" | "close"
    reason: str


class SessionInfo(BaseModel):
    """Información de sesión activa"""
    session_id: str
    condominium_id: str
    current_step: str
    started_at: str
    visitor_name: Optional[str] = None


# ============================================
# ENDPOINTS
# ============================================

@router.get("/sessions/active")
async def get_active_sessions():
    """
    Obtiene todas las sesiones activas.
    Útil para monitoreo en tiempo real.
    """
    # TODO: Consultar Redis por sesiones activas
    return {
        "total": 0,
        "sessions": [],
    }


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    """
    Obtiene detalle completo de una sesión.
    """
    # TODO: Consultar LangGraph checkpointer
    return {
        "session_id": session_id,
        "status": "active",
        "state": {},
    }


@router.post("/door/control")
async def manual_door_control(request: ManualDoorControl):
    """
    Control manual de puerta (override).
    Requiere autenticación de admin.
    """
    logger.warning(
        f"⚠️  Control manual de puerta {request.door_id}: {request.action} "
        f"- Razón: {request.reason}"
    )

    # TODO: Llamar a servicio de Hikvision
    # TODO: Registrar en access_logs con tipo "manual_override"

    return {
        "success": True,
        "door_id": request.door_id,
        "action": request.action,
    }


@router.get("/stats/today")
async def get_today_stats():
    """
    Estadísticas del día actual:
    - Total de accesos
    - Accesos autorizados vs denegados
    - Tipos de autorización
    - Tiempo promedio de procesamiento
    """
    # TODO: Consultar Supabase (vista daily_access_stats)
    return {
        "date": "2025-11-30",
        "total_accesses": 0,
        "authorized": 0,
        "denied": 0,
        "by_type": {},
        "avg_processing_time": 0.0,
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Health check detallado con estado de dependencias.
    """
    # TODO: Verificar conexiones
    # - Redis
    # - Supabase
    # - Servicio OCR
    # - Hikvision
    # - FreePBX

    return {
        "status": "healthy",
        "services": {
            "redis": "unknown",
            "supabase": "unknown",
            "ocr_service": "unknown",
            "hikvision": "unknown",
            "freepbx": "unknown",
        },
    }

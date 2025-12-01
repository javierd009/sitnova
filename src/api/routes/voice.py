"""
API Routes para gestion de llamadas de voz con Ultravox.
Permite iniciar, monitorear y terminar llamadas del portero virtual.
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from loguru import logger

from src.config.settings import settings
from src.services.voice.ultravox_client import (
    get_ultravox_client,
    UltravoxClient,
    UltravoxCall,
)
from src.services.voice.webhook_handler import (
    get_active_sessions,
    get_session_transcript,
)

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class CreateCallRequest(BaseModel):
    """Request para crear una llamada."""
    visitor_plate: Optional[str] = None
    visitor_name: Optional[str] = None
    resident_apartment: Optional[str] = None
    resident_name: Optional[str] = None
    use_sip: bool = False
    sip_uri: Optional[str] = None


class CreateCallResponse(BaseModel):
    """Response de llamada creada."""
    success: bool
    call_id: str
    session_id: str
    join_url: str
    message: str


class CallStatusResponse(BaseModel):
    """Response de estado de llamada."""
    call_id: str
    status: str
    duration: Optional[int] = None
    transcript_count: int = 0


# ============================================
# ENDPOINTS
# ============================================

@router.post("/calls", response_model=CreateCallResponse)
async def create_voice_call(
    request: CreateCallRequest,
    background_tasks: BackgroundTasks,
):
    """
    Crea una nueva llamada de voz con el portero virtual.

    Esta llamada inicia una sesion de Ultravox que puede conectarse via:
    - WebRTC (navegador/app)
    - SIP (intercomunicador Fanvil)

    El agente de voz guiara la conversacion con el visitante.
    """
    client = get_ultravox_client()

    if not client.api_key:
        raise HTTPException(
            status_code=503,
            detail="Ultravox no configurado. Falta ULTRAVOX_API_KEY."
        )

    # Generar session_id unico
    session_id = f"portero-{uuid.uuid4().hex[:8]}"

    # Contexto del visitante
    visitor_context = {}
    if request.visitor_plate:
        visitor_context["plate"] = request.visitor_plate
    if request.visitor_name:
        visitor_context["name"] = request.visitor_name

    try:
        if request.use_sip and request.sip_uri:
            # Llamada via SIP (intercomunicador)
            call = await client.create_sip_call(
                session_id=session_id,
                sip_uri=request.sip_uri,
                visitor_context=visitor_context,
            )
        else:
            # Llamada via WebRTC
            call = await client.create_call(
                session_id=session_id,
                visitor_context=visitor_context,
                resident_name=request.resident_name,
                apartment=request.resident_apartment,
            )

        logger.success(f"Llamada creada: {call.call_id}")

        return CreateCallResponse(
            success=True,
            call_id=call.call_id,
            session_id=session_id,
            join_url=call.join_url,
            message="Llamada creada exitosamente. Use join_url para conectar.",
        )

    except Exception as e:
        logger.error(f"Error creando llamada: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creando llamada: {str(e)}"
        )


@router.get("/calls/{call_id}", response_model=CallStatusResponse)
async def get_call_status(call_id: str):
    """
    Obtiene el estado de una llamada.
    """
    client = get_ultravox_client()

    try:
        status = await client.get_call_status(call_id)

        return CallStatusResponse(
            call_id=call_id,
            status=status.get("status", "unknown"),
            duration=status.get("duration"),
            transcript_count=len(status.get("messages", [])),
        )

    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Llamada no encontrada: {call_id}"
        )


@router.post("/calls/{call_id}/end")
async def end_voice_call(call_id: str):
    """
    Termina una llamada activa.
    """
    client = get_ultravox_client()

    try:
        success = await client.end_call(call_id)

        if success:
            return {"status": "ended", "call_id": call_id}
        else:
            raise HTTPException(status_code=500, detail="Error terminando llamada")

    except Exception as e:
        logger.error(f"Error terminando llamada: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calls/{call_id}/transcript")
async def get_call_transcript(call_id: str):
    """
    Obtiene la transcripcion de una llamada.
    Primero busca en sesiones activas, luego en Ultravox API.
    """
    # Primero buscar en sesiones locales
    local_transcript = get_session_transcript(call_id)
    if local_transcript:
        return {
            "call_id": call_id,
            "source": "local",
            "transcript": local_transcript,
        }

    # Si no esta local, buscar en Ultravox
    client = get_ultravox_client()
    try:
        transcript = await client.get_transcript(call_id)
        return {
            "call_id": call_id,
            "source": "ultravox",
            "transcript": transcript,
        }
    except Exception as e:
        logger.error(f"Error obteniendo transcripcion: {e}")
        raise HTTPException(status_code=404, detail="Transcripcion no encontrada")


@router.get("/sessions")
async def list_active_sessions():
    """
    Lista todas las sesiones de voz activas.
    Util para monitoreo y debugging.
    """
    sessions = get_active_sessions()
    return {
        "count": len(sessions),
        "sessions": sessions,
    }


# ============================================
# ENDPOINTS DE TESTING
# ============================================

@router.post("/test/simulate-visitor")
async def simulate_visitor_arrival(
    plate: str = "ABC123",
    visitor_name: str = "Juan Perez",
):
    """
    Endpoint de testing: Simula la llegada de un visitante.
    Crea una llamada de prueba con contexto.

    Solo disponible en desarrollo.
    """
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    client = get_ultravox_client()
    session_id = f"test-{uuid.uuid4().hex[:8]}"

    # Simular deteccion de placa
    visitor_context = {
        "plate": plate,
        "name": visitor_name,
        "vehicle_type": "sedan",
        "detected_at": datetime.now().isoformat(),
    }

    try:
        call = await client.create_call(
            session_id=session_id,
            visitor_context=visitor_context,
        )

        return {
            "status": "simulation_started",
            "session_id": session_id,
            "call_id": call.call_id,
            "join_url": call.join_url,
            "visitor": visitor_context,
            "instructions": "Abre join_url en un navegador para simular la conversacion",
        }

    except Exception as e:
        logger.error(f"Error en simulacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def voice_health_check():
    """
    Health check del servicio de voz.
    Verifica que Ultravox este configurado.
    """
    client = get_ultravox_client()

    return {
        "status": "healthy" if client.api_key else "not_configured",
        "ultravox_configured": bool(client.api_key),
        "voice": client.voice,
        "model": client.model,
    }

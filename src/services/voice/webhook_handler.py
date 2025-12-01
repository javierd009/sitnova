"""
Manejador de webhooks de Ultravox.
Procesa eventos de llamadas y ejecuta acciones via LangGraph.
"""
import json
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
from loguru import logger

from src.config.settings import settings


# Enum local para evitar importar dependencias pesadas de LangChain
class VisitStep(str, Enum):
    """Pasos del flujo de visita (copia local)"""
    INICIO = "inicio"
    VERIFICANDO_PLACA = "verificando_placa"
    CONVERSANDO = "conversando"
    ESPERANDO_AUTORIZACION = "esperando_autorizacion"
    ACCESO_OTORGADO = "acceso_otorgado"
    ACCESO_DENEGADO = "acceso_denegado"


# ============================================
# SESIONES ACTIVAS (en produccion usar Redis)
# ============================================

active_sessions: Dict[str, Dict[str, Any]] = {}


# ============================================
# VERIFICACION DE FIRMA
# ============================================

def verify_ultravox_signature(
    signature: Optional[str],
    payload: bytes,
    secret: Optional[str] = None,
) -> bool:
    """
    Verifica la firma del webhook de Ultravox.

    Args:
        signature: Firma recibida en header X-Webhook-Signature
        payload: Body del request como bytes
        secret: Webhook secret (usa settings si no se provee)

    Returns:
        True si la firma es valida
    """
    if not signature:
        logger.warning("Webhook sin firma - aceptando en desarrollo")
        return settings.is_development

    webhook_secret = secret or settings.ultravox_webhook_secret
    if not webhook_secret:
        logger.warning("ULTRAVOX_WEBHOOK_SECRET no configurado")
        return settings.is_development

    # Calcular HMAC SHA256
    expected = hmac.new(
        webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Comparar de forma segura
    return hmac.compare_digest(signature, expected)


# ============================================
# HANDLERS POR TIPO DE EVENTO
# ============================================

async def handle_call_started(call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa el evento de llamada iniciada.
    Crea una nueva sesion del portero.
    """
    session_id = data.get("metadata", {}).get("session_id", call_id)
    condominium_id = data.get("metadata", {}).get("condominium_id", "default")

    logger.info(f"Llamada iniciada: {call_id} (sesion: {session_id})")

    # Crear estado inicial del portero (formato simplificado para tracking)
    initial_state = {
        "session_id": session_id,
        "condominium_id": condominium_id,
        "current_step": VisitStep.INICIO.value,
        "visitor_name": None,
        "cedula": None,
        "plate": data.get("metadata", {}).get("plate"),
        "resident_id": None,
        "resident_name": None,
        "apartment": None,
        "is_plate_authorized": False,
        "is_pre_authorized": False,
        "resident_authorized": None,
        "access_granted": False,
        "call_sid": call_id,
        "call_active": True,
        "started_at": datetime.now().isoformat(),
        "metadata": {
            "call_id": call_id,
            "medium": data.get("medium", "webrtc"),
        }
    }

    # Guardar sesion activa
    active_sessions[call_id] = {
        "session_id": session_id,
        "state": initial_state,
        "started_at": datetime.now().isoformat(),
        "transcript": [],
    }

    return {
        "status": "session_created",
        "session_id": session_id,
        "call_id": call_id,
    }


async def handle_call_transcript(call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa fragmentos de transcripcion.
    Actualiza el estado de la conversacion.
    """
    transcript = data.get("transcript", {})
    role = transcript.get("role", "unknown")
    text = transcript.get("text", "")

    logger.debug(f"Transcripcion [{role}]: {text[:50]}...")

    # Obtener sesion activa
    session = active_sessions.get(call_id)
    if not session:
        logger.warning(f"Sesion no encontrada para call: {call_id}")
        return {"status": "session_not_found"}

    # Agregar al historial
    session["transcript"].append({
        "role": role,
        "text": text,
        "timestamp": datetime.now().isoformat(),
    })

    return {
        "status": "transcript_saved",
        "call_id": call_id,
        "role": role,
    }


async def handle_tool_call(call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa invocaciones de herramientas desde Ultravox.
    Ejecuta la accion correspondiente en el backend.
    """
    tool_name = data.get("tool", {}).get("name")
    tool_params = data.get("tool", {}).get("parameters", {})

    logger.info(f"Tool call: {tool_name} con params: {tool_params}")

    session = active_sessions.get(call_id)
    if not session:
        return {"status": "error", "error": "Session not found"}

    # Mapear tools de Ultravox a acciones del agente
    result = await execute_agent_tool(
        session_id=session["session_id"],
        tool_name=tool_name,
        params=tool_params,
    )

    return {
        "status": "tool_executed",
        "tool": tool_name,
        "result": result,
    }


async def handle_call_ended(call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa el fin de una llamada.
    Finaliza la sesion y registra el evento.
    """
    reason = data.get("reason", "normal")
    duration = data.get("duration", 0)

    logger.info(f"Llamada terminada: {call_id} (razon: {reason}, duracion: {duration}s)")

    session = active_sessions.get(call_id)
    if session:
        # Registrar evento de finalizacion
        session["ended_at"] = datetime.now().isoformat()
        session["end_reason"] = reason
        session["duration"] = duration

        # TODO: Persistir sesion completa en Supabase
        # await save_session_to_db(session)

        # Limpiar sesion activa (en produccion mover a Redis con TTL)
        del active_sessions[call_id]

    return {
        "status": "session_ended",
        "call_id": call_id,
        "reason": reason,
        "duration": duration,
    }


async def handle_call_error(call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa errores de llamada.
    """
    error_code = data.get("error", {}).get("code", "unknown")
    error_message = data.get("error", {}).get("message", "Unknown error")

    logger.error(f"Error en llamada {call_id}: {error_code} - {error_message}")

    return {
        "status": "error_logged",
        "call_id": call_id,
        "error_code": error_code,
    }


# ============================================
# EJECUTOR DE TOOLS
# ============================================

async def execute_agent_tool(
    session_id: str,
    tool_name: str,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Ejecuta un tool del agente LangGraph basado en
    la invocacion desde Ultravox.
    """
    # Importar tools del agente (son LangChain tools con decorador @tool)
    from src.agent.tools import (
        check_pre_authorized_visitor,
        notify_resident_whatsapp,
        open_gate,
        log_access_event,
    )

    # Obtener condominium_id de la sesion activa
    session = active_sessions.get(session_id) or {}
    condominium_id = session.get("state", {}).get("condominium_id", "default")

    try:
        if tool_name == "verificar_visitante_preautorizado":
            # Verificar pre-autorizacion usando los parametros correctos del tool
            result = check_pre_authorized_visitor.invoke({
                "condominium_id": condominium_id,
                "cedula": params.get("cedula", ""),
            })
            return {
                "authorized": result.get("authorized", False),
                "resident_name": result.get("resident_name"),
                "message": "Pre-autorizado" if result.get("authorized") else "No pre-autorizado",
            }

        elif tool_name == "notificar_residente":
            # Enviar notificacion WhatsApp con parametros correctos
            result = notify_resident_whatsapp.invoke({
                "resident_phone": "+50688888888",  # TODO: Buscar por apartamento
                "visitor_name": params.get("nombre_visitante", "Visitante"),
                "cedula_photo_url": None,
            })
            return {
                "notified": result.get("sent", False),
                "message": "Residente notificado" if result.get("sent") else "Error notificando",
            }

        elif tool_name == "abrir_porton":
            # Abrir porton con parametros correctos
            result = open_gate.invoke({
                "condominium_id": condominium_id,
                "door_id": 1,
                "reason": params.get("motivo", "Autorizado por voz"),
            })
            return {
                "opened": result.get("success", False),
                "message": "Porton abierto" if result.get("success") else "Error abriendo porton",
            }

        elif tool_name == "denegar_acceso":
            # Registrar denegacion con parametros correctos
            result = log_access_event.invoke({
                "condominium_id": condominium_id,
                "entry_type": "intercom",
                "access_decision": "denied",
                "decision_reason": params.get("razon", "Denegado por agente"),
                "decision_method": "voice_agent",
            })
            return {
                "logged": result.get("success", False),
                "message": "Acceso denegado registrado",
            }

        else:
            logger.warning(f"Tool desconocido: {tool_name}")
            return {"error": f"Tool '{tool_name}' no reconocido"}

    except Exception as e:
        logger.error(f"Error ejecutando tool {tool_name}: {e}")
        return {"error": str(e)}


# ============================================
# HANDLER PRINCIPAL
# ============================================

async def process_ultravox_webhook(
    event: str,
    call_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Router principal de eventos de Ultravox.

    Args:
        event: Tipo de evento (call.started, call.transcript, etc)
        call_id: ID de la llamada
        data: Payload del evento

    Returns:
        Resultado del procesamiento
    """
    logger.info(f"Procesando evento Ultravox: {event}")

    handlers = {
        "call.started": handle_call_started,
        "call.transcript": handle_call_transcript,
        "call.tool_call": handle_tool_call,
        "call.ended": handle_call_ended,
        "call.error": handle_call_error,
    }

    handler = handlers.get(event)
    if not handler:
        logger.warning(f"Evento no manejado: {event}")
        return {"status": "unknown_event", "event": event}

    return await handler(call_id, data)


# ============================================
# UTILIDADES
# ============================================

def get_active_sessions() -> Dict[str, Dict[str, Any]]:
    """Retorna las sesiones activas (para debugging)."""
    return {
        call_id: {
            "session_id": s["session_id"],
            "started_at": s["started_at"],
            "transcript_count": len(s.get("transcript", [])),
        }
        for call_id, s in active_sessions.items()
    }


def get_session_transcript(call_id: str) -> list:
    """Obtiene la transcripcion de una sesion."""
    session = active_sessions.get(call_id)
    if session:
        return session.get("transcript", [])
    return []

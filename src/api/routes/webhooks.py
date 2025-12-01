"""
Webhooks para integraciones externas:
- Ultravox (voice AI)
- Hikvision (eventos de camaras)
- Evolution API (WhatsApp responses)
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Annotated
from loguru import logger

from src.config.settings import settings
from src.services.voice.webhook_handler import (
    process_ultravox_webhook,
    verify_ultravox_signature,
    get_active_sessions,
)

router = APIRouter()


# ============================================
# ULTRAVOX WEBHOOKS
# ============================================

@router.post("/ultravox")
async def ultravox_webhook(
    request: Request,
    x_webhook_signature: Annotated[Optional[str], Header()] = None,
):
    """
    Webhook para eventos de Ultravox Voice AI.

    Eventos manejados:
    - call.started: Inicia sesion del portero
    - call.transcript: Actualiza transcripcion
    - call.tool_call: Ejecuta herramientas (verificar, notificar, abrir)
    - call.ended: Finaliza sesion
    - call.error: Registra errores
    """
    # Obtener body para verificacion de firma
    body = await request.body()

    # Validar firma (opcional en desarrollo)
    if not verify_ultravox_signature(x_webhook_signature, body):
        logger.warning("Firma de webhook invalida")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parsear payload
    payload = await request.json()
    event = payload.get("event", "unknown")
    call_id = payload.get("callId", payload.get("call_id", "unknown"))
    data = payload.get("data", payload)

    logger.info(f"Ultravox webhook: {event} (call: {call_id})")

    # Procesar evento
    result = await process_ultravox_webhook(event, call_id, data)

    return {
        "status": "processed",
        "event": event,
        "result": result,
    }


@router.get("/ultravox/sessions")
async def get_ultravox_sessions():
    """
    Endpoint de debug para ver sesiones activas.
    Solo disponible en desarrollo.
    """
    if not settings.is_development:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "active_sessions": get_active_sessions(),
    }


# ============================================
# HIKVISION WEBHOOKS
# ============================================

@router.post("/hikvision/events")
async def hikvision_events(request: Request):
    """
    Webhook para eventos de Hikvision.

    Eventos esperados:
    - Motion detection
    - Face detection
    - Vehicle detection
    - Door events
    """
    # Hikvision envía XML, no JSON
    body = await request.body()

    logger.info(f"📹 Hikvision event received")

    # TODO: Parsear XML de Hikvision
    # TODO: Trigger vision processing si es detección de vehículo

    return {"status": "received"}


# ============================================
# EVOLUTION API (WhatsApp) WEBHOOKS
# ============================================

@router.post("/evolution/whatsapp")
async def evolution_webhook(request: Request):
    """
    Webhook para respuestas de WhatsApp (Evolution API).

    Usado para capturar respuestas de residentes a autorizaciones.
    """
    payload = await request.json()
    event = payload.get("event")

    logger.info(f"💬 WhatsApp webhook: {event}")

    # TODO: Procesar respuesta del residente
    # - "SÍ" o "1" → Autorizar acceso
    # - "NO" o "2" → Denegar acceso

    return {"status": "received"}

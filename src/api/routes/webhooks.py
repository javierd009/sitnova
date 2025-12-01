"""
Webhooks para integraciones externas:
- Ultravox (voice AI)
- Hikvision (eventos de cámaras)
- Evolution API (WhatsApp responses)
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Annotated
from loguru import logger

from src.config.settings import settings

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
    Webhook para eventos de Ultravox.

    Eventos esperados:
    - call.started: Llamada iniciada
    - call.transcript: Transcripción de audio
    - call.ended: Llamada terminada
    - call.error: Error en la llamada
    """
    payload = await request.json()
    event = payload.get("event")

    # TODO: Validar signature
    # if not verify_ultravox_signature(x_webhook_signature, payload):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    logger.info(f"📞 Ultravox webhook: {event}")

    # TODO: Procesar evento con LangGraph
    # - call.started → Inicializar estado
    # - call.transcript → Actualizar conversación
    # - call.ended → Finalizar sesión

    return {"status": "received", "event": event}


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

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
from src.api.routes.auth_state import (
    get_pending_authorization,
    update_authorization,
    get_all_authorizations,
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

    # Validar firma (deshabilitado temporalmente para testing)
    # TODO: Habilitar en producción cuando Ultravox envíe firmas
    # if not verify_ultravox_signature(x_webhook_signature, body):
    #     logger.warning("Firma de webhook invalida")
    #     raise HTTPException(status_code=401, detail="Invalid webhook signature")
    logger.info("Webhook signature validation bypassed (testing mode)")

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
# Funciones de auth_state compartidas con tools.py

@router.post("/evolution/whatsapp")
async def evolution_webhook(request: Request):
    """
    Webhook para respuestas de WhatsApp (Evolution API).

    Usado para capturar respuestas de residentes a autorizaciones.
    Evolution API envía eventos como:
    - messages.upsert: Mensaje recibido
    """
    payload = await request.json()
    event = payload.get("event")

    logger.info(f"💬 WhatsApp webhook: {event}")
    logger.debug(f"Payload: {payload}")

    # Procesar solo mensajes entrantes
    if event == "messages.upsert":
        data = payload.get("data", {})
        message = data.get("message", {})

        # Obtener info del mensaje
        remote_jid = data.get("key", {}).get("remoteJid", "")
        from_me = data.get("key", {}).get("fromMe", True)
        text = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "")

        # Solo procesar mensajes entrantes (no los que enviamos nosotros)
        if from_me:
            logger.debug("Ignorando mensaje propio")
            return {"status": "ignored", "reason": "own_message"}

        # Extraer número de teléfono
        phone = remote_jid.replace("@s.whatsapp.net", "")

        logger.info(f"📥 Mensaje de {phone}: {text}")

        # Buscar autorización pendiente para este número
        key, auth = get_pending_authorization(phone)

        if auth and auth.get("status") == "pendiente":
            text_lower = text.lower().strip()

            # Detectar autorización o rechazo
            if text_lower in ["si", "sí", "yes", "1", "ok", "autorizo", "autorizado", "dale", "pase"]:
                update_authorization(phone, "autorizado")
                logger.success(f"✅ Acceso AUTORIZADO por {phone}")
                return {
                    "status": "processed",
                    "action": "authorized",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                }

            elif text_lower in ["no", "2", "negar", "denegado", "rechazar", "no autorizo"]:
                update_authorization(phone, "denegado")
                logger.warning(f"❌ Acceso DENEGADO por {phone}")
                return {
                    "status": "processed",
                    "action": "denied",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                }

            else:
                logger.info(f"Respuesta no reconocida: {text}")
                return {"status": "unrecognized", "message": text}

        else:
            logger.info(f"No hay autorización pendiente para {phone}")
            return {"status": "no_pending_auth"}

    return {"status": "received", "event": event}


@router.get("/evolution/autorizaciones")
async def listar_autorizaciones():
    """Debug: Ver autorizaciones pendientes."""
    auths = get_all_authorizations()
    return {
        "total": len(auths),
        "autorizaciones": auths,
    }

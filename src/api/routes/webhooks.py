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
    - messages.upsert / MESSAGES_UPSERT: Mensaje recibido
    """
    # Log raw body for debugging
    try:
        raw_body = await request.body()
        logger.info(f"📨 RAW WEBHOOK BODY: {raw_body.decode('utf-8')[:500]}")
    except Exception as e:
        logger.error(f"Error reading raw body: {e}")

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"❌ Error parsing JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    event = payload.get("event", "")
    instance = payload.get("instance", "unknown")

    logger.info(f"💬 WhatsApp webhook received!")
    logger.info(f"   Event: {event}")
    logger.info(f"   Instance: {instance}")
    logger.info(f"   Full payload keys: {list(payload.keys())}")

    # Normalizar evento (manejar mayúsculas y minúsculas)
    event_normalized = event.lower().replace("_", ".")

    # Procesar mensajes entrantes (messages.upsert o MESSAGES_UPSERT)
    if event_normalized == "messages.upsert":
        logger.info("📩 Procesando evento messages.upsert")

        # Evolution API puede enviar data de diferentes formas
        data = payload.get("data", payload)  # A veces data está en root
        message = data.get("message", {})
        key_data = data.get("key", {})

        # Obtener info del mensaje
        remote_jid = key_data.get("remoteJid", "")
        from_me = key_data.get("fromMe", False)

        # Extraer texto del mensaje (puede estar en varios lugares)
        text = (
            message.get("conversation") or
            message.get("extendedTextMessage", {}).get("text", "") or
            data.get("body", "") or
            ""
        )

        logger.info(f"   📱 RemoteJID: {remote_jid}")
        logger.info(f"   📤 FromMe: {from_me}")
        logger.info(f"   💬 Text: {text}")
        logger.info(f"   📋 Message keys: {list(message.keys()) if message else 'empty'}")

        # Solo procesar mensajes entrantes (no los que enviamos nosotros)
        if from_me:
            logger.info("⏭️ Ignorando mensaje propio (fromMe=true)")
            return {"status": "ignored", "reason": "own_message"}

        # Extraer número de teléfono (quitar @s.whatsapp.net)
        phone = remote_jid.replace("@s.whatsapp.net", "").replace("@c.us", "")
        logger.info(f"📞 Número extraído: {phone}")

        # Buscar autorización pendiente para este número
        key, auth = get_pending_authorization(phone)
        logger.info(f"🔍 Búsqueda de autorización: key={key}, auth={auth}")

        # Log all pending authorizations for debugging
        all_auths = get_all_authorizations()
        logger.info(f"📋 Todas las autorizaciones pendientes: {all_auths}")

        if auth and auth.get("status") == "pendiente":
            text_lower = text.lower().strip()
            logger.info(f"🔄 Procesando respuesta: '{text_lower}'")

            # Detectar autorización (más palabras)
            palabras_si = ["si", "sí", "yes", "1", "ok", "autorizo", "autorizado", "dale", "pase", "dejalo", "déjalo", "que pase", "adelante", "permitido", "aprobado"]
            palabras_no = ["no", "2", "negar", "denegado", "rechazar", "no autorizo", "rechazado", "negado", "no lo conozco", "no dejar"]

            if any(palabra in text_lower for palabra in palabras_si):
                update_authorization(phone, "autorizado")
                logger.success(f"✅ ACCESO AUTORIZADO por {phone} para {auth.get('apartment')}")
                return {
                    "status": "processed",
                    "action": "authorized",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                    "responded_by": phone,
                }

            elif any(palabra in text_lower for palabra in palabras_no):
                update_authorization(phone, "denegado")
                logger.warning(f"❌ ACCESO DENEGADO por {phone} para {auth.get('apartment')}")
                return {
                    "status": "processed",
                    "action": "denied",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                    "responded_by": phone,
                }

            else:
                logger.info(f"❓ Respuesta no reconocida: '{text}'")
                return {"status": "unrecognized", "message": text, "hint": "Responda 'si' para autorizar o 'no' para denegar"}

        else:
            logger.info(f"⚠️ No hay autorización pendiente para {phone}")
            return {"status": "no_pending_auth", "phone": phone}

    else:
        logger.info(f"⏭️ Evento ignorado: {event} (normalizado: {event_normalized})")

    return {"status": "received", "event": event, "processed": False}


@router.get("/evolution/autorizaciones")
async def listar_autorizaciones():
    """Debug: Ver autorizaciones pendientes."""
    auths = get_all_authorizations()
    return {
        "total": len(auths),
        "autorizaciones": auths,
    }


@router.post("/evolution/test-webhook")
async def test_evolution_webhook():
    """
    Endpoint de prueba para simular un webhook de Evolution API.
    Útil para verificar que el procesamiento funciona.
    """
    # Simular payload de Evolution API
    test_payload = {
        "event": "messages.upsert",
        "instance": "sitnova_agente",
        "data": {
            "key": {
                "remoteJid": "50684817227@s.whatsapp.net",
                "fromMe": False,
                "id": "TEST123"
            },
            "message": {
                "conversation": "si"
            },
            "messageType": "conversation"
        }
    }

    logger.info("🧪 TEST: Simulando webhook de Evolution API")

    # Procesar como si fuera un webhook real
    event = test_payload.get("event")
    data = test_payload.get("data", {})
    key_data = data.get("key", {})
    message = data.get("message", {})

    phone = key_data.get("remoteJid", "").replace("@s.whatsapp.net", "")
    text = message.get("conversation", "")

    logger.info(f"🧪 Phone: {phone}, Text: {text}")

    # Verificar autorizaciones pendientes
    key, auth = get_pending_authorization(phone)
    all_auths = get_all_authorizations()

    return {
        "test": "webhook_simulation",
        "phone_tested": phone,
        "text_tested": text,
        "found_authorization": auth is not None,
        "authorization_details": auth,
        "all_pending_authorizations": all_auths,
        "message": "Use este endpoint después de llamar a notificar_residente para verificar el flujo"
    }


@router.get("/evolution/health")
async def evolution_health():
    """Health check para el webhook de Evolution."""
    auths = get_all_authorizations()
    return {
        "status": "ok",
        "webhook_endpoint": "/webhooks/evolution/whatsapp",
        "pending_authorizations": len(auths),
        "message": "Webhook de Evolution API activo"
    }

"""
Webhooks para integraciones externas:
- Ultravox (voice AI)
- Hikvision (eventos de camaras)
- Evolution API (WhatsApp responses)
"""
from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional, Annotated
from datetime import datetime
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
import re


def detectar_tipo_respuesta(texto: str) -> tuple[str, str]:
    """
    Detecta el tipo de respuesta del residente.

    Returns:
        tuple: (tipo, mensaje_original)
        tipo puede ser: "autorizado", "denegado", "mensaje"
    """
    if not texto:
        return "mensaje", ""

    texto_lower = texto.lower().strip()
    texto_original = texto.strip()

    # Usar regex con word boundaries para evitar falsos positivos
    # Palabras de autorización (deben ser palabras completas)
    patrones_si = [
        r'\bsi\b', r'\bsí\b', r'\byes\b', r'\bok\b', r'\bokay\b',
        r'\bautorizo\b', r'\bautorizado\b', r'\bdale\b', r'\bpase\b',
        r'\bdejalo\b', r'\bdéjalo\b', r'\bque pase\b', r'\badelante\b',
        r'\bpermitido\b', r'\baprobado\b', r'\bclaro\b', r'\bbueno\b',
        r'\bperfecto\b', r'\bsi,?\s*(que|pase|deja)', r'^1$'
    ]

    # Palabras de denegación
    patrones_no = [
        r'\bno\b', r'\bnegar\b', r'\bdenegado\b', r'\brechazar\b',
        r'\brechazado\b', r'\bnegado\b', r'\bno autorizo\b',
        r'\bno lo conozco\b', r'\bno dejar\b', r'\bno pase\b',
        r'^2$'
    ]

    # Verificar autorización
    for patron in patrones_si:
        if re.search(patron, texto_lower):
            return "autorizado", texto_original

    # Verificar denegación
    for patron in patrones_no:
        if re.search(patron, texto_lower):
            return "denegado", texto_original

    # Si no coincide con ninguno, es mensaje personalizado
    return "mensaje", texto_original

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

# Log de todos los webhooks recibidos (para debugging)
webhook_log = []
MAX_WEBHOOK_LOG = 20


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

    # Guardar en log para debugging
    webhook_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "instance": instance,
        "payload": payload,
    }
    webhook_log.append(webhook_entry)
    if len(webhook_log) > MAX_WEBHOOK_LOG:
        webhook_log.pop(0)

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

        # Extraer número de teléfono
        # En chats individuales: remoteJid es el número (@s.whatsapp.net)
        # En grupos: remoteJid es el grupo (@g.us), el número está en participant
        phone = None

        if "@g.us" in remote_jid:
            # Es un mensaje de grupo - ignorar (no procesamos autorizaciones en grupos)
            logger.info(f"⏭️ Ignorando mensaje de grupo: {remote_jid}")
            return {"status": "ignored", "reason": "group_message"}
        else:
            # Chat individual - extraer número del remoteJid
            phone = remote_jid.replace("@s.whatsapp.net", "").replace("@c.us", "")

        if not phone:
            logger.warning("⚠️ No se pudo extraer número de teléfono")
            return {"status": "error", "reason": "no_phone_extracted"}

        logger.info(f"📞 Número extraído: {phone}")

        # Buscar autorización pendiente para este número
        key, auth = get_pending_authorization(phone)
        logger.info(f"🔍 Búsqueda de autorización: key={key}, auth={auth}")

        # Log all pending authorizations for debugging
        all_auths = get_all_authorizations()
        logger.info(f"📋 Todas las autorizaciones pendientes: {all_auths}")

        if auth and auth.get("status") == "pendiente":
            logger.info(f"🔄 Procesando respuesta: '{text}'")

            # Usar función centralizada para detectar tipo de respuesta
            tipo_respuesta, mensaje_original = detectar_tipo_respuesta(text)
            logger.info(f"   📊 Tipo detectado: {tipo_respuesta}")

            if tipo_respuesta == "autorizado":
                update_authorization(phone, "autorizado")
                logger.success(f"✅ ACCESO AUTORIZADO por {phone} para {auth.get('apartment')}")
                return {
                    "status": "processed",
                    "action": "authorized",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                    "responded_by": phone,
                }

            elif tipo_respuesta == "denegado":
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
                # Mensaje personalizado del residente - guardarlo para que el agente lo comunique
                logger.info(f"💬 Mensaje personalizado del residente: '{mensaje_original}'")
                update_authorization(phone, "mensaje", mensaje_personalizado=mensaje_original)
                logger.success(f"📝 MENSAJE PERSONALIZADO guardado de {phone} para {auth.get('apartment')}")
                return {
                    "status": "processed",
                    "action": "custom_message",
                    "apartment": auth.get("apartment"),
                    "visitor": auth.get("visitor_name"),
                    "responded_by": phone,
                    "mensaje_personalizado": mensaje_original,
                    "hint": "El agente comunicará este mensaje al visitante"
                }

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


@router.post("/evolution/simular-respuesta")
async def simular_respuesta_residente(
    phone: str,
    respuesta: str = "si"
):
    """
    PRUEBA: Simula la respuesta del residente sin necesidad de WhatsApp.

    Uso:
        curl -X POST "URL/webhooks/evolution/simular-respuesta?phone=50684817227&respuesta=si"

    Esto actualiza directamente la autorización como si el residente hubiera respondido.
    """
    from src.api.routes.auth_state import _normalize_phone

    logger.info(f"🧪 SIMULANDO respuesta de residente: phone={phone}, respuesta={respuesta}")

    # Normalizar teléfono
    clean_phone = _normalize_phone(phone)
    logger.info(f"   Teléfono normalizado: {clean_phone}")

    # Buscar autorización
    key, auth = get_pending_authorization(phone)
    logger.info(f"   Autorización encontrada: key={key}, auth={auth}")

    if not auth:
        all_auths = get_all_authorizations()
        return {
            "success": False,
            "error": f"No hay autorización pendiente para {phone}",
            "phone_buscado": clean_phone,
            "todas_autorizaciones": all_auths,
            "hint": "Primero llama a /tools/notificar-residente para crear una autorización"
        }

    if auth.get("status") != "pendiente":
        return {
            "success": False,
            "error": f"La autorización ya fue procesada: {auth.get('status')}",
            "auth": auth
        }

    # Procesar respuesta usando la función centralizada
    status, mensaje_original = detectar_tipo_respuesta(respuesta)
    logger.info(f"   Tipo detectado: {status}")

    # Actualizar
    if status == "mensaje":
        success = update_authorization(phone, status, mensaje_personalizado=mensaje_original)
    else:
        success = update_authorization(phone, status)

    # Verificar que se actualizó
    key2, auth2 = get_pending_authorization(phone)

    return {
        "success": success,
        "status_aplicado": status,
        "phone": clean_phone,
        "apartment": auth.get("apartment"),
        "visitor": auth.get("visitor_name"),
        "auth_antes": auth,
        "auth_despues": auth2,
        "mensaje": f"Autorización actualizada a '{status}' para {auth.get('apartment')}"
    }


@router.get("/evolution/diagnostico-completo")
async def diagnostico_completo():
    """
    Diagnóstico completo del flujo de autorización.
    Muestra el estado de cada componente.
    """
    from src.api.routes.auth_state import _get_supabase_client, _normalize_phone

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "componentes": {},
        "autorizaciones": {},
        "webhooks_recibidos": len(webhook_log),
        "ultimos_webhooks": webhook_log[-5:] if webhook_log else [],
    }

    # 1. Verificar conexión a Supabase
    try:
        client = _get_supabase_client()
        if client:
            # Intentar query simple
            test = client.table("pending_authorizations").select("count", count="exact").execute()
            resultado["componentes"]["supabase"] = {
                "status": "ok",
                "total_registros": test.count if hasattr(test, 'count') else len(test.data) if test.data else 0
            }
        else:
            resultado["componentes"]["supabase"] = {"status": "no_disponible", "usando": "memoria"}
    except Exception as e:
        resultado["componentes"]["supabase"] = {"status": "error", "error": str(e)}

    # 2. Obtener todas las autorizaciones
    all_auths = get_all_authorizations()
    resultado["autorizaciones"] = {
        "total": len(all_auths),
        "pendientes": sum(1 for a in all_auths.values() if a.get("status") == "pendiente"),
        "autorizadas": sum(1 for a in all_auths.values() if a.get("status") == "autorizado"),
        "denegadas": sum(1 for a in all_auths.values() if a.get("status") == "denegado"),
        "mensajes": sum(1 for a in all_auths.values() if a.get("status") == "mensaje"),
        "detalle": all_auths
    }

    # 3. Verificar formato de teléfonos guardados
    phones_info = []
    for phone, auth in all_auths.items():
        phones_info.append({
            "phone_guardado": phone,
            "phone_normalizado": _normalize_phone(phone),
            "apartment": auth.get("apartment"),
            "status": auth.get("status"),
        })
    resultado["phones_registrados"] = phones_info

    # 4. Instrucciones de prueba
    resultado["como_probar"] = {
        "paso_1": "POST /tools/notificar-residente?apartamento=Casa10&nombre_visitante=Juan",
        "paso_2": "GET /webhooks/evolution/autorizaciones (verificar que se creó)",
        "paso_3_opcion_a": "POST /webhooks/evolution/simular-respuesta?phone=TELEFONO&respuesta=si",
        "paso_3_opcion_b": "El residente responde 'si' por WhatsApp real",
        "paso_4": "GET /tools/estado-autorizacion?apartamento=Casa10 (verificar estado=autorizado)",
    }

    return resultado


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


@router.get("/evolution/webhook-log")
async def ver_webhook_log():
    """
    Debug: Ver todos los webhooks recibidos de Evolution API.
    Útil para verificar si los webhooks están llegando.
    """
    return {
        "total_received": len(webhook_log),
        "webhooks": webhook_log,
        "message": "Estos son los últimos webhooks recibidos de Evolution API"
    }


@router.delete("/evolution/webhook-log")
async def limpiar_webhook_log():
    """Limpia el log de webhooks."""
    webhook_log.clear()
    return {"message": "Log de webhooks limpiado", "total": 0}

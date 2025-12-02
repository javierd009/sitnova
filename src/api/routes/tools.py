"""
Endpoints de Tools para AsterSIPVox/Ultravox.

Estos endpoints son llamados por el agente de voz cuando necesita
ejecutar acciones durante la conversacion con el visitante.

Flujo:
1. Visitante habla con el agente de voz (via AsterSIPVox)
2. El agente decide ejecutar un tool (verificar, notificar, abrir)
3. AsterSIPVox hace HTTP request a estos endpoints
4. SITNOVA ejecuta la accion y responde
5. El agente recibe la respuesta y continua la conversacion
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from loguru import logger
import json
import unicodedata


# Headers para Ultravox - indica que el agente debe hablar después del tool
ULTRAVOX_HEADERS = {
    "X-Ultravox-Agent-Reaction": "speaks"
}

from src.database.connection import get_supabase
from src.config.settings import settings
from src.services.messaging.evolution_client import create_evolution_client, EvolutionConfig
from src.api.routes.auth_state import set_pending_authorization, get_authorization_by_apartment


def normalize_text(text: str) -> str:
    """Remove accents and normalize text for search."""
    if not text:
        return text
    # Normalize unicode and remove accents
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

router = APIRouter()

# ============================================
# REGISTRO DE LLAMADAS (para debugging)
# ============================================
tool_calls_log = []
MAX_LOG_SIZE = 50


# ============================================
# HELPER: Log incoming requests for debugging
# ============================================
async def log_request(request: Request, endpoint: str) -> dict:
    """Log all incoming request details for debugging."""
    body = {}
    try:
        body = await request.json()
    except:
        pass

    # Store in memory log for diagnostics
    call_record = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "method": request.method,
        "query_params": dict(request.query_params),
        "body": body,
        "client_ip": request.client.host if request.client else "unknown",
    }
    tool_calls_log.append(call_record)

    # Keep only last N calls
    if len(tool_calls_log) > MAX_LOG_SIZE:
        tool_calls_log.pop(0)

    logger.info(f"=== INCOMING REQUEST TO {endpoint} ===")
    logger.info(f"Timestamp: {call_record['timestamp']}")
    logger.info(f"Client IP: {call_record['client_ip']}")
    logger.info(f"Body: {body}")
    logger.info(f"=====================================")

    return body


# ============================================
# SCHEMAS
# ============================================

class VerificarVisitanteRequest(BaseModel):
    """Request para verificar visitante."""
    cedula: Optional[str] = None
    nombre: Optional[str] = None


class VerificarVisitanteResponse(BaseModel):
    """Response de verificacion."""
    autorizado: bool
    mensaje: str
    residente_nombre: Optional[str] = None
    apartamento: Optional[str] = None


class NotificarResidenteRequest(BaseModel):
    """Request para notificar residente."""
    apartamento: str
    nombre_visitante: str
    motivo: Optional[str] = None


class NotificarResidenteResponse(BaseModel):
    """Response de notificacion."""
    enviado: bool
    mensaje: str
    metodo: str  # whatsapp, llamada, push


class AbrirPortonRequest(BaseModel):
    """Request para abrir porton."""
    motivo: str


class AbrirPortonResponse(BaseModel):
    """Response de apertura."""
    abierto: bool
    mensaje: str


class DenegarAccesoRequest(BaseModel):
    """Request para denegar acceso."""
    razon: str


class DenegarAccesoResponse(BaseModel):
    """Response de denegacion."""
    registrado: bool
    mensaje: str


# ============================================
# ENDPOINTS
# ============================================

@router.post("/verificar-visitante")
async def verificar_visitante(
    request: Request,
    cedula: Optional[str] = Query(None),
    nombre: Optional[str] = Query(None),
):
    """
    Verifica si un visitante tiene pre-autorizacion.
    Acepta parametros via body JSON o query params.
    """
    # Log raw request for debugging
    body = await log_request(request, "/verificar-visitante")

    # Get params from body or query
    visitor_cedula = body.get("cedula") or cedula
    visitor_nombre = body.get("nombre") or nombre

    logger.info(f"Verificando visitante: cedula={visitor_cedula}, nombre={visitor_nombre}")

    # Buscar en Supabase
    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado, usando modo mock")
            return {
                "autorizado": True,
                "mensaje": f"MOCK: El visitante {visitor_nombre or 'identificado'} autorizado (Supabase no configurado)",
                "residente_nombre": "Juan Perez",
                "apartamento": "Casa 5",
            }

        now = datetime.now().isoformat()

        # Buscar en pre_authorized_visitors
        # Schema real: visitor_name, cedula, resident_id, valid_from, valid_until
        query = supabase.table("pre_authorized_visitors").select(
            "*, residents(full_name, apartment, phone)"
        ).eq("used", False).lte("valid_from", now).gte("valid_until", now)

        # Filtrar por nombre o cedula
        if visitor_cedula and visitor_cedula != "null":
            query = query.eq("cedula", visitor_cedula)
        elif visitor_nombre:
            # Normalize name to remove accents for matching
            nombre_normalizado = normalize_text(visitor_nombre)
            logger.info(f"Buscando nombre normalizado: {nombre_normalizado}")

            # Buscar por primer nombre para mayor flexibilidad con speech-to-text
            primer_nombre = nombre_normalizado.split()[0] if nombre_normalizado else ""
            logger.info(f"Buscando por primer nombre: {primer_nombre}")
            query = query.ilike("visitor_name", f"%{primer_nombre}%")

        result = query.execute()

        if result.data and len(result.data) > 0:
            visitor = result.data[0]
            resident = visitor.get("residents", {})
            logger.info(f"Visitante PRE-AUTORIZADO encontrado: {visitor.get('visitor_name')}")
            return {
                "autorizado": True,
                "mensaje": f"El visitante {visitor.get('visitor_name')} tiene pre-autorizacion vigente",
                "residente_nombre": resident.get("full_name") if resident else None,
                "apartamento": resident.get("apartment") if resident else None,
            }
        else:
            logger.info(f"Visitante NO encontrado en pre-autorizados")
            return {
                "autorizado": False,
                "mensaje": "El visitante no tiene pre-autorizacion. Debe contactar al residente.",
                "residente_nombre": None,
                "apartamento": None,
            }

    except Exception as e:
        logger.error(f"Error buscando en Supabase: {e}")
        # Fallback a mock en caso de error
        return {
            "autorizado": False,
            "mensaje": f"Error verificando visitante: {str(e)}",
            "residente_nombre": None,
            "apartamento": None,
        }


@router.post("/notificar-residente")
async def notificar_residente(
    request: Request,
    apartamento: Optional[str] = Query(None),
    nombre_visitante: Optional[str] = Query(None),
    cedula: Optional[str] = Query(None),
    placa: Optional[str] = Query(None),
):
    """
    Envia notificacion al residente para autorizar visita.
    Acepta parametros via body JSON o query params.

    Busca el residente por apartamento y envía notificación según su preferencia:
    - WhatsApp (Evolution API)
    - Llamada telefónica (próximamente)

    Parámetros opcionales de OCR:
    - cedula: Número de cédula del visitante (capturado por OCR)
    - placa: Placa del vehículo (capturada por OCR)
    """
    body = await log_request(request, "/notificar-residente")

    apt = body.get("apartamento") or apartamento
    visitante = body.get("nombre_visitante") or nombre_visitante
    visitor_cedula = body.get("cedula") or cedula
    visitor_placa = body.get("placa") or placa

    logger.info(f"Notificando residente: apt={apt}, visitante={visitante}")
    if visitor_cedula:
        logger.info(f"   📄 Cédula: {visitor_cedula}")
    if visitor_placa:
        logger.info(f"   🚗 Placa: {visitor_placa}")

    # Buscar residente en Supabase
    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado, usando modo mock")
            return JSONResponse(
                content={
                    "enviado": True,
                    "mensaje": f"MOCK: Notificación enviada al residente de {apt}.",
                    "metodo": "mock",
                    "result": f"He notificado al residente de {apt}. Por favor espere.",
                },
                headers=ULTRAVOX_HEADERS
            )

        # Buscar residente por apartamento
        apt_normalized = normalize_text(apt) if apt else ""
        logger.info(f"🔍 Buscando residente para apartamento: '{apt}' (normalizado: '{apt_normalized}')")

        # Primero intentar búsqueda exacta (case-insensitive)
        result = supabase.table("residents").select(
            "id, full_name, apartment, phone, phone_secondary, notification_preference"
        ).ilike("apartment", apt_normalized).eq("is_active", True).execute()

        # Si no hay match exacto, buscar con patrón más flexible
        if not result.data or len(result.data) == 0:
            logger.info(f"🔍 No hay match exacto, buscando con patrón flexible...")
            result = supabase.table("residents").select(
                "id, full_name, apartment, phone, phone_secondary, notification_preference"
            ).ilike("apartment", f"%{apt_normalized}%").eq("is_active", True).execute()

        if not result.data or len(result.data) == 0:
            logger.warning(f"❌ Residente no encontrado para apartamento: {apt}")
            return JSONResponse(
                content={
                    "enviado": False,
                    "mensaje": f"No se encontró residente en {apt}. Verifique el número.",
                    "metodo": "ninguno",
                    "result": f"No encontré ningún residente registrado en {apt}. ¿Podría verificar el número de casa o apartamento?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # Si hay múltiples resultados, buscar el más específico
        logger.info(f"📋 Resultados encontrados: {len(result.data)}")
        for r in result.data:
            logger.info(f"   - {r.get('full_name')}: {r.get('apartment')} -> {r.get('phone')}")

        # Seleccionar el mejor match
        resident = None
        apt_lower = apt_normalized.lower().replace(" ", "")

        # Primero buscar match exacto
        for r in result.data:
            apt_db = r.get("apartment", "").lower().replace(" ", "")
            if apt_db == apt_lower:
                resident = r
                logger.info(f"✅ Match exacto encontrado: {r.get('full_name')}")
                break

        # Si no hay exacto, buscar el que contenga el número
        if not resident:
            # Extraer solo números del apartamento buscado
            apt_numbers = ''.join(filter(str.isdigit, apt_normalized))
            for r in result.data:
                apt_db = r.get("apartment", "").lower().replace(" ", "")
                apt_db_numbers = ''.join(filter(str.isdigit, apt_db))
                # Match si los números son exactamente iguales
                if apt_numbers and apt_db_numbers == apt_numbers:
                    resident = r
                    logger.info(f"✅ Match por número encontrado: {r.get('full_name')} (números: {apt_numbers})")
                    break

        # Si aún no hay match, usar el primero pero advertir
        if not resident:
            resident = result.data[0]
            logger.warning(f"⚠️ Usando primer resultado (puede no ser exacto): {resident.get('full_name')}")
        resident_name = resident.get("full_name", "Residente")
        resident_apt = resident.get("apartment", "?")
        whatsapp_number = resident.get("phone") or resident.get("phone_secondary")
        notification_pref = resident.get("notification_preference", "whatsapp")
        notify_whatsapp = notification_pref in ["whatsapp", "both", None]

        logger.info(f"📱 RESIDENTE SELECCIONADO:")
        logger.info(f"   Nombre: {resident_name}")
        logger.info(f"   Apartamento: {resident_apt}")
        logger.info(f"   Teléfono: {whatsapp_number}")
        logger.info(f"   Preferencia: {notification_pref}")

        metodos_usados = []

        # Enviar por WhatsApp si está habilitado
        if notify_whatsapp and whatsapp_number:
            try:
                # Crear cliente Evolution
                evolution = create_evolution_client(
                    base_url=settings.evolution_api_url,
                    api_key=settings.evolution_api_key,
                    instance_name=settings.evolution_instance_name,
                    use_mock=(not settings.evolution_api_key)
                )

                # Mensaje de notificación con datos OCR opcionales
                mensaje_wa = (
                    f"🚪 *Visita en portería*\n\n"
                    f"Hay una persona esperando en la entrada:\n"
                    f"👤 *Nombre:* {visitante}\n"
                    f"🏠 *Destino:* {apt}\n"
                )
                # Agregar datos OCR si están disponibles
                if visitor_cedula:
                    mensaje_wa += f"🪪 *Cédula:* {visitor_cedula}\n"
                if visitor_placa:
                    mensaje_wa += f"🚗 *Placa:* {visitor_placa}\n"
                mensaje_wa += (
                    f"\nResponda *SI* para autorizar o *NO* para denegar.\n"
                    f"También puede enviar un mensaje para el visitante."
                )

                result_wa = evolution.send_text(whatsapp_number, mensaje_wa)

                if result_wa.get("success"):
                    logger.success(f"WhatsApp enviado a {whatsapp_number}")
                    metodos_usados.append("whatsapp")
                    # Guardar autorización pendiente para tracking (con datos OCR)
                    set_pending_authorization(
                        whatsapp_number,
                        apt,
                        visitante,
                        cedula=visitor_cedula,
                        placa=visitor_placa
                    )
                else:
                    logger.error(f"Error enviando WhatsApp: {result_wa.get('error')}")

            except Exception as e:
                logger.error(f"Error con Evolution API: {e}")

        # TODO: Agregar notificación por llamada si notification_preference es "call"
        # if notification_pref in ["call", "both"]:
        #     # Originar llamada via AsterSIPVox
        #     metodos_usados.append("llamada")

        if not metodos_usados:
            return JSONResponse(
                content={
                    "enviado": False,
                    "mensaje": f"No se pudo notificar al residente de {apt}. Sin WhatsApp configurado.",
                    "metodo": "ninguno",
                    "result": f"No fue posible contactar al residente de {apt}. No tiene WhatsApp configurado. Por favor intente comunicarse de otra forma.",
                },
                headers=ULTRAVOX_HEADERS
            )

        return JSONResponse(
            content={
                "enviado": True,
                "mensaje": f"Notificación enviada a {resident_name} ({apt}). Por favor espere la autorización.",
                "metodo": ", ".join(metodos_usados),
                "result": f"He enviado una notificación por WhatsApp al residente de {apt}. Por favor espere un momento mientras confirma si autoriza su ingreso.",
            },
            headers=ULTRAVOX_HEADERS
        )

    except Exception as e:
        logger.error(f"Error notificando residente: {e}")
        return JSONResponse(
            content={
                "enviado": False,
                "mensaje": f"Error al notificar: {str(e)}",
                "metodo": "error",
                "result": "Hubo un problema técnico al intentar contactar al residente. Por favor intente nuevamente en unos momentos.",
            },
            headers=ULTRAVOX_HEADERS
        )


@router.post("/abrir-porton")
async def abrir_porton(
    request: Request,
    motivo: Optional[str] = Query(None),
):
    """
    Abre el porton de entrada.
    Acepta parametros via body JSON o query params.
    """
    body = await log_request(request, "/abrir-porton")

    reason = body.get("motivo") or motivo or "Autorizado por agente"

    logger.info(f"Abriendo porton: motivo={reason}")

    # TODO: Implementar apertura real via Hikvision ISAPI
    logger.success(f"PORTON ABIERTO: {reason}")

    return {
        "abierto": True,
        "mensaje": "El porton se ha abierto. Puede ingresar. Bienvenido al condominio.",
    }


@router.post("/denegar-acceso")
async def denegar_acceso(
    request: Request,
    razon: Optional[str] = Query(None),
):
    """
    Deniega el acceso y registra el evento.
    Acepta parametros via body JSON o query params.
    """
    body = await log_request(request, "/denegar-acceso")

    reason = body.get("razon") or razon or "No autorizado"

    logger.warning(f"ACCESO DENEGADO: {reason}")

    # TODO: Implementar registro real en Supabase

    return {
        "registrado": True,
        "mensaje": f"Acceso denegado. {reason}. Por favor retire su vehiculo.",
    }


@router.api_route("/buscar-residente", methods=["GET", "POST"])
async def buscar_residente(
    request: Request,
    apartamento: Optional[str] = Query(None, description="Numero de casa o apartamento"),
    nombre: Optional[str] = Query(None, description="Nombre del residente"),
):
    """
    Busca residentes por apartamento O por nombre.

    IMPORTANTE: Usar este endpoint ANTES de notificar para verificar
    que existe el residente y obtener información correcta.

    Casos manejados:
    - Búsqueda por apartamento: Retorna el residente de esa casa
    - Búsqueda por nombre: Si hay múltiples, pide más información
    - Sin resultados: Indica que no se encontró
    """
    body = await log_request(request, "/buscar-residente")

    apt = body.get("apartamento") or apartamento
    nombre_buscar = body.get("nombre") or nombre

    logger.info(f"🔍 Buscando residente: apartamento={apt}, nombre={nombre_buscar}")

    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado")
            return JSONResponse(
                content={
                    "encontrado": False,
                    "mensaje": "Base de datos no disponible",
                    "result": "No puedo acceder a la base de datos en este momento. Por favor intente más tarde.",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 1: Búsqueda por apartamento (más específica)
        if apt:
            apt_normalized = normalize_text(apt) if apt else ""

            # Buscar por apartamento
            result = supabase.table("residents").select(
                "id, full_name, apartment, phone"
            ).ilike("apartment", f"%{apt_normalized}%").eq("is_active", True).execute()

            if not result.data or len(result.data) == 0:
                logger.info(f"❌ No se encontró residente en {apt}")
                return JSONResponse(
                    content={
                        "encontrado": False,
                        "cantidad": 0,
                        "mensaje": f"No hay ningún residente registrado en {apt}.",
                        "result": f"No encontré ningún residente registrado en la casa o apartamento {apt}. ¿Podría verificar el número?",
                    },
                    headers=ULTRAVOX_HEADERS
                )

            # Seleccionar el mejor match por número
            apt_numbers = ''.join(filter(str.isdigit, apt_normalized))
            mejor_match = None
            for r in result.data:
                apt_db_numbers = ''.join(filter(str.isdigit, r.get("apartment", "")))
                if apt_numbers and apt_db_numbers == apt_numbers:
                    mejor_match = r
                    break

            if not mejor_match:
                mejor_match = result.data[0]

            logger.info(f"✅ Encontrado: {mejor_match.get('full_name')} en {mejor_match.get('apartment')}")
            return JSONResponse(
                content={
                    "encontrado": True,
                    "cantidad": 1,
                    "residente": {
                        "nombre": mejor_match.get("full_name"),
                        "apartamento": mejor_match.get("apartment"),
                        "tiene_telefono": bool(mejor_match.get("phone")),
                    },
                    "mensaje": f"Encontré a {mejor_match.get('full_name')} en {mejor_match.get('apartment')}.",
                    "result": f"Encontré a {mejor_match.get('full_name')} registrado en {mejor_match.get('apartment')}. ¿Desea que le notifique?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 2: Búsqueda por nombre (puede ser ambigua)
        elif nombre_buscar:
            nombre_normalized = normalize_text(nombre_buscar)
            primer_nombre = nombre_normalized.split()[0] if nombre_normalized else ""

            logger.info(f"🔍 Buscando por nombre: '{nombre_normalized}' (primer nombre: '{primer_nombre}')")

            # Buscar por nombre
            result = supabase.table("residents").select(
                "id, full_name, apartment, phone"
            ).ilike("full_name", f"%{primer_nombre}%").eq("is_active", True).execute()

            if not result.data or len(result.data) == 0:
                logger.info(f"❌ No se encontró residente con nombre {nombre_buscar}")
                return JSONResponse(
                    content={
                        "encontrado": False,
                        "cantidad": 0,
                        "mensaje": f"No encontré ningún residente con el nombre {nombre_buscar}.",
                        "result": f"No encontré ningún residente registrado con el nombre {nombre_buscar}. ¿Tiene el número de casa o apartamento?",
                    },
                    headers=ULTRAVOX_HEADERS
                )

            # UN SOLO RESULTADO - perfecto
            if len(result.data) == 1:
                residente = result.data[0]
                logger.info(f"✅ Un solo match: {residente.get('full_name')}")
                return JSONResponse(
                    content={
                        "encontrado": True,
                        "cantidad": 1,
                        "residente": {
                            "nombre": residente.get("full_name"),
                            "apartamento": residente.get("apartment"),
                            "tiene_telefono": bool(residente.get("phone")),
                        },
                        "mensaje": f"Encontré a {residente.get('full_name')} en {residente.get('apartment')}.",
                        "result": f"Encontré a {residente.get('full_name')} en {residente.get('apartment')}. ¿Desea que le notifique?",
                    },
                    headers=ULTRAVOX_HEADERS
                )

            # MÚLTIPLES RESULTADOS - necesita más información
            logger.info(f"⚠️ Múltiples matches ({len(result.data)}) para '{nombre_buscar}'")
            nombres_encontrados = [r.get("full_name") for r in result.data[:5]]  # Máximo 5

            return JSONResponse(
                content={
                    "encontrado": True,
                    "cantidad": len(result.data),
                    "ambiguo": True,
                    "residentes": [
                        {"nombre": r.get("full_name"), "apartamento": r.get("apartment")}
                        for r in result.data[:5]
                    ],
                    "mensaje": f"Hay {len(result.data)} residentes con ese nombre. Necesito más información.",
                    "result": f"Encontré {len(result.data)} personas con el nombre {nombre_buscar}. ¿Sabe el apellido o el número de casa para poder identificar a la persona correcta?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 3: Sin parámetros suficientes
        else:
            return JSONResponse(
                content={
                    "encontrado": False,
                    "mensaje": "Necesito el número de casa/apartamento o el nombre del residente.",
                    "result": "Para poder ayudarle necesito saber a quién busca. ¿Tiene el número de casa o el nombre de la persona?",
                },
                headers=ULTRAVOX_HEADERS
            )

    except Exception as e:
        logger.error(f"❌ Error buscando residente: {e}")
        return JSONResponse(
            content={
                "encontrado": False,
                "mensaje": f"Error en la búsqueda: {str(e)}",
                "result": "Hubo un problema técnico al buscar. Por favor intente nuevamente.",
            },
            headers=ULTRAVOX_HEADERS
        )


@router.api_route("/estado-autorizacion", methods=["GET", "POST"])
async def estado_autorizacion(
    request: Request,
    apartamento: Optional[str] = Query(None, description="Numero de apartamento"),
    session_id: Optional[str] = Query(None, description="ID de sesion de la visita"),
):
    """
    Consulta el estado de una autorizacion pendiente.

    IMPORTANTE: El agente DEBE llamar este endpoint después de notificar_residente
    para verificar si el residente ya autorizó o denegó el acceso.

    El agente debe seguir consultando hasta que el estado sea "autorizado" o "denegado".
    """
    # Log request for debugging
    body = await log_request(request, "/estado-autorizacion")

    # Obtener apartamento de body o query params
    apt = body.get("apartamento") or apartamento

    logger.info(f"🔍 Consultando estado de autorización: apartamento={apt}, session={session_id}")

    # Log all pending authorizations for debugging
    from src.api.routes.auth_state import get_all_authorizations
    all_auths = get_all_authorizations()
    logger.info(f"📋 Autorizaciones pendientes actuales: {all_auths}")

    # Buscar por apartamento si se proporciona
    if apt:
        key, auth = get_authorization_by_apartment(apt)
        logger.info(f"🔎 Resultado búsqueda: key={key}, auth={auth}")

        if auth:
            status = auth.get("status", "pendiente")
            visitor = auth.get("visitor_name", "desconocido")

            if status == "autorizado":
                logger.success(f"✅ Estado: AUTORIZADO para {apt}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "autorizado",
                        "mensaje": f"El residente ha AUTORIZADO el acceso del visitante {visitor}. Puede abrir el portón.",
                        "visitor_name": visitor,
                        "result": f"Excelente noticias. El residente de {apt} ha autorizado el ingreso de {visitor}. Puede abrir el portón.",
                    },
                    headers=ULTRAVOX_HEADERS
                )
            elif status == "denegado":
                logger.warning(f"❌ Estado: DENEGADO para {apt}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "denegado",
                        "mensaje": f"El residente ha DENEGADO el acceso del visitante {visitor}.",
                        "visitor_name": visitor,
                        "result": f"Lo siento, el residente de {apt} ha denegado el acceso. No puede ingresar al condominio.",
                    },
                    headers=ULTRAVOX_HEADERS
                )
            elif status == "mensaje":
                # Mensaje personalizado del residente
                mensaje_custom = auth.get("mensaje_personalizado", "")
                logger.info(f"💬 Estado: MENSAJE PERSONALIZADO para {apt}: {mensaje_custom}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "mensaje",
                        "mensaje": f"El residente envió un mensaje: {mensaje_custom}",
                        "visitor_name": visitor,
                        "mensaje_personalizado": mensaje_custom,
                        "result": f"El residente de {apt} le envía el siguiente mensaje: {mensaje_custom}",
                    },
                    headers=ULTRAVOX_HEADERS
                )
            else:
                logger.info(f"⏳ Estado: PENDIENTE para {apt}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "pendiente",
                        "mensaje": f"Esperando respuesta del residente de {apt}.",
                        "visitor_name": visitor,
                        "result": f"Todavía estoy esperando la respuesta del residente de {apt}. Por favor aguarde un momento más.",
                    },
                    headers=ULTRAVOX_HEADERS
                )
        else:
            logger.warning(f"⚠️ No hay autorización para {apt}")
            return JSONResponse(
                content={
                    "apartamento": apt,
                    "estado": "no_encontrado",
                    "mensaje": f"No hay autorización pendiente para {apt}.",
                    "result": f"No encontré una solicitud de autorización pendiente para {apt}. Primero debo notificar al residente.",
                },
                headers=ULTRAVOX_HEADERS
            )

    # Fallback si no hay apartamento
    logger.warning("⚠️ No se especificó apartamento")
    return JSONResponse(
        content={
            "session_id": session_id,
            "estado": "pendiente",
            "mensaje": "Especifique el apartamento para consultar el estado.",
            "result": "Necesito saber el número de casa o apartamento para consultar el estado de la autorización.",
        },
        headers=ULTRAVOX_HEADERS
    )


# ============================================
# DIAGNOSTICO - Ver llamadas recientes
# ============================================
@router.get("/diagnostico")
async def diagnostico():
    """
    Muestra las ultimas llamadas a los tools.
    Util para verificar que AsterSIPVox esta llamando correctamente.
    """
    return {
        "total_calls": len(tool_calls_log),
        "recent_calls": tool_calls_log[-10:],  # Ultimas 10
        "message": "Estas son las ultimas llamadas recibidas a los endpoints de tools"
    }


@router.delete("/diagnostico")
async def limpiar_diagnostico():
    """Limpia el log de llamadas."""
    tool_calls_log.clear()
    return {"message": "Log limpiado", "total_calls": 0}


@router.get("/autorizaciones-pendientes")
async def ver_autorizaciones():
    """
    Debug: Ver todas las autorizaciones pendientes.
    Útil para verificar que el flujo de WhatsApp está funcionando.
    """
    from src.api.routes.auth_state import get_all_authorizations, clear_old_authorizations

    # Limpiar autorizaciones viejas (más de 30 min)
    cleared = clear_old_authorizations(30)

    auths = get_all_authorizations()
    return {
        "total": len(auths),
        "autorizaciones_limpiadas": cleared,
        "autorizaciones": auths,
        "mensaje": "Use /webhooks/evolution/autorizaciones para la misma info"
    }

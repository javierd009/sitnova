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
):
    """
    Envia notificacion al residente para autorizar visita.
    Acepta parametros via body JSON o query params.

    Busca el residente por apartamento y envía notificación según su preferencia:
    - WhatsApp (Evolution API)
    - Llamada telefónica (próximamente)
    """
    body = await log_request(request, "/notificar-residente")

    apt = body.get("apartamento") or apartamento
    visitante = body.get("nombre_visitante") or nombre_visitante

    logger.info(f"Notificando residente: apt={apt}, visitante={visitante}")

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

        # Buscar residente por apartamento (normalizar para búsqueda flexible)
        apt_normalized = normalize_text(apt) if apt else ""
        result = supabase.table("residents").select(
            "id, full_name, apartment, phone, phone_secondary, notification_preference"
        ).ilike("apartment", f"%{apt_normalized}%").eq("is_active", True).limit(1).execute()

        if not result.data or len(result.data) == 0:
            logger.warning(f"Residente no encontrado para apartamento: {apt}")
            return JSONResponse(
                content={
                    "enviado": False,
                    "mensaje": f"No se encontró residente en {apt}. Verifique el número.",
                    "metodo": "ninguno",
                    "result": f"No encontré ningún residente registrado en {apt}. ¿Podría verificar el número de casa o apartamento?",
                },
                headers=ULTRAVOX_HEADERS
            )

        resident = result.data[0]
        resident_name = resident.get("full_name", "Residente")
        whatsapp_number = resident.get("phone") or resident.get("phone_secondary")
        notification_pref = resident.get("notification_preference", "whatsapp")
        notify_whatsapp = notification_pref in ["whatsapp", "both", None]

        logger.info(f"Residente encontrado: {resident_name}, WhatsApp: {whatsapp_number}, Notificar WA: {notify_whatsapp}")

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

                # Mensaje de notificación
                mensaje_wa = (
                    f"🚪 *Visita en portería*\n\n"
                    f"Hay una persona esperando en la entrada:\n"
                    f"👤 *Nombre:* {visitante}\n"
                    f"🏠 *Destino:* {apt}\n\n"
                    f"Por favor confirme si autoriza el acceso."
                )

                result_wa = evolution.send_text(whatsapp_number, mensaje_wa)

                if result_wa.get("success"):
                    logger.success(f"WhatsApp enviado a {whatsapp_number}")
                    metodos_usados.append("whatsapp")
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


@router.get("/buscar-residente")
async def buscar_residente(
    apartamento: str = Query(..., description="Numero de casa o apartamento"),
):
    """
    Busca informacion de un residente por apartamento.

    Util para el agente cuando necesita verificar si existe
    un residente en determinado apartamento.
    """
    logger.info(f"Buscando residente: apartamento={apartamento}")

    # TODO: Implementar busqueda real en Supabase
    # Por ahora, retornamos mock

    return {
        "encontrado": True,
        "apartamento": apartamento,
        "residente_nombre": "Maria Garcia",
        "telefono_registrado": True,
    }


@router.get("/estado-autorizacion")
async def estado_autorizacion(
    session_id: str = Query(..., description="ID de sesion de la visita"),
):
    """
    Consulta el estado de una autorizacion pendiente.

    Cuando el agente envia notificacion al residente, puede
    consultar periodicamente si ya respondio.
    """
    logger.info(f"Consultando estado: session={session_id}")

    # TODO: Implementar consulta real de estado
    # Por ahora, retornamos mock

    return {
        "session_id": session_id,
        "estado": "pendiente",  # pendiente, autorizado, denegado
        "mensaje": "Esperando respuesta del residente",
    }


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

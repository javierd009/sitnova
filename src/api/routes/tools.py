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
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from loguru import logger
import json

router = APIRouter()


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

    logger.info(f"=== INCOMING REQUEST TO {endpoint} ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Query params: {dict(request.query_params)}")
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

    # TODO: Implementar busqueda real en Supabase
    # Por ahora, retornamos mock para testing

    # Simular verificacion - autorizar si cedula empieza con "1"
    if visitor_cedula and str(visitor_cedula).startswith("1"):
        logger.info(f"Visitante {visitor_cedula} PRE-AUTORIZADO")
        return {
            "autorizado": True,
            "mensaje": f"El visitante {visitor_nombre or 'identificado'} tiene pre-autorizacion vigente",
            "residente_nombre": "Juan Perez",
            "apartamento": "Casa 5",
        }
    else:
        logger.info(f"Visitante {visitor_cedula or visitor_nombre} NO pre-autorizado")
        return {
            "autorizado": False,
            "mensaje": "El visitante no tiene pre-autorizacion. Debe contactar al residente.",
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
    """
    body = await log_request(request, "/notificar-residente")

    apt = body.get("apartamento") or apartamento
    visitante = body.get("nombre_visitante") or nombre_visitante

    logger.info(f"Notificando residente: apt={apt}, visitante={visitante}")

    # TODO: Implementar notificacion real via Evolution API

    return {
        "enviado": True,
        "mensaje": f"Notificacion enviada al residente de {apt}. Por favor espere la autorizacion.",
        "metodo": "whatsapp",
    }


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

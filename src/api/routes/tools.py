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
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

router = APIRouter()


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

@router.post("/verificar-visitante", response_model=VerificarVisitanteResponse)
async def verificar_visitante(request: VerificarVisitanteRequest):
    """
    Verifica si un visitante tiene pre-autorizacion.

    El agente de voz llama a este endpoint cuando necesita verificar
    si un visitante puede ingresar sin contactar al residente.

    Busca en la base de datos:
    - Pre-autorizaciones activas por cedula
    - Visitantes frecuentes
    - Proveedores autorizados
    """
    logger.info(f"Verificando visitante: cedula={request.cedula}, nombre={request.nombre}")

    # TODO: Implementar busqueda real en Supabase
    # Por ahora, retornamos mock para testing

    # Simular verificacion
    if request.cedula and request.cedula.startswith("1"):
        # Visitante pre-autorizado (mock)
        logger.info(f"Visitante {request.cedula} PRE-AUTORIZADO")
        return VerificarVisitanteResponse(
            autorizado=True,
            mensaje=f"El visitante {request.nombre or 'identificado'} tiene pre-autorizacion vigente",
            residente_nombre="Juan Perez",
            apartamento="Casa 5",
        )
    else:
        # No pre-autorizado
        logger.info(f"Visitante {request.cedula} NO pre-autorizado")
        return VerificarVisitanteResponse(
            autorizado=False,
            mensaje="El visitante no tiene pre-autorizacion. Debe contactar al residente.",
            residente_nombre=None,
            apartamento=None,
        )


@router.post("/notificar-residente", response_model=NotificarResidenteResponse)
async def notificar_residente(request: NotificarResidenteRequest):
    """
    Envia notificacion al residente para autorizar visita.

    El agente de voz llama a este endpoint cuando necesita contactar
    al residente para autorizar el ingreso de un visitante.

    Metodos de notificacion:
    1. WhatsApp (via Evolution API)
    2. Llamada telefonica (via FreePBX)
    3. Push notification (via OneSignal)
    """
    logger.info(f"Notificando residente: apt={request.apartamento}, visitante={request.nombre_visitante}")

    # TODO: Implementar notificacion real via Evolution API
    # Por ahora, retornamos mock

    # Simular envio de notificacion
    logger.info(f"WhatsApp enviado a residente de {request.apartamento}")

    return NotificarResidenteResponse(
        enviado=True,
        mensaje=f"Notificacion enviada al residente de {request.apartamento}. Por favor espere la autorizacion.",
        metodo="whatsapp",
    )


@router.post("/abrir-porton", response_model=AbrirPortonResponse)
async def abrir_porton(request: AbrirPortonRequest):
    """
    Abre el porton de entrada.

    El agente de voz llama a este endpoint cuando el visitante
    ha sido autorizado para ingresar.

    Acciones:
    1. Envia comando a Hikvision ISAPI
    2. Registra evento de acceso en Supabase
    3. Notifica al residente (opcional)
    """
    logger.info(f"Abriendo porton: motivo={request.motivo}")

    # TODO: Implementar apertura real via Hikvision ISAPI
    # Por ahora, retornamos mock

    # Simular apertura
    logger.success(f"Porton ABIERTO: {request.motivo}")

    return AbrirPortonResponse(
        abierto=True,
        mensaje="El porton se ha abierto. Puede ingresar. Bienvenido al condominio.",
    )


@router.post("/denegar-acceso", response_model=DenegarAccesoResponse)
async def denegar_acceso(request: DenegarAccesoRequest):
    """
    Deniega el acceso y registra el evento.

    El agente de voz llama a este endpoint cuando el acceso
    es denegado (residente no autorizo, visitante sospechoso, etc).

    Acciones:
    1. Registra evento de denegacion en Supabase
    2. Captura foto del visitante (opcional)
    3. Notifica a seguridad (si es necesario)
    """
    logger.warning(f"Acceso DENEGADO: {request.razon}")

    # TODO: Implementar registro real en Supabase
    # Por ahora, retornamos mock

    return DenegarAccesoResponse(
        registrado=True,
        mensaje=f"Acceso denegado. {request.razon}. Por favor retire su vehiculo.",
    )


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

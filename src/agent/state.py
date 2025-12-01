"""
Definición del estado del agente LangGraph para SITNOVA.
Este estado se mantiene durante toda la sesión de un visitante.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class VisitStep(str, Enum):
    """Pasos del flujo de visita"""
    INICIO = "inicio"
    VERIFICANDO_PLACA = "verificando_placa"
    CONVERSANDO = "conversando"
    IDENTIFICANDO_RESIDENTE = "identificando_residente"
    SOLICITANDO_CEDULA = "solicitando_cedula"
    LLAMANDO_RESIDENTE = "llamando_residente"
    ESPERANDO_AUTORIZACION = "esperando_autorizacion"
    ACCESO_OTORGADO = "acceso_otorgado"
    ACCESO_DENEGADO = "acceso_denegado"
    TIMEOUT = "timeout"
    ERROR = "error"


class AuthorizationType(str, Enum):
    """Tipos de autorización de acceso"""
    AUTO_PLACA = "auto_placa"  # Vehículo autorizado
    RESIDENTE = "residente"  # Residente autorizó por llamada
    ADMIN = "admin"  # Admin autorizó manualmente
    PRE_AUTORIZADO = "pre_autorizado"  # Visitante pre-autorizado
    PROTOCOLO = "protocolo"  # Protocolo automático del condominio
    DELIVERY = "delivery"  # Repartidor autorizado


class PorteroState(BaseModel):
    """
    Estado completo del agente virtual SITNOVA.
    Este estado se persiste en Redis via LangGraph checkpointing.
    """

    # ============================================
    # IDENTIFICADORES
    # ============================================
    session_id: str = Field(..., description="ID único de la sesión")
    condominium_id: str = Field(..., description="UUID del condominio (multi-tenant)")
    camera_id: str = Field(default="cam_entrada", description="ID de la cámara activa")
    door_id: int = Field(default=1, description="ID de la puerta a controlar")

    # ============================================
    # CONVERSACIÓN
    # ============================================
    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list,
        description="Historial de mensajes de la conversación"
    )

    # ============================================
    # DATOS DEL VISITANTE
    # ============================================
    plate: Optional[str] = Field(default=None, description="Placa del vehículo")
    plate_confidence: Optional[float] = Field(default=None, description="Confianza del OCR de placa")
    plate_image_url: Optional[str] = Field(default=None, description="URL de imagen de la placa")

    cedula: Optional[str] = Field(default=None, description="Número de cédula")
    cedula_confidence: Optional[float] = Field(default=None, description="Confianza del OCR de cédula")
    cedula_image_url: Optional[str] = Field(default=None, description="URL de imagen de cédula")

    visitor_name: Optional[str] = Field(default=None, description="Nombre del visitante")
    visitor_phone: Optional[str] = Field(default=None, description="Teléfono del visitante")
    vehicle_type: Optional[str] = Field(default=None, description="Tipo de vehículo (auto, moto, camión)")

    # ============================================
    # DATOS DEL RESIDENTE DESTINO
    # ============================================
    resident_id: Optional[str] = Field(default=None, description="UUID del residente")
    resident_name: Optional[str] = Field(default=None, description="Nombre del residente")
    resident_phone: Optional[str] = Field(default=None, description="Teléfono del residente")
    apartment: Optional[str] = Field(default=None, description="Número de casa/apartamento")

    # ============================================
    # ESTADO DE VERIFICACIONES
    # ============================================
    is_plate_authorized: bool = Field(default=False, description="¿Placa autorizada?")
    is_pre_authorized: bool = Field(default=False, description="¿Visitante pre-autorizado?")
    resident_contacted: bool = Field(default=False, description="¿Se contactó al residente?")
    resident_authorized: Optional[bool] = Field(default=None, description="¿Residente autorizó?")

    # ============================================
    # CONTROL DE FLUJO
    # ============================================
    current_step: VisitStep = Field(
        default=VisitStep.INICIO,
        description="Paso actual en el flujo"
    )

    retry_count: int = Field(default=0, description="Contador de reintentos")
    max_retries: int = Field(default=3, description="Máximo de reintentos")

    # ============================================
    # RESULTADO
    # ============================================
    access_granted: bool = Field(default=False, description="¿Acceso otorgado?")
    authorization_type: Optional[AuthorizationType] = Field(
        default=None,
        description="Tipo de autorización usada"
    )
    denial_reason: Optional[str] = Field(default=None, description="Razón de denegación")

    # ============================================
    # TIMESTAMPS
    # ============================================
    started_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(default=None)

    # ============================================
    # METADATA
    # ============================================
    images_captured: list[str] = Field(
        default_factory=list,
        description="URLs de imágenes capturadas"
    )
    notes: Optional[str] = Field(default=None, description="Notas adicionales")

    # Protocolo del condominio (cargado dinámicamente)
    protocol_config: dict = Field(
        default_factory=dict,
        description="Configuración del protocolo de atención"
    )

    # Ultravox call tracking
    call_sid: Optional[str] = Field(default=None, description="SID de la llamada de Ultravox")
    call_active: bool = Field(default=False, description="¿Llamada activa?")

    class Config:
        arbitrary_types_allowed = True


# ============================================
# TIPOS AUXILIARES
# ============================================

class OCRResult(BaseModel):
    """Resultado de una operación de OCR"""
    detected: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    image_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class VehicleCheckResult(BaseModel):
    """Resultado de verificación de vehículo"""
    authorized: bool
    resident_id: Optional[str] = None
    resident_name: Optional[str] = None
    apartment: Optional[str] = None
    vehicle_type: Optional[str] = None
    notes: Optional[str] = None


class ResidentSearchResult(BaseModel):
    """Resultado de búsqueda de residente"""
    found: bool
    resident_id: Optional[str] = None
    full_name: Optional[str] = None
    apartment: Optional[str] = None
    phone: Optional[str] = None
    authorized_visitors: list[str] = Field(default_factory=list)
    vehicles: list[dict] = Field(default_factory=list)


class PreAuthorizationCheck(BaseModel):
    """Resultado de verificación de pre-autorización"""
    authorized: bool
    resident_id: Optional[str] = None
    resident_name: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class DoorControlResult(BaseModel):
    """Resultado de control de puerta"""
    success: bool
    timestamp: datetime = Field(default_factory=datetime.now)
    door_status: Optional[str] = None
    error: Optional[str] = None


class CallResult(BaseModel):
    """Resultado de llamada al residente"""
    call_completed: bool
    response: Optional[str] = None  # "authorized", "denied", "no_answer"
    duration: Optional[int] = None  # segundos
    error: Optional[str] = None

"""
Cliente de Ultravox Voice AI para SITNOVA.
Gestiona llamadas de voz con IA para el portero virtual.
"""
import httpx
from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from src.config.settings import settings


# ============================================
# MODELOS DE DATOS
# ============================================

class UltravoxCallConfig(BaseModel):
    """Configuracion para iniciar una llamada Ultravox."""
    system_prompt: str
    voice: str = "es-CR-SofiaNeural"
    model: str = "fixie-ai/ultravox-v0_4"
    first_speaker: Literal["agent", "user"] = "agent"
    initial_messages: list[dict] = []
    tools: list[dict] = []
    temperature: float = 0.7


class UltravoxCall(BaseModel):
    """Representa una llamada activa de Ultravox."""
    call_id: str
    join_url: str
    status: str
    created_at: datetime
    session_id: Optional[str] = None


class UltravoxWebhookEvent(BaseModel):
    """Evento recibido del webhook de Ultravox."""
    event: str  # call.started, call.transcript, call.ended, call.error
    call_id: str
    timestamp: datetime
    data: Dict[str, Any] = {}


# ============================================
# CLIENTE ULTRAVOX
# ============================================

class UltravoxClient:
    """
    Cliente para la API de Ultravox Voice AI.

    Ultravox permite crear agentes de voz conversacionales
    que pueden conectarse via WebRTC o SIP.
    """

    BASE_URL = "https://api.ultravox.ai/api"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ultravox_api_key
        self.voice = settings.ultravox_voice
        self.model = settings.ultravox_model

        if not self.api_key:
            logger.warning("ULTRAVOX_API_KEY no configurada")

    @property
    def headers(self) -> dict:
        """Headers para requests a Ultravox."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_call(
        self,
        session_id: str,
        visitor_context: Optional[Dict[str, Any]] = None,
        resident_name: Optional[str] = None,
        apartment: Optional[str] = None,
    ) -> UltravoxCall:
        """
        Crea una nueva llamada de voz con Ultravox.

        Args:
            session_id: ID de sesion del portero para tracking
            visitor_context: Contexto del visitante (placa, etc)
            resident_name: Nombre del residente (si se conoce)
            apartment: Numero de apartamento/casa

        Returns:
            UltravoxCall con el call_id y join_url
        """
        # Construir el system prompt del portero
        system_prompt = self._build_system_prompt(
            visitor_context=visitor_context,
            resident_name=resident_name,
            apartment=apartment,
        )

        # Configurar los tools que el agente puede usar
        tools = self._build_agent_tools()

        # Payload para crear la llamada
        payload = {
            "systemPrompt": system_prompt,
            "voice": self.voice,
            "model": self.model,
            "firstSpeaker": "FIRST_SPEAKER_AGENT",
            "temperature": 0.7,
            "medium": {
                "webRtc": {}  # Para conexion via WebRTC
            },
            "initialMessages": [
                {
                    "role": "MESSAGE_ROLE_AGENT",
                    "text": "Buenas, bienvenido al condominio. Soy el asistente de seguridad. ¿A quién viene a visitar?"
                }
            ],
            "selectedTools": tools,
            "metadata": {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
            }
        }

        logger.info(f"Creando llamada Ultravox para sesion: {session_id}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/calls",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 201:
                logger.error(f"Error creando llamada: {response.status_code} - {response.text}")
                raise Exception(f"Error creando llamada Ultravox: {response.text}")

            data = response.json()

            call = UltravoxCall(
                call_id=data["callId"],
                join_url=data["joinUrl"],
                status="created",
                created_at=datetime.now(),
                session_id=session_id,
            )

            logger.success(f"Llamada creada: {call.call_id}")
            return call

    async def create_sip_call(
        self,
        session_id: str,
        sip_uri: str,
        visitor_context: Optional[Dict[str, Any]] = None,
    ) -> UltravoxCall:
        """
        Crea una llamada que se conecta via SIP (para Fanvil/FreePBX).

        Args:
            session_id: ID de sesion
            sip_uri: URI SIP del intercomunicador (ej: sip:entrada@pbx.local)
            visitor_context: Contexto del visitante

        Returns:
            UltravoxCall
        """
        system_prompt = self._build_system_prompt(visitor_context=visitor_context)
        tools = self._build_agent_tools()

        payload = {
            "systemPrompt": system_prompt,
            "voice": self.voice,
            "model": self.model,
            "firstSpeaker": "FIRST_SPEAKER_AGENT",
            "temperature": 0.7,
            "medium": {
                "sip": {
                    "uri": sip_uri,
                    "codec": "PCMU",  # G.711 mu-law
                }
            },
            "selectedTools": tools,
            "metadata": {
                "session_id": session_id,
                "sip_uri": sip_uri,
            }
        }

        logger.info(f"Creando llamada SIP para: {sip_uri}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/calls",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 201:
                logger.error(f"Error creando llamada SIP: {response.text}")
                raise Exception(f"Error: {response.text}")

            data = response.json()

            return UltravoxCall(
                call_id=data["callId"],
                join_url=data.get("joinUrl", ""),
                status="created",
                created_at=datetime.now(),
                session_id=session_id,
            )

    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual de una llamada."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/calls/{call_id}",
                headers=self.headers,
            )

            if response.status_code != 200:
                logger.error(f"Error obteniendo estado: {response.text}")
                return {"status": "error", "error": response.text}

            return response.json()

    async def end_call(self, call_id: str) -> bool:
        """Termina una llamada activa."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.BASE_URL}/calls/{call_id}/end",
                headers=self.headers,
            )

            if response.status_code in [200, 204]:
                logger.info(f"Llamada {call_id} terminada")
                return True

            logger.error(f"Error terminando llamada: {response.text}")
            return False

    async def get_transcript(self, call_id: str) -> list[dict]:
        """Obtiene la transcripcion completa de una llamada."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.BASE_URL}/calls/{call_id}/transcript",
                headers=self.headers,
            )

            if response.status_code != 200:
                return []

            return response.json().get("messages", [])

    def _build_system_prompt(
        self,
        visitor_context: Optional[Dict[str, Any]] = None,
        resident_name: Optional[str] = None,
        apartment: Optional[str] = None,
    ) -> str:
        """
        Construye el prompt del sistema para el agente de voz.
        """
        context_info = ""
        if visitor_context:
            if visitor_context.get("plate"):
                context_info += f"\n- Placa del vehiculo: {visitor_context['plate']}"
            if visitor_context.get("vehicle_type"):
                context_info += f"\n- Tipo: {visitor_context['vehicle_type']}"

        if resident_name:
            context_info += f"\n- Residente destino: {resident_name}"
        if apartment:
            context_info += f"\n- Casa/Apartamento: {apartment}"

        # Si no hay contexto, usar valor por defecto
        if not context_info:
            context_info = "\n- Sin informacion previa"

        return f"""Eres el asistente de seguridad virtual de un condominio residencial en Costa Rica.

Tu rol es recibir a los visitantes de manera profesional y amable, verificar su identidad y destino, y gestionar su acceso.

INFORMACION DEL VISITANTE ACTUAL:{context_info}

INSTRUCCIONES:
1. Saluda cordialmente y pregunta a quien viene a visitar
2. Solicita el nombre del visitante
3. Si es necesario, pide la cedula para verificacion
4. Una vez tengas la informacion, usa la herramienta correspondiente para verificar o notificar al residente
5. Se claro con las instrucciones ("espere un momento mientras contacto al residente")
6. Informa el resultado (acceso autorizado/denegado)

TONO:
- Profesional pero amigable
- Usa el voseo costarricense cuando sea apropiado
- Se conciso, no des explicaciones largas
- Mantene la conversacion fluida y natural

IMPORTANTE:
- Si el visitante no colabora o actua sospechoso, deniega el acceso
- Si hay una emergencia mencionada, prioriza la seguridad
- Nunca reveles informacion personal de los residentes"""

    def _build_agent_tools(self) -> list[dict]:
        """
        Define las herramientas que el agente de voz puede invocar.
        Estas se mapean a los tools del LangGraph agent.
        """
        return [
            {
                "name": "verificar_visitante_preautorizado",
                "description": "Verifica si un visitante tiene pre-autorizacion para ingresar",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "cedula": {
                            "type": "string",
                            "description": "Numero de cedula del visitante"
                        },
                        "nombre": {
                            "type": "string",
                            "description": "Nombre del visitante"
                        }
                    },
                    "required": ["nombre"]
                }
            },
            {
                "name": "notificar_residente",
                "description": "Envia notificacion al residente para autorizar la visita",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "apartamento": {
                            "type": "string",
                            "description": "Numero de casa o apartamento del residente"
                        },
                        "nombre_visitante": {
                            "type": "string",
                            "description": "Nombre del visitante que solicita acceso"
                        },
                        "motivo": {
                            "type": "string",
                            "description": "Motivo de la visita"
                        }
                    },
                    "required": ["apartamento", "nombre_visitante"]
                }
            },
            {
                "name": "abrir_porton",
                "description": "Abre el porton de acceso despues de la autorizacion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "motivo": {
                            "type": "string",
                            "description": "Razon de la apertura"
                        }
                    },
                    "required": ["motivo"]
                }
            },
            {
                "name": "denegar_acceso",
                "description": "Deniega el acceso y registra el evento",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "razon": {
                            "type": "string",
                            "description": "Razon del rechazo"
                        }
                    },
                    "required": ["razon"]
                }
            }
        ]


# ============================================
# SINGLETON
# ============================================

_ultravox_client: Optional[UltravoxClient] = None


def get_ultravox_client() -> UltravoxClient:
    """Obtiene la instancia singleton del cliente Ultravox."""
    global _ultravox_client
    if _ultravox_client is None:
        _ultravox_client = UltravoxClient()
    return _ultravox_client

"""
Cliente de AsterSIPVox para SITNOVA.
Permite originar llamadas desde el asistente virtual de FreePBX a intercomunicadores.

AsterSIPVox es el bridge entre FreePBX/Asterisk y Ultravox Voice AI.
Documentacion: https://astersipvox.asternic.net
"""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from src.config.settings import settings


# ============================================
# MODELOS DE DATOS
# ============================================

class AsterSIPVoxCallRequest(BaseModel):
    """Request para originar una llamada."""
    username: str  # Extension del asistente virtual (ej: "205")
    destination: str  # Destino a llamar (ej: "1006" o "sip:1006@pbx.local")
    api_text_to_inject: Optional[str] = None  # Prompt adicional para la llamada


class AsterSIPVoxCallResponse(BaseModel):
    """Response de llamada originada."""
    destination: str
    from_user: str
    status: str


class StoredData(BaseModel):
    """Datos almacenados en el key/value store."""
    key: str
    value: Dict[str, Any]
    expires_at: Optional[datetime] = None


# ============================================
# CLIENTE ASTERSIPVOX
# ============================================

class AsterSIPVoxClient:
    """
    Cliente para la API de AsterSIPVox.

    Permite:
    - Originar llamadas salientes desde el asistente virtual
    - Almacenar/recuperar datos temporales (5 min TTL)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        assistant_extension: Optional[str] = None,
    ):
        self.base_url = base_url or settings.astersipvox_url or "http://localhost:7070"
        self.api_key = api_key or settings.astersipvox_api_key
        self.assistant_extension = assistant_extension or settings.astersipvox_extension or "205"

        if not self.api_key:
            logger.warning("ASTERSIPVOX_API_KEY no configurada")

    @property
    def headers(self) -> dict:
        """Headers para requests a AsterSIPVox."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def originate_call(
        self,
        destination: str,
        visitor_context: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None,
    ) -> AsterSIPVoxCallResponse:
        """
        Origina una llamada desde el asistente virtual al destino especificado.

        Args:
            destination: Extension o SIP URI del destino (ej: "1006")
            visitor_context: Contexto del visitante (placa, nombre, etc.)
            custom_prompt: Prompt adicional para inyectar en la conversacion

        Returns:
            AsterSIPVoxCallResponse con el estado de la llamada
        """
        # Construir prompt dinamico basado en el contexto
        prompt = self._build_call_prompt(visitor_context, custom_prompt)

        payload = {
            "username": self.assistant_extension,
            "destination": destination,
            "api_text_to_inject": prompt,
        }

        logger.info(f"Originando llamada: {self.assistant_extension} -> {destination}")
        logger.debug(f"Prompt inyectado: {prompt[:100]}...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/call",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"Error originando llamada: {response.status_code} - {response.text}")
                raise Exception(f"Error AsterSIPVox: {response.text}")

            data = response.json()
            logger.success(f"Llamada originada: {data.get('status')}")

            return AsterSIPVoxCallResponse(
                destination=data.get("destination", destination),
                from_user=data.get("from_user", self.assistant_extension),
                status=data.get("status", "unknown"),
            )

    async def store_data(self, key: str, value: Dict[str, Any]) -> bool:
        """
        Almacena datos en el key/value store (expira en 5 minutos).

        Util para pasar contexto entre llamadas o almacenar
        informacion temporal del visitante.

        Args:
            key: Clave unica (ej: ID de sesion, numero de placa)
            value: Datos a almacenar como diccionario

        Returns:
            True si se almaceno correctamente
        """
        logger.debug(f"Almacenando datos: key={key}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{self.base_url}/store/{key}",
                headers=self.headers,
                json=value,
            )

            if response.status_code != 200:
                logger.error(f"Error almacenando datos: {response.text}")
                return False

            return True

    async def get_data(self, key: str) -> Optional[StoredData]:
        """
        Recupera datos del key/value store.

        Args:
            key: Clave a buscar

        Returns:
            StoredData si existe, None si no existe o expiro
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/store/{key}",
                headers=self.headers,
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"Error recuperando datos: {response.text}")
                return None

            data = response.json()

            # El value viene como string JSON, hay que parsearlo
            import json
            value = json.loads(data.get("value", "{}"))

            return StoredData(
                key=data.get("key", key),
                value=value,
                expires_at=data.get("expires_at"),
            )

    async def get_value(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Recupera solo el valor (sin metadata) del key/value store.

        Args:
            key: Clave a buscar

        Returns:
            Diccionario con el valor, o None si no existe
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/store/{key}/value",
                headers=self.headers,
            )

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                logger.error(f"Error recuperando valor: {response.text}")
                return None

            return response.json()

    def _build_call_prompt(
        self,
        visitor_context: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Construye el prompt dinamico para la llamada.

        Este prompt se inyecta en la conversacion del asistente
        para darle contexto sobre el visitante actual.
        """
        # Prompt base del portero
        base_prompt = """Eres el asistente de seguridad virtual de un condominio residencial.
Tu rol es verificar la identidad del visitante y gestionar su acceso.

INSTRUCCIONES:
1. Saluda cordialmente
2. Pregunta a quien viene a visitar (nombre del residente y numero de casa/apartamento)
3. Solicita el nombre del visitante
4. Verifica si tiene pre-autorizacion o contacta al residente
5. Informa el resultado (acceso autorizado o denegado)

TONO: Profesional pero amigable. Se conciso."""

        # Agregar contexto del visitante si existe
        if visitor_context:
            context_lines = ["\n\nCONTEXTO DEL VISITANTE ACTUAL:"]

            if visitor_context.get("plate"):
                context_lines.append(f"- Placa del vehiculo: {visitor_context['plate']}")
            if visitor_context.get("name"):
                context_lines.append(f"- Nombre (si lo dio): {visitor_context['name']}")
            if visitor_context.get("vehicle_type"):
                context_lines.append(f"- Tipo de vehiculo: {visitor_context['vehicle_type']}")
            if visitor_context.get("resident_name"):
                context_lines.append(f"- Dice que visita a: {visitor_context['resident_name']}")
            if visitor_context.get("apartment"):
                context_lines.append(f"- Casa/Apartamento: {visitor_context['apartment']}")

            base_prompt += "\n".join(context_lines)

        # Agregar prompt personalizado si existe
        if custom_prompt:
            base_prompt += f"\n\nINSTRUCCIONES ADICIONALES:\n{custom_prompt}"

        return base_prompt


# ============================================
# SINGLETON
# ============================================

_astersipvox_client: Optional[AsterSIPVoxClient] = None


def get_astersipvox_client() -> AsterSIPVoxClient:
    """Obtiene la instancia singleton del cliente AsterSIPVox."""
    global _astersipvox_client
    if _astersipvox_client is None:
        _astersipvox_client = AsterSIPVoxClient()
    return _astersipvox_client

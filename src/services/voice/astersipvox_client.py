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
from src.services.voice.prompts import get_full_system_prompt


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

    async def hangup(
        self,
        call_id: Optional[str] = None,
        channel: Optional[str] = None,
        reason: str = "normal_clearing"
    ) -> Dict[str, Any]:
        """
        Cuelga la llamada activa.

        CRÍTICO: Usar para liberar recursos y evitar consumo de tokens/minutos.

        Args:
            call_id: ID de la llamada (si se tiene)
            channel: Canal de Asterisk (ej: "SIP/205-00000001")
            reason: Razón del hangup ("normal_clearing", "user_busy", "call_rejected")

        Returns:
            dict con resultado del hangup
        """
        payload = {
            "reason": reason,
        }

        if call_id:
            payload["call_id"] = call_id
        if channel:
            payload["channel"] = channel

        logger.info(f"📴 Colgando llamada: {call_id or channel or 'current'}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/hangup",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.success(f"✅ Llamada colgada: {data.get('status', 'ok')}")
                    return {
                        "success": True,
                        "status": data.get("status", "hangup_complete"),
                        "reason": reason,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"❌ Error colgando llamada: {response.status_code}")
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ Excepción en hangup: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def transfer(
        self,
        destination: str,
        call_id: Optional[str] = None,
        channel: Optional[str] = None,
        transfer_type: str = "blind"  # "blind" o "attended"
    ) -> Dict[str, Any]:
        """
        Transfiere la llamada activa a otra extensión (Human-in-the-Loop).

        Args:
            destination: Extensión destino (ej: "1002" para el operador)
            call_id: ID de la llamada (si se tiene)
            channel: Canal de Asterisk
            transfer_type: Tipo de transferencia:
                - "blind": Transferencia ciega (el visitante espera mientras conecta)
                - "attended": Transferencia atendida (el operador puede aceptar/rechazar)

        Returns:
            dict con resultado de la transferencia
        """
        payload = {
            "destination": destination,
            "transfer_type": transfer_type,
        }

        if call_id:
            payload["call_id"] = call_id
        if channel:
            payload["channel"] = channel

        logger.info(f"🔀 Transfiriendo llamada a: {destination} (tipo: {transfer_type})")

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.base_url}/transfer",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.success(f"✅ Llamada transferida a: {destination}")
                    return {
                        "success": True,
                        "transferred": True,
                        "destination": destination,
                        "status": data.get("status", "transfer_complete"),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"❌ Error transfiriendo: {response.status_code}")
                    return {
                        "success": False,
                        "transferred": False,
                        "error": response.text,
                        "status_code": response.status_code
                    }

        except Exception as e:
            logger.error(f"❌ Excepción en transfer: {e}")
            return {
                "success": False,
                "transferred": False,
                "error": str(e)
            }

    async def send_dtmf(self, digits: str, channel: Optional[str] = None) -> bool:
        """
        Envía tonos DTMF al canal de la llamada.

        Útil para navegación de menús IVR o señalización.

        Args:
            digits: Dígitos a enviar (ej: "1", "123#")
            channel: Canal de Asterisk (opcional)

        Returns:
            True si se enviaron correctamente
        """
        payload = {
            "digits": digits,
        }

        if channel:
            payload["channel"] = channel

        logger.debug(f"📞 Enviando DTMF: {digits}")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.base_url}/dtmf",
                    headers=self.headers,
                    json=payload,
                )

                return response.status_code == 200

        except Exception as e:
            logger.error(f"❌ Error enviando DTMF: {e}")
            return False

    def _build_call_prompt(
        self,
        visitor_context: Optional[Dict[str, Any]] = None,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """
        Construye el prompt dinamico para la llamada.

        Este prompt se inyecta en la conversacion del asistente
        para darle contexto sobre el visitante actual.
        Usa el prompt centralizado de src/services/voice/prompts.py
        """
        # Extraer datos del contexto del visitante
        plate = visitor_context.get("plate") if visitor_context else None
        name = visitor_context.get("name") if visitor_context else None
        vehicle_type = visitor_context.get("vehicle_type") if visitor_context else None
        resident_name = visitor_context.get("resident_name") if visitor_context else None
        apartment = visitor_context.get("apartment") if visitor_context else None

        # Usar el prompt centralizado
        base_prompt = get_full_system_prompt(
            plate=plate,
            name=name,
            vehicle_type=vehicle_type,
            resident_name=resident_name,
            apartment=apartment,
        )

        # Agregar prompt personalizado si existe (para casos especiales)
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

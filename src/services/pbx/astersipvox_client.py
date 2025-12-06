"""
Cliente para AsterSIPVox (Voice AI Gateway).

Permite:
1. Originar llamadas hacia residentes (outbound) con inyección de contexto AI.
2. Almacenar metadata temporal (Key/Value Store).
"""
import httpx
from typing import Dict, Any, Optional
from loguru import logger
from src.config.settings import settings

class AsterSIPVoxClient:
    def __init__(self, base_url: str, api_key: str, default_extension: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.default_extension = default_extension
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def initiate_call(
        self, 
        destination: str, 
        context_text: str, 
        extension: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inicia una llamada saliente con contexto inyectado.

        Args:
            destination: Número de destino (extensión o teléfono externo)
            context_text: Texto que guiará al agente (System Prompt injection)
            extension: Extensión desde donde se origina (opcional, usa default si no se provee)

        Returns:
            Dict con respuesta de la API
        """
        url = f"{self.base_url}/call"
        
        payload = {
            "username": extension or self.default_extension,
            "destination": destination,
            "api_text_to_inject": context_text
        }
        
        logger.info(f"📞 AsterSIPVox: Iniciando llamada a {destination} desde {payload['username']}")
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Error HTTP AsterSIPVox: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"❌ Error conectando a AsterSIPVox: {str(e)}")
                raise

    async def store_data(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Almacena datos temporales (TTL 5 min) para compartir contexto.
        """
        url = f"{self.base_url}/store/{key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=self.headers)
                return response.status_code == 200
            except Exception as e:
                logger.error(f"❌ Error guardando data en AsterSIPVox: {e}")
                return False

# Factory function
def get_astersipvox_client() -> AsterSIPVoxClient:
    return AsterSIPVoxClient(
        base_url=settings.ASTERSIPVOX_URL,
        api_key=settings.ASTERSIPVOX_API_KEY,
        default_extension=settings.ASTERSIPVOX_EXTENSION
    )

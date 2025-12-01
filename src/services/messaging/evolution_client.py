"""
Cliente para Evolution API (WhatsApp Business).

Evolution API permite:
- Enviar mensajes de texto
- Enviar imágenes/media
- Recibir mensajes via webhook
- Gestionar instancias de WhatsApp
"""
import requests
from typing import Optional, Dict, Any, List, Union
from loguru import logger
from dataclasses import dataclass
import base64
from pathlib import Path


@dataclass
class EvolutionConfig:
    """Configuración de Evolution API"""
    base_url: str  # ej: http://localhost:8080
    api_key: str
    instance_name: str = "portero"
    timeout: int = 30


class EvolutionClient:
    """
    Cliente para Evolution API.

    API Docs: https://doc.evolution-api.com/

    Endpoints principales:
    - POST /message/sendText - Enviar texto
    - POST /message/sendMedia - Enviar imagen/video/audio
    - GET /instance/connect/{instance} - Conectar instancia
    - GET /instance/qrcode/{instance} - Obtener QR
    """

    def __init__(self, config: EvolutionConfig):
        """
        Inicializa cliente Evolution API.

        Args:
            config: Configuración de Evolution
        """
        self.config = config
        self.session = requests.Session()

        # Headers comunes
        self.session.headers.update({
            "apikey": config.api_key,
            "Content-Type": "application/json"
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        files: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta request HTTP a Evolution API.

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint relativo
            json: JSON data
            files: Files para upload

        Returns:
            Response JSON

        Raises:
            requests.RequestException: Error en request
        """
        url = f"{self.config.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json,
                files=files,
                timeout=self.config.timeout
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"❌ Error en Evolution API: {method} {endpoint} - {e}")
            raise

    def send_text(
        self,
        phone: str,
        message: str,
        delay: int = 1000
    ) -> Dict[str, Any]:
        """
        Envía mensaje de texto.

        Args:
            phone: Número con código de país (ej: +50612345678 o 50612345678)
            message: Texto del mensaje
            delay: Delay en milisegundos antes de enviar

        Returns:
            Dict con resultado
        """
        logger.info(f"💬 Enviando WhatsApp a {phone}")

        # Limpiar número (quitar + y espacios)
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "number": clean_phone,
            "text": message,
            "delay": delay
        }

        try:
            endpoint = f"/message/sendText/{self.config.instance_name}"
            result = self._request("POST", endpoint, json=payload)

            if result.get("key"):
                logger.success(f"✅ Mensaje enviado a {phone}")
                return {
                    "success": True,
                    "message_id": result.get("key", {}).get("id"),
                    "phone": phone
                }
            else:
                logger.error(f"❌ Error enviando mensaje: {result}")
                return {"success": False, "error": str(result)}

        except Exception as e:
            logger.error(f"❌ Excepción enviando mensaje: {e}")
            return {"success": False, "error": str(e)}

    def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image"
    ) -> Dict[str, Any]:
        """
        Envía imagen, video o audio.

        Args:
            phone: Número destino
            media_url: URL de la imagen/video/audio (http:// o base64)
            caption: Texto que acompaña el media
            media_type: "image", "video", "audio", "document"

        Returns:
            Dict con resultado
        """
        logger.info(f"📷 Enviando {media_type} a {phone}")

        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "number": clean_phone,
            "mediatype": media_type,
            "media": media_url
        }

        if caption:
            payload["caption"] = caption

        try:
            endpoint = f"/message/sendMedia/{self.config.instance_name}"
            result = self._request("POST", endpoint, json=payload)

            if result.get("key"):
                logger.success(f"✅ Media enviado a {phone}")
                return {
                    "success": True,
                    "message_id": result.get("key", {}).get("id"),
                    "phone": phone
                }
            else:
                logger.error(f"❌ Error enviando media: {result}")
                return {"success": False, "error": str(result)}

        except Exception as e:
            logger.error(f"❌ Excepción enviando media: {e}")
            return {"success": False, "error": str(e)}

    def send_image_file(
        self,
        phone: str,
        image_path: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Envía imagen desde archivo local.

        Args:
            phone: Número destino
            image_path: Path al archivo de imagen
            caption: Texto que acompaña la imagen

        Returns:
            Dict con resultado
        """
        try:
            # Leer imagen y convertir a base64
            with open(image_path, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Determinar tipo MIME
            ext = Path(image_path).suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }
            mime = mime_types.get(ext, "image/jpeg")

            # Construir data URI
            media_url = f"data:{mime};base64,{image_base64}"

            return self.send_media(phone, media_url, caption, "image")

        except Exception as e:
            logger.error(f"❌ Error leyendo imagen {image_path}: {e}")
            return {"success": False, "error": str(e)}

    def send_with_buttons(
        self,
        phone: str,
        message: str,
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Envía mensaje con botones interactivos.

        Args:
            phone: Número destino
            message: Texto del mensaje
            buttons: Lista de botones [{"id": "1", "text": "Autorizar"}, ...]

        Returns:
            Dict con resultado
        """
        logger.info(f"🔘 Enviando mensaje con botones a {phone}")

        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "number": clean_phone,
            "text": message,
            "buttons": buttons
        }

        try:
            endpoint = f"/message/sendButtons/{self.config.instance_name}"
            result = self._request("POST", endpoint, json=payload)

            if result.get("key"):
                logger.success(f"✅ Mensaje con botones enviado a {phone}")
                return {
                    "success": True,
                    "message_id": result.get("key", {}).get("id")
                }
            else:
                return {"success": False, "error": str(result)}

        except Exception as e:
            logger.error(f"❌ Error enviando botones: {e}")
            return {"success": False, "error": str(e)}

    def get_instance_status(self) -> Dict[str, Any]:
        """
        Obtiene estado de la instancia.

        Returns:
            Dict con estado de conexión
        """
        try:
            endpoint = f"/instance/connectionState/{self.config.instance_name}"
            result = self._request("GET", endpoint)

            state = result.get("state")
            logger.info(f"📱 Estado de instancia: {state}")

            return {
                "connected": state == "open",
                "state": state,
                "instance": self.config.instance_name
            }

        except Exception as e:
            logger.error(f"❌ Error obteniendo estado: {e}")
            return {"connected": False, "error": str(e)}

    def get_qr_code(self) -> Optional[str]:
        """
        Obtiene código QR para conectar WhatsApp.

        Returns:
            Base64 del QR o None
        """
        try:
            endpoint = f"/instance/qrcode/{self.config.instance_name}"
            result = self._request("GET", endpoint)

            qr_base64 = result.get("qrcode")
            if qr_base64:
                logger.success("✅ QR code obtenido")
                return qr_base64
            else:
                logger.warning("⚠️  No hay QR disponible (ya conectado?)")
                return None

        except Exception as e:
            logger.error(f"❌ Error obteniendo QR: {e}")
            return None

    def logout_instance(self) -> bool:
        """
        Desconecta la instancia de WhatsApp.

        Returns:
            True si desconectó exitosamente
        """
        try:
            endpoint = f"/instance/logout/{self.config.instance_name}"
            result = self._request("DELETE", endpoint)

            logger.success("✅ Instancia desconectada")
            return True

        except Exception as e:
            logger.error(f"❌ Error desconectando instancia: {e}")
            return False


# ============================================
# MOCK CLIENT
# ============================================

class MockEvolutionClient:
    """
    Cliente mock para desarrollo sin Evolution API.
    """

    def __init__(self, config: EvolutionConfig):
        self.config = config
        logger.warning("⚠️  Usando MockEvolutionClient (sin Evolution API real)")

    def send_text(
        self,
        phone: str,
        message: str,
        delay: int = 1000
    ) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: WhatsApp enviado a {phone}")
        logger.info(f"📝 Mensaje: {message[:100]}...")
        return {
            "success": True,
            "message_id": "mock-msg-123",
            "phone": phone
        }

    def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image"
    ) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: {media_type} enviado a {phone}")
        if caption:
            logger.info(f"📝 Caption: {caption}")
        return {
            "success": True,
            "message_id": "mock-media-123",
            "phone": phone
        }

    def send_image_file(
        self,
        phone: str,
        image_path: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: Imagen {image_path} enviada a {phone}")
        return {
            "success": True,
            "message_id": "mock-img-123",
            "phone": phone
        }

    def send_with_buttons(
        self,
        phone: str,
        message: str,
        buttons: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: Mensaje con {len(buttons)} botones enviado a {phone}")
        for btn in buttons:
            logger.info(f"  🔘 {btn.get('text')}")
        return {
            "success": True,
            "message_id": "mock-buttons-123"
        }

    def get_instance_status(self) -> Dict[str, Any]:
        logger.info("🔧 Mock: Instancia conectada")
        return {
            "connected": True,
            "state": "open",
            "instance": self.config.instance_name
        }

    def get_qr_code(self) -> Optional[str]:
        logger.info("🔧 Mock: QR code mock")
        return "mock-qr-base64-data"

    def logout_instance(self) -> bool:
        logger.info("🔧 Mock: Instancia desconectada")
        return True


# ============================================
# FACTORY FUNCTION
# ============================================

def create_evolution_client(
    base_url: str,
    api_key: str,
    instance_name: str = "portero",
    use_mock: bool = False
) -> Union[EvolutionClient, MockEvolutionClient]:
    """
    Factory para crear cliente Evolution API.

    Args:
        base_url: URL base de Evolution API (ej: http://localhost:8080)
        api_key: API Key de Evolution
        instance_name: Nombre de la instancia
        use_mock: Usar mock en lugar de cliente real

    Returns:
        Cliente Evolution (real o mock)
    """
    config = EvolutionConfig(
        base_url=base_url,
        api_key=api_key,
        instance_name=instance_name
    )

    if use_mock:
        return MockEvolutionClient(config)
    else:
        return EvolutionClient(config)

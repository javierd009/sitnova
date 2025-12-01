"""
Cliente para control de acceso Hikvision via ISAPI.

Implementa endpoints estándar de ISAPI para:
- Abrir puertas/portones
- Consultar estado de dispositivos
- Configurar accesos
- Suscribirse a eventos

Basado en Hikvision ISAPI specification v2.0
"""
import requests
from requests.auth import HTTPDigestAuth
from typing import Optional, Dict, Any, List, Union
from loguru import logger
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from datetime import datetime


@dataclass
class HikvisionConfig:
    """Configuración del dispositivo Hikvision"""
    host: str
    port: int = 80
    username: str = "admin"
    password: str = ""
    timeout: int = 10
    use_https: bool = False

    @property
    def base_url(self) -> str:
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.host}:{self.port}/ISAPI"


class HikvisionClient:
    """
    Cliente para control de acceso Hikvision.

    Endpoints principales:
    - /AccessControl/RemoteControl/door/{doorID} - Abrir puerta
    - /AccessControl/Door/{doorID}/status - Estado de puerta
    - /System/deviceInfo - Información del dispositivo
    - /Event/notification/alertStream - Stream de eventos
    """

    def __init__(self, config: HikvisionConfig):
        """
        Inicializa cliente Hikvision.

        Args:
            config: Configuración del dispositivo
        """
        self.config = config
        self.auth = HTTPDigestAuth(config.username, config.password)
        self.session = requests.Session()
        self.session.auth = self.auth

        # Deshabilitar warnings SSL si usa HTTPS sin verificación
        if config.use_https:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[str] = None,
        params: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> requests.Response:
        """
        Ejecuta request HTTP a ISAPI.

        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint relativo (ej: /System/deviceInfo)
            data: XML data para POST/PUT
            params: Query parameters
            timeout: Timeout en segundos

        Returns:
            Response object

        Raises:
            requests.RequestException: Error en request
        """
        url = f"{self.config.base_url}{endpoint}"
        timeout = timeout or self.config.timeout

        headers = {
            "Content-Type": "application/xml",
            "Accept": "application/xml"
        }

        try:
            response = self.session.request(
                method=method,
                url=url,
                data=data,
                params=params,
                headers=headers,
                timeout=timeout,
                verify=False  # Para desarrollo; cambiar en producción
            )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            logger.error(f"❌ Error en request ISAPI: {method} {endpoint} - {e}")
            raise

    def get_device_info(self) -> Dict[str, Any]:
        """
        Obtiene información del dispositivo.

        Returns:
            Dict con: deviceName, model, serialNumber, firmwareVersion
        """
        try:
            response = self._request("GET", "/System/deviceInfo")

            # Parsear XML
            root = ET.fromstring(response.content)

            info = {
                "deviceName": root.findtext("deviceName", "Unknown"),
                "model": root.findtext("model", "Unknown"),
                "serialNumber": root.findtext("serialNumber", "Unknown"),
                "firmwareVersion": root.findtext("firmwareVersion", "Unknown"),
                "macAddress": root.findtext("macAddress", "Unknown"),
            }

            logger.success(f"✅ Device info: {info['model']} - {info['serialNumber']}")
            return info

        except Exception as e:
            logger.error(f"❌ Error obteniendo device info: {e}")
            return {"error": str(e)}

    def open_door(self, door_id: int = 1) -> Dict[str, Any]:
        """
        Abre una puerta/portón.

        Endpoint: POST /AccessControl/RemoteControl/door/{doorID}

        Args:
            door_id: ID de la puerta (default: 1)

        Returns:
            Dict con status y mensaje
        """
        try:
            # XML para abrir puerta
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<RemoteControlDoor>
    <cmd>open</cmd>
</RemoteControlDoor>"""

            endpoint = f"/AccessControl/RemoteControl/door/{door_id}"

            response = self._request("PUT", endpoint, data=xml_data)

            # Verificar respuesta
            if response.status_code == 200:
                logger.success(f"✅ Puerta {door_id} abierta exitosamente")
                return {
                    "success": True,
                    "door_id": door_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"⚠️  Respuesta inesperada: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Status code: {response.status_code}"
                }

        except requests.RequestException as e:
            logger.error(f"❌ Error abriendo puerta {door_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def close_door(self, door_id: int = 1) -> Dict[str, Any]:
        """
        Cierra una puerta/portón.

        Args:
            door_id: ID de la puerta

        Returns:
            Dict con status
        """
        try:
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<RemoteControlDoor>
    <cmd>close</cmd>
</RemoteControlDoor>"""

            endpoint = f"/AccessControl/RemoteControl/door/{door_id}"
            response = self._request("PUT", endpoint, data=xml_data)

            if response.status_code == 200:
                logger.success(f"✅ Puerta {door_id} cerrada")
                return {"success": True, "door_id": door_id}
            else:
                return {"success": False, "error": f"Status: {response.status_code}"}

        except Exception as e:
            logger.error(f"❌ Error cerrando puerta {door_id}: {e}")
            return {"success": False, "error": str(e)}

    def get_door_status(self, door_id: int = 1) -> Dict[str, Any]:
        """
        Obtiene estado de una puerta.

        Args:
            door_id: ID de la puerta

        Returns:
            Dict con: status (open/closed), locked, alarm
        """
        try:
            endpoint = f"/AccessControl/Door/{door_id}/status"
            response = self._request("GET", endpoint)

            root = ET.fromstring(response.content)

            status = {
                "door_id": door_id,
                "status": root.findtext("doorStatus", "unknown"),
                "locked": root.findtext("lockStatus", "unknown"),
                "alarm": root.findtext("alarmStatus", "normal"),
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"🚪 Puerta {door_id}: {status['status']}")
            return status

        except Exception as e:
            logger.error(f"❌ Error obteniendo estado puerta {door_id}: {e}")
            return {"error": str(e)}

    def get_all_doors(self) -> List[Dict[str, Any]]:
        """
        Lista todas las puertas configuradas.

        Returns:
            Lista de puertas con su configuración
        """
        try:
            endpoint = "/AccessControl/Door/capabilities"
            response = self._request("GET", endpoint)

            root = ET.fromstring(response.content)

            doors = []
            for door in root.findall(".//Door"):
                door_info = {
                    "id": door.findtext("doorID"),
                    "name": door.findtext("doorName"),
                    "enabled": door.findtext("enabled") == "true"
                }
                doors.append(door_info)

            logger.info(f"🚪 Total puertas: {len(doors)}")
            return doors

        except Exception as e:
            logger.warning(f"⚠️  Error listando puertas: {e}")
            return []

    def trigger_alarm_output(self, output_id: int = 1, duration: int = 5) -> Dict[str, Any]:
        """
        Activa salida de alarma (útil para sirenas, luces, etc.).

        Args:
            output_id: ID de la salida
            duration: Duración en segundos

        Returns:
            Dict con status
        """
        try:
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<IOPortData>
    <outputState>high</outputState>
    <delayTime>{duration}</delayTime>
</IOPortData>"""

            endpoint = f"/System/IO/outputs/{output_id}/trigger"
            response = self._request("PUT", endpoint, data=xml_data)

            if response.status_code == 200:
                logger.success(f"✅ Alarma {output_id} activada por {duration}s")
                return {"success": True, "output_id": output_id, "duration": duration}
            else:
                return {"success": False, "error": f"Status: {response.status_code}"}

        except Exception as e:
            logger.error(f"❌ Error activando alarma: {e}")
            return {"success": False, "error": str(e)}

    def health_check(self) -> bool:
        """
        Verifica conectividad con el dispositivo.

        Returns:
            True si conectado
        """
        try:
            response = self._request("GET", "/System/status", timeout=5)
            logger.success("✅ Hikvision device reachable")
            return response.status_code == 200

        except Exception as e:
            logger.error(f"❌ Hikvision device unreachable: {e}")
            return False


# ============================================
# MOCK CLIENT (Para desarrollo sin hardware)
# ============================================

class MockHikvisionClient:
    """
    Cliente mock para desarrollo sin hardware Hikvision.
    """

    def __init__(self, config: HikvisionConfig):
        self.config = config
        logger.warning("⚠️  Usando MockHikvisionClient (sin hardware real)")

    def get_device_info(self) -> Dict[str, Any]:
        logger.info("🔧 Mock: Retornando device info")
        return {
            "deviceName": "Mock Hikvision ACS",
            "model": "DS-K2604",
            "serialNumber": "MOCK-12345",
            "firmwareVersion": "V4.3.0",
            "macAddress": "00:11:22:33:44:55"
        }

    def open_door(self, door_id: int = 1) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: Abriendo puerta {door_id}")
        return {
            "success": True,
            "door_id": door_id,
            "timestamp": datetime.now().isoformat()
        }

    def close_door(self, door_id: int = 1) -> Dict[str, Any]:
        logger.info(f"🔧 Mock: Cerrando puerta {door_id}")
        return {"success": True, "door_id": door_id}

    def get_door_status(self, door_id: int = 1) -> Dict[str, Any]:
        logger.info(f"🔧 Mock: Estado puerta {door_id}")
        return {
            "door_id": door_id,
            "status": "closed",
            "locked": "locked",
            "alarm": "normal",
            "timestamp": datetime.now().isoformat()
        }

    def get_all_doors(self) -> List[Dict[str, Any]]:
        logger.info("🔧 Mock: Listando puertas")
        return [
            {"id": "1", "name": "Portón Principal", "enabled": True},
            {"id": "2", "name": "Portón Peatonal", "enabled": True}
        ]

    def trigger_alarm_output(self, output_id: int = 1, duration: int = 5) -> Dict[str, Any]:
        logger.info(f"🔧 Mock: Activando alarma {output_id} por {duration}s")
        return {"success": True, "output_id": output_id, "duration": duration}

    def health_check(self) -> bool:
        logger.success("✅ Mock: Device OK")
        return True


# ============================================
# FACTORY FUNCTION
# ============================================

def create_hikvision_client(
    host: str,
    username: str = "admin",
    password: str = "",
    port: int = 80,
    use_mock: bool = False
) -> Union[HikvisionClient, MockHikvisionClient]:
    """
    Factory para crear cliente Hikvision.

    Args:
        host: IP del dispositivo
        username: Usuario ISAPI
        password: Contraseña
        port: Puerto (default: 80)
        use_mock: Usar mock en lugar de cliente real

    Returns:
        Cliente Hikvision (real o mock)
    """
    config = HikvisionConfig(
        host=host,
        port=port,
        username=username,
        password=password
    )

    if use_mock:
        return MockHikvisionClient(config)
    else:
        return HikvisionClient(config)

"""
Cliente para FreePBX/Asterisk via AMI (Asterisk Manager Interface).

Permite:
- Originar llamadas a residentes
- Capturar respuestas DTMF (1=autorizar, 2=denegar)
- Monitorear estado de llamadas
- Colgar llamadas
"""
import socket
import threading
import time
from typing import Optional, Dict, Any, Callable, Union
from loguru import logger
from dataclasses import dataclass
import re
from queue import Queue


@dataclass
class FreePBXConfig:
    """Configuración de FreePBX/Asterisk"""
    host: str
    port: int = 5038  # Puerto AMI por defecto
    username: str = "admin"
    secret: str = ""
    timeout: int = 10


class AMIClient:
    """
    Cliente AMI (Asterisk Manager Interface) para FreePBX.

    Protocol:
    - Conexión TCP al puerto 5038
    - Autenticación con username/secret
    - Mensajes en formato key: value
    - Eventos asíncronos del servidor
    """

    def __init__(self, config: FreePBXConfig):
        """
        Inicializa cliente AMI.

        Args:
            config: Configuración de FreePBX
        """
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.authenticated = False

        # Para recibir eventos asíncronos
        self.event_queue = Queue()
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False

    def connect(self) -> bool:
        """
        Conecta al servidor AMI.

        Returns:
            True si conectó exitosamente
        """
        try:
            logger.info(f"📞 Conectando a FreePBX AMI: {self.config.host}:{self.config.port}")

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))

            # Leer banner de bienvenida
            banner = self._read_response()
            logger.debug(f"AMI Banner: {banner.get('Response', 'Unknown')}")

            self.connected = True
            logger.success("✅ Conectado a AMI")

            # Autenticar
            return self.authenticate()

        except Exception as e:
            logger.error(f"❌ Error conectando a AMI: {e}")
            return False

    def authenticate(self) -> bool:
        """
        Autentica con el servidor AMI.

        Returns:
            True si autenticación exitosa
        """
        try:
            # Enviar acción de login
            action = {
                "Action": "Login",
                "Username": self.config.username,
                "Secret": self.config.secret
            }

            response = self._send_action(action)

            if response.get("Response") == "Success":
                logger.success("✅ Autenticado en AMI")
                self.authenticated = True

                # Iniciar listener de eventos
                self._start_event_listener()

                return True
            else:
                logger.error(f"❌ Autenticación fallida: {response.get('Message')}")
                return False

        except Exception as e:
            logger.error(f"❌ Error en autenticación: {e}")
            return False

    def _send_action(self, action: Dict[str, str]) -> Dict[str, Any]:
        """
        Envía una acción al servidor AMI.

        Args:
            action: Dict con Action y parámetros

        Returns:
            Dict con la respuesta
        """
        if not self.socket:
            raise Exception("No hay conexión AMI")

        # Construir mensaje
        message = ""
        for key, value in action.items():
            message += f"{key}: {value}\r\n"
        message += "\r\n"  # Línea vacía marca fin de acción

        # Enviar
        self.socket.sendall(message.encode('utf-8'))

        # Leer respuesta
        return self._read_response()

    def _read_response(self) -> Dict[str, Any]:
        """
        Lee una respuesta del servidor AMI.

        Returns:
            Dict con los campos de la respuesta
        """
        response = {}
        buffer = ""

        while True:
            try:
                chunk = self.socket.recv(4096).decode('utf-8')
                if not chunk:
                    break

                buffer += chunk

                # Buscar doble \r\n que marca fin de mensaje
                if "\r\n\r\n" in buffer:
                    lines = buffer.split("\r\n\r\n")[0].split("\r\n")

                    for line in lines:
                        if ": " in line:
                            key, value = line.split(": ", 1)
                            response[key.strip()] = value.strip()

                    break

            except socket.timeout:
                logger.warning("⚠️  Timeout leyendo respuesta AMI")
                break

        return response

    def _start_event_listener(self):
        """Inicia thread para escuchar eventos asíncronos."""
        self.running = True
        self.listener_thread = threading.Thread(target=self._event_listener, daemon=True)
        self.listener_thread.start()
        logger.info("🎧 Event listener iniciado")

    def _event_listener(self):
        """Loop que escucha eventos del servidor."""
        while self.running and self.connected:
            try:
                event = self._read_response()
                if event:
                    self.event_queue.put(event)
                    logger.debug(f"📨 Evento AMI: {event.get('Event', 'Unknown')}")
            except Exception as e:
                logger.error(f"❌ Error en event listener: {e}")
                time.sleep(1)

    def originate_call(
        self,
        extension: str,
        context: str = "from-internal",
        caller_id: str = "Portero <1000>",
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Origina una llamada a una extensión.

        Args:
            extension: Extensión a llamar (ej: "101")
            context: Contexto de marcado
            caller_id: Caller ID a mostrar
            timeout: Timeout en segundos

        Returns:
            Dict con resultado
        """
        logger.info(f"📞 Originando llamada a extensión {extension}")

        try:
            action = {
                "Action": "Originate",
                "Channel": f"Local/{extension}@{context}",
                "Context": context,
                "Exten": extension,
                "Priority": "1",
                "CallerID": caller_id,
                "Timeout": str(timeout * 1000),  # En milisegundos
                "Async": "true"  # No esperar a que conteste
            }

            response = self._send_action(action)

            if response.get("Response") == "Success":
                logger.success(f"✅ Llamada originada a {extension}")
                return {
                    "success": True,
                    "extension": extension,
                    "actionid": response.get("ActionID")
                }
            else:
                logger.error(f"❌ Error originando llamada: {response.get('Message')}")
                return {
                    "success": False,
                    "error": response.get("Message")
                }

        except Exception as e:
            logger.error(f"❌ Excepción originando llamada: {e}")
            return {"success": False, "error": str(e)}

    def wait_for_dtmf(self, timeout: int = 30) -> Optional[str]:
        """
        Espera por input DTMF del usuario.

        Args:
            timeout: Tiempo máximo de espera

        Returns:
            Dígito DTMF recibido o None
        """
        logger.info("🎹 Esperando DTMF...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Revisar eventos en la cola
                if not self.event_queue.empty():
                    event = self.event_queue.get(timeout=1)

                    # Buscar evento DTMF
                    if event.get("Event") == "DTMF":
                        digit = event.get("Digit")
                        logger.info(f"🎹 DTMF recibido: {digit}")
                        return digit

                time.sleep(0.1)

            except Exception as e:
                logger.error(f"❌ Error esperando DTMF: {e}")
                break

        logger.warning("⏱️  Timeout esperando DTMF")
        return None

    def hangup(self, channel: str) -> bool:
        """
        Cuelga un canal específico.

        Args:
            channel: Nombre del canal

        Returns:
            True si colgó exitosamente
        """
        try:
            action = {
                "Action": "Hangup",
                "Channel": channel
            }

            response = self._send_action(action)

            if response.get("Response") == "Success":
                logger.success(f"✅ Canal {channel} colgado")
                return True
            else:
                logger.error(f"❌ Error colgando: {response.get('Message')}")
                return False

        except Exception as e:
            logger.error(f"❌ Excepción colgando: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión AMI."""
        try:
            if self.authenticated:
                # Enviar Logoff
                action = {"Action": "Logoff"}
                self._send_action(action)

            self.running = False

            if self.socket:
                self.socket.close()

            logger.info("📞 Desconectado de AMI")

        except Exception as e:
            logger.error(f"❌ Error desconectando: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# ============================================
# MOCK CLIENT
# ============================================

class MockFreePBXClient:
    """
    Cliente mock para desarrollo sin FreePBX.
    """

    def __init__(self, config: FreePBXConfig):
        self.config = config
        self.connected = False
        self.authenticated = False
        logger.warning("⚠️  Usando MockFreePBXClient (sin FreePBX real)")

    def connect(self) -> bool:
        logger.info("🔧 Mock: Conectando a FreePBX...")
        self.connected = True
        self.authenticated = True
        return True

    def authenticate(self) -> bool:
        logger.success("🔧 Mock: Autenticado")
        return True

    def originate_call(
        self,
        extension: str,
        context: str = "from-internal",
        caller_id: str = "Portero <1000>",
        timeout: int = 30
    ) -> Dict[str, Any]:
        logger.success(f"🔧 Mock: Llamando a extensión {extension}")
        return {
            "success": True,
            "extension": extension,
            "actionid": "mock-action-123"
        }

    def wait_for_dtmf(self, timeout: int = 30) -> Optional[str]:
        logger.info("🔧 Mock: Simulando DTMF...")
        time.sleep(2)  # Simular espera
        dtmf = "1"  # Simular autorización
        logger.success(f"🔧 Mock: DTMF recibido: {dtmf}")
        return dtmf

    def hangup(self, channel: str) -> bool:
        logger.info(f"🔧 Mock: Colgando canal {channel}")
        return True

    def disconnect(self):
        logger.info("🔧 Mock: Desconectado")
        self.connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


# ============================================
# FACTORY FUNCTION
# ============================================

def create_freepbx_client(
    host: str,
    username: str = "admin",
    secret: str = "",
    port: int = 5038,
    use_mock: bool = False
) -> Union[AMIClient, MockFreePBXClient]:
    """
    Factory para crear cliente FreePBX.

    Args:
        host: IP del servidor FreePBX
        username: Usuario AMI
        secret: Contraseña AMI
        port: Puerto AMI (default: 5038)
        use_mock: Usar mock en lugar de cliente real

    Returns:
        Cliente FreePBX (real o mock)
    """
    config = FreePBXConfig(
        host=host,
        port=port,
        username=username,
        secret=secret
    )

    if use_mock:
        return MockFreePBXClient(config)
    else:
        return AMIClient(config)

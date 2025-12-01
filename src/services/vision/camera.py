"""
Módulo para conexión y captura desde cámaras RTSP (Hikvision).
Maneja streaming de video y captura de frames.
"""
import cv2
import numpy as np
from loguru import logger
from datetime import datetime
from pathlib import Path
from typing import Optional,  Tuple, Optional


class RTSPCamera:
    """Cliente para cámaras RTSP"""

    def __init__(self, rtsp_url: str, camera_id: str = "default"):
        """
        Inicializa conexión a cámara RTSP.

        Args:
            rtsp_url: URL RTSP completa (ej: rtsp://admin:pass@192.168.1.100:554/Streaming/Channels/101)
            camera_id: Identificador de la cámara
        """
        self.rtsp_url = rtsp_url
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_connected = False

    def connect(self, timeout: int = 10) -> bool:
        """
        Conecta a la cámara RTSP.

        Args:
            timeout: Timeout en segundos

        Returns:
            True si conectó exitosamente
        """
        logger.info(f"📹 Conectando a cámara {self.camera_id}: {self.rtsp_url}")

        try:
            # Crear VideoCapture con opciones
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)

            # Configurar buffer bajo para reducir latencia
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Verificar conexión
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.is_connected = True
                    height, width = frame.shape[:2]
                    logger.success(f"✅ Conectado a {self.camera_id} ({width}x{height})")
                    return True

            logger.error(f"❌ No se pudo conectar a {self.camera_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Error conectando a cámara: {e}")
            return False

    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Captura un frame de la cámara.

        Returns:
            Frame como numpy array (BGR) o None si falla
        """
        if not self.is_connected or not self.cap:
            logger.error("❌ Cámara no conectada")
            return None

        try:
            ret, frame = self.cap.read()

            if ret and frame is not None:
                return frame

            logger.warning("⚠️  Frame vacío")
            return None

        except Exception as e:
            logger.error(f"❌ Error capturando frame: {e}")
            return None

    def capture_and_save(self, output_dir: str = "data/images") -> Optional[str]:
        """
        Captura un frame y lo guarda en disco.

        Args:
            output_dir: Directorio donde guardar

        Returns:
            Path del archivo guardado o None
        """
        frame = self.capture_frame()

        if frame is None:
            return None

        try:
            # Crear directorio si no existe
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Generar nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.camera_id}_{timestamp}.jpg"
            filepath = Path(output_dir) / filename

            # Guardar imagen
            cv2.imwrite(str(filepath), frame)

            logger.info(f"💾 Imagen guardada: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Error guardando imagen: {e}")
            return None

    def disconnect(self):
        """Cierra la conexión a la cámara"""
        if self.cap:
            self.cap.release()
            self.is_connected = False
            logger.info(f"📹 Desconectado de {self.camera_id}")

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.disconnect()


# ============================================
# HELPER FUNCTIONS
# ============================================

def capture_from_camera(rtsp_url: str, save_path: Optional[str] = None) -> Optional[np.ndarray]:
    """
    Helper rápido para capturar un frame.

    Args:
        rtsp_url: URL RTSP de la cámara
        save_path: Path opcional para guardar

    Returns:
        Frame capturado o None
    """
    with RTSPCamera(rtsp_url) as camera:
        if not camera.is_connected:
            return None

        frame = camera.capture_frame()

        if frame is not None and save_path:
            cv2.imwrite(save_path, frame)
            logger.info(f"💾 Frame guardado en: {save_path}")

        return frame


def test_camera_connection(rtsp_url: str) -> bool:
    """
    Test rápido de conexión a cámara.

    Args:
        rtsp_url: URL RTSP

    Returns:
        True si la cámara responde
    """
    logger.info(f"🧪 Testing conexión a: {rtsp_url}")

    with RTSPCamera(rtsp_url) as camera:
        if camera.is_connected:
            frame = camera.capture_frame()
            if frame is not None:
                logger.success("✅ Test exitoso - cámara funcional")
                return True

    logger.error("❌ Test fallido - verificar URL y credenciales")
    return False


# ============================================
# MOCK CAMERA (Para desarrollo sin hardware)
# ============================================

class MockCamera(RTSPCamera):
    """Cámara mock para testing sin hardware"""

    def connect(self, timeout: int = 10) -> bool:
        """Mock connection"""
        logger.info(f"🎭 Mock camera {self.camera_id} conectada")
        self.is_connected = True
        return True

    def capture_frame(self) -> Optional[np.ndarray]:
        """Genera frame mock"""
        if not self.is_connected:
            return None

        # Crear imagen negra con texto
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            img,
            f"MOCK CAMERA: {self.camera_id}",
            (50, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2
        )

        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(
            img,
            timestamp,
            (250, 300),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        return img

    def disconnect(self):
        """Mock disconnect"""
        self.is_connected = False
        logger.info(f"🎭 Mock camera {self.camera_id} desconectada")

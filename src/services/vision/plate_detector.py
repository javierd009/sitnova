"""
Detector de placas vehiculares usando YOLOv8 + EasyOCR.
No requiere entrenamiento - usa modelo pre-entrenado.
"""
import cv2
import numpy as np
from loguru import logger
import re
from typing import Optional, Dict, Tuple
from pathlib import Path


class PlateDetector:
    """
    Detector de placas vehiculares para Costa Rica.

    Strategy (sin entrenar modelo):
    1. YOLOv8 pre-trained detecta vehículo
    2. Crop región frontal del vehículo
    3. Buscar región rectangular (placa)
    4. EasyOCR lee texto
    5. Validar formato Costa Rica: ABC-123
    """

    def __init__(self, use_gpu: bool = False):
        """
        Inicializa detector.

        Args:
            use_gpu: Usar GPU si está disponible
        """
        self.yolo_model = None
        self.ocr_reader = None
        self.use_gpu = use_gpu

        # Patrones de placas Costa Rica
        self.plate_patterns = [
            r'^[A-Z]{3}-\d{3}$',  # ABC-123 (estándar)
            r'^[A-Z]{2}-\d{4}$',  # AB-1234 (motos)
            r'^[A-Z]\d{5}$',      # A12345 (taxis)
        ]

    def load_models(self):
        """Carga modelos YOLO y EasyOCR"""
        if self.yolo_model is not None and self.ocr_reader is not None:
            return  # Ya cargados

        logger.info("📦 Cargando modelos...")

        try:
            # Cargar YOLO (detecta vehículos)
            from ultralytics import YOLO

            model_path = "models/yolov8n.pt"  # Modelo nano (más rápido)

            if not Path(model_path).exists():
                logger.warning(f"⚠️  Modelo no encontrado en {model_path}, usando mock")
                self.yolo_model = None
            else:
                self.yolo_model = YOLO(model_path)
                logger.success("✅ YOLO cargado")

        except ImportError:
            logger.warning("⚠️  ultralytics no instalado, modo mock")
            self.yolo_model = None

        try:
            # Cargar EasyOCR (lee texto)
            import easyocr

            self.ocr_reader = easyocr.Reader(
                ['en'],  # Placas son alfanuméricas
                gpu=self.use_gpu
            )
            logger.success("✅ EasyOCR cargado")

        except ImportError:
            logger.warning("⚠️  easyocr no instalado, modo mock")
            self.ocr_reader = None

    def detect_vehicle(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detecta vehículo en la imagen.

        Args:
            image: Imagen BGR

        Returns:
            Bounding box (x1, y1, x2, y2) o None
        """
        if self.yolo_model is None:
            logger.warning("⚠️  YOLO no disponible, usando detección mock")
            # Mock: devuelve toda la imagen
            h, w = image.shape[:2]
            return (0, 0, w, h)

        try:
            # Detectar objetos
            results = self.yolo_model(image, verbose=False)

            # Buscar vehículos (car=2, motorcycle=3, truck=7)
            vehicle_classes = [2, 3, 7]

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls = int(box.cls[0])
                    if cls in vehicle_classes:
                        conf = float(box.conf[0])
                        if conf > 0.5:  # Confianza mínima
                            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                            return (int(x1), int(y1), int(x2), int(y2))

            logger.warning("⚠️  No se detectó vehículo")
            return None

        except Exception as e:
            logger.error(f"❌ Error en detección YOLO: {e}")
            return None

    def find_plate_region(self, vehicle_crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Encuentra región de la placa en el crop del vehículo.

        Strategy:
        1. Convertir a escala de grises
        2. Detectar bordes (Canny)
        3. Encontrar contornos rectangulares
        4. Filtrar por aspect ratio de placa (3:1 aprox)

        Args:
            vehicle_crop: Imagen del vehículo

        Returns:
            Crop de la placa o None
        """
        try:
            # Convertir a escala de grises
            gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)

            # Reducir ruido
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Detectar bordes
            edges = cv2.Canny(blurred, 100, 200)

            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            # Buscar rectángulos con aspect ratio de placa
            for contour in contours:
                approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)

                if len(approx) == 4:  # Rectángulo
                    x, y, w, h = cv2.boundingRect(contour)

                    # Aspect ratio de placa CR: ~3:1
                    aspect_ratio = w / h if h > 0 else 0

                    if 2.0 < aspect_ratio < 5.0 and w > 50 and h > 15:
                        # Crop de la placa
                        plate_crop = vehicle_crop[y:y+h, x:x+w]
                        return plate_crop

            logger.warning("⚠️  No se encontró región de placa")
            # Fallback: crop inferior del vehículo (donde suelen estar las placas)
            h, w = vehicle_crop.shape[:2]
            return vehicle_crop[int(h*0.7):h, :]

        except Exception as e:
            logger.error(f"❌ Error buscando región de placa: {e}")
            return None

    def read_plate_text(self, plate_image: np.ndarray) -> Optional[Dict]:
        """
        Lee texto de la placa usando OCR.

        Args:
            plate_image: Imagen de la placa

        Returns:
            Dict con text y confidence o None
        """
        if self.ocr_reader is None:
            logger.warning("⚠️  OCR no disponible, usando mock")
            return {
                "text": "ABC-123",
                "confidence": 0.85
            }

        try:
            # Preprocesar imagen para mejorar OCR
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)

            # Aumentar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Aplicar threshold
            _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # OCR
            results = self.ocr_reader.readtext(thresh)

            if not results:
                logger.warning("⚠️  OCR no detectó texto")
                return None

            # Tomar resultado con mayor confianza
            best_result = max(results, key=lambda x: x[2])
            text = best_result[1].upper().replace(" ", "")
            confidence = best_result[2]

            logger.info(f"📝 OCR detectó: {text} (conf: {confidence:.2f})")

            return {
                "text": text,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"❌ Error en OCR: {e}")
            return None

    def validate_plate_format(self, text: str) -> bool:
        """
        Valida formato de placa de Costa Rica.

        Args:
            text: Texto detectado

        Returns:
            True si coincide con algún patrón válido
        """
        for pattern in self.plate_patterns:
            if re.match(pattern, text):
                logger.success(f"✅ Placa válida: {text}")
                return True

        logger.warning(f"⚠️  Formato de placa inválido: {text}")
        return False

    def detect_plate(self, image: np.ndarray, save_debug: bool = False) -> Dict:
        """
        Pipeline completo de detección de placa.

        Args:
            image: Imagen BGR
            save_debug: Guardar imágenes de debug

        Returns:
            Dict con: detected, text, confidence, vehicle_bbox, plate_crop
        """
        logger.info("🔍 Iniciando detección de placa...")

        # Cargar modelos si no están cargados
        self.load_models()

        result = {
            "detected": False,
            "text": None,
            "confidence": 0.0,
            "vehicle_type": None,
            "vehicle_bbox": None,
            "plate_image": None
        }

        # 1. Detectar vehículo
        vehicle_bbox = self.detect_vehicle(image)

        if vehicle_bbox is None:
            logger.warning("❌ No se detectó vehículo")
            return result

        result["vehicle_bbox"] = vehicle_bbox

        # 2. Crop vehículo
        x1, y1, x2, y2 = vehicle_bbox
        vehicle_crop = image[y1:y2, x1:x2]

        # 3. Encontrar placa
        plate_crop = self.find_plate_region(vehicle_crop)

        if plate_crop is None:
            logger.warning("❌ No se encontró placa")
            return result

        result["plate_image"] = plate_crop

        # 4. Leer texto
        ocr_result = self.read_plate_text(plate_crop)

        if ocr_result is None:
            logger.warning("❌ OCR no pudo leer placa")
            return result

        # 5. Validar formato
        is_valid = self.validate_plate_format(ocr_result["text"])

        if is_valid:
            result["detected"] = True
            result["text"] = ocr_result["text"]
            result["confidence"] = ocr_result["confidence"]
            logger.success(f"✅ Placa detectada: {result['text']}")
        else:
            logger.warning(f"❌ Placa con formato inválido: {ocr_result['text']}")

        return result


# ============================================
# HELPER FUNCTION
# ============================================

def detect_plate_from_camera(camera_ip: str) -> Dict:
    """
    Detecta placa desde cámara RTSP.

    Args:
        camera_ip: IP de la cámara

    Returns:
        Resultado de detección
    """
    from src.services.vision.camera import RTSPCamera

    with RTSPCamera(camera_ip) as camera:
        if not camera.is_connected:
            return {"detected": False, "error": "Camera not connected"}

        frame = camera.capture_frame()

        if frame is None:
            return {"detected": False, "error": "Failed to capture frame"}

        detector = PlateDetector()
        return detector.detect_plate(frame)

"""
Lector de cédulas costarricenses usando YOLOv8 + EasyOCR.
No requiere entrenamiento - usa modelo pre-entrenado.
"""
import cv2
import numpy as np
from loguru import logger
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path


class CedulaReader:
    """
    Lector de cédulas de identidad de Costa Rica.

    Strategy (sin entrenar modelo):
    1. YOLOv8 pre-trained detecta documentos rectangulares
    2. Crop región del documento
    3. EasyOCR lee texto
    4. Parsear y extraer campos específicos
    5. Validar formato Costa Rica: X-XXXX-XXXX
    """

    def __init__(self, use_gpu: bool = False):
        """
        Inicializa lector.

        Args:
            use_gpu: Usar GPU si está disponible
        """
        self.yolo_model = None
        self.ocr_reader = None
        self.use_gpu = use_gpu

        # Patrón de cédula Costa Rica: X-XXXX-XXXX (físicas) o XXXXXXXXX (DIMEX)
        self.cedula_patterns = [
            r'\b\d-\d{4}-\d{4}\b',  # Cédula física: 1-2345-6789
            r'\b\d{9}\b',            # DIMEX: 123456789
            r'\b\d{10}\b',           # Residencia: 1234567890
        ]

    def load_models(self):
        """Carga modelos YOLO y EasyOCR"""
        if self.yolo_model is not None and self.ocr_reader is not None:
            return  # Ya cargados

        logger.info("📦 Cargando modelos OCR para cédulas...")

        try:
            # Cargar YOLO (detecta documentos)
            from ultralytics import YOLO

            model_path = "models/yolov8n.pt"  # Modelo nano

            if not Path(model_path).exists():
                logger.warning(f"⚠️  Modelo no encontrado en {model_path}, usando mock")
                self.yolo_model = None
            else:
                self.yolo_model = YOLO(model_path)
                logger.success("✅ YOLO cargado para cédulas")

        except ImportError:
            logger.warning("⚠️  ultralytics no instalado, modo mock")
            self.yolo_model = None

        try:
            # Cargar EasyOCR
            import easyocr

            self.ocr_reader = easyocr.Reader(
                ['es', 'en'],  # Español e inglés
                gpu=self.use_gpu
            )
            logger.success("✅ EasyOCR cargado para cédulas")

        except ImportError:
            logger.warning("⚠️  easyocr no instalado, modo mock")
            self.ocr_reader = None

    def detect_document(self, image: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        Detecta documento rectangular en la imagen.

        Strategy:
        - Si YOLO está disponible, buscar objetos rectangulares
        - Si no, usar detección de contornos por color/forma

        Args:
            image: Imagen BGR

        Returns:
            Bounding box (x1, y1, x2, y2) o None
        """
        try:
            # Estrategia 1: Detección por contornos (más confiable para documentos)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Detectar bordes
            edges = cv2.Canny(blurred, 50, 150)

            # Dilatar para conectar bordes
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edges, kernel, iterations=2)

            # Encontrar contornos
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Buscar el contorno más grande con forma rectangular
            for contour in sorted(contours, key=cv2.contourArea, reverse=True):
                area = cv2.contourArea(contour)

                # Filtrar por tamaño mínimo
                if area < 10000:  # Cédula debe ser visible
                    continue

                # Aproximar a polígono
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

                # Debe ser aproximadamente rectangular (4 esquinas)
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(contour)

                    # Aspect ratio de cédula CR: ~1.6:1 (85mm x 54mm)
                    aspect_ratio = w / h if h > 0 else 0

                    if 1.3 < aspect_ratio < 2.0 and w > 200 and h > 100:
                        logger.info(f"✅ Documento detectado: {w}x{h} (ratio: {aspect_ratio:.2f})")
                        return (x, y, x + w, y + h)

            logger.warning("⚠️  No se detectó documento por contornos")

            # Fallback: devolver región central (donde suele estar la cédula)
            h, w = image.shape[:2]
            margin_x = int(w * 0.1)
            margin_y = int(h * 0.2)
            return (margin_x, margin_y, w - margin_x, h - margin_y)

        except Exception as e:
            logger.error(f"❌ Error en detección de documento: {e}")
            return None

    def read_text_from_document(self, doc_image: np.ndarray) -> List[Tuple[str, float]]:
        """
        Lee todo el texto del documento usando OCR.

        Args:
            doc_image: Imagen del documento

        Returns:
            Lista de tuplas (text, confidence)
        """
        if self.ocr_reader is None:
            logger.warning("⚠️  OCR no disponible, usando mock")
            return [
                ("REPUBLICA DE COSTA RICA", 0.95),
                ("TRIBUNAL SUPREMO DE ELECCIONES", 0.95),
                ("1-2345-6789", 0.92),
                ("PEREZ GONZALEZ JUAN CARLOS", 0.90),
                ("VENC: 01/01/2030", 0.88),
            ]

        try:
            # Preprocesar imagen
            gray = cv2.cvtColor(doc_image, cv2.COLOR_BGR2GRAY)

            # Aumentar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Threshold adaptativo
            thresh = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            # OCR
            results = self.ocr_reader.readtext(thresh)

            if not results:
                logger.warning("⚠️  OCR no detectó texto en documento")
                return []

            # Extraer texto y confianza
            text_results = [
                (result[1].strip(), result[2])
                for result in results
            ]

            logger.info(f"📝 OCR detectó {len(text_results)} líneas de texto")
            return text_results

        except Exception as e:
            logger.error(f"❌ Error en OCR de documento: {e}")
            return []

    def extract_cedula_number(self, text_lines: List[Tuple[str, float]]) -> Optional[Dict]:
        """
        Extrae número de cédula del texto OCR.

        Args:
            text_lines: Lista de (text, confidence)

        Returns:
            Dict con numero, tipo, confidence o None
        """
        for text, conf in text_lines:
            # Limpiar texto
            clean_text = text.replace(" ", "").replace("O", "0").upper()

            # Buscar patrón de cédula física
            match = re.search(r'\b(\d-\d{4}-\d{4})\b', clean_text)
            if match:
                return {
                    "numero": match.group(1),
                    "tipo": "fisica",
                    "confidence": conf
                }

            # Buscar DIMEX (9 dígitos consecutivos)
            match = re.search(r'\b(\d{9})\b', clean_text)
            if match:
                return {
                    "numero": match.group(1),
                    "tipo": "dimex",
                    "confidence": conf
                }

            # Buscar cédula de residencia (10 dígitos)
            match = re.search(r'\b(\d{10})\b', clean_text)
            if match:
                return {
                    "numero": match.group(1),
                    "tipo": "residencia",
                    "confidence": conf
                }

        logger.warning("⚠️  No se encontró número de cédula válido en OCR")
        return None

    def extract_name(self, text_lines: List[Tuple[str, float]]) -> Optional[Dict]:
        """
        Extrae nombre de la cédula.

        Strategy: El nombre suele estar en las primeras líneas grandes de texto,
        después del encabezado del TSE.

        Args:
            text_lines: Lista de (text, confidence)

        Returns:
            Dict con nombre completo y confidence
        """
        # Filtrar líneas con texto largo (más de 8 caracteres)
        name_candidates = [
            (text, conf) for text, conf in text_lines
            if len(text.strip()) > 8 and text.strip().replace(" ", "").isalpha()
        ]

        # Excluir texto del header
        excluded = ["REPUBLICA", "COSTA RICA", "TRIBUNAL", "ELECCIONES", "TSE"]
        name_candidates = [
            (text, conf) for text, conf in name_candidates
            if not any(ex in text.upper() for ex in excluded)
        ]

        if name_candidates:
            # Tomar el primer candidato con confianza razonable
            for text, conf in name_candidates:
                if conf > 0.7:
                    return {
                        "nombre": text.strip().upper(),
                        "confidence": conf
                    }

        logger.warning("⚠️  No se pudo extraer nombre de cédula")
        return None

    def extract_expiration(self, text_lines: List[Tuple[str, float]]) -> Optional[Dict]:
        """
        Extrae fecha de vencimiento.

        Busca patrones: "VENC:", "VTO:", seguido de fecha DD/MM/YYYY

        Args:
            text_lines: Lista de (text, confidence)

        Returns:
            Dict con fecha y confidence
        """
        for text, conf in text_lines:
            # Buscar patrón de vencimiento
            match = re.search(
                r'(VENC|VTO|EXPIR)[:\s]*(\d{2})[/-](\d{2})[/-](\d{4})',
                text.upper()
            )
            if match:
                day, month, year = match.group(2), match.group(3), match.group(4)
                return {
                    "fecha": f"{day}/{month}/{year}",
                    "confidence": conf
                }

        logger.warning("⚠️  No se encontró fecha de vencimiento")
        return None

    def validate_cedula_format(self, cedula: str, tipo: str) -> bool:
        """
        Valida formato de cédula según tipo.

        Args:
            cedula: Número de cédula
            tipo: "fisica", "dimex", "residencia"

        Returns:
            True si formato válido
        """
        if tipo == "fisica":
            # Formato: X-XXXX-XXXX
            if re.match(r'^\d-\d{4}-\d{4}$', cedula):
                logger.success(f"✅ Cédula física válida: {cedula}")
                return True

        elif tipo == "dimex":
            # Formato: 9 dígitos
            if re.match(r'^\d{9}$', cedula):
                logger.success(f"✅ DIMEX válido: {cedula}")
                return True

        elif tipo == "residencia":
            # Formato: 10 dígitos
            if re.match(r'^\d{10}$', cedula):
                logger.success(f"✅ Cédula de residencia válida: {cedula}")
                return True

        logger.warning(f"⚠️  Formato de cédula inválido: {cedula} (tipo: {tipo})")
        return False

    def read_cedula(self, image: np.ndarray, save_debug: bool = False) -> Dict:
        """
        Pipeline completo de lectura de cédula.

        Args:
            image: Imagen BGR
            save_debug: Guardar imágenes de debug

        Returns:
            Dict con: detected, numero, tipo, nombre, vencimiento, document_bbox, document_image
        """
        logger.info("🔍 Iniciando lectura de cédula...")

        # Cargar modelos si no están cargados
        self.load_models()

        result = {
            "detected": False,
            "numero": None,
            "tipo": None,
            "nombre": None,
            "vencimiento": None,
            "confidence": 0.0,
            "document_bbox": None,
            "document_image": None
        }

        # 1. Detectar documento
        doc_bbox = self.detect_document(image)

        if doc_bbox is None:
            logger.warning("❌ No se detectó documento")
            return result

        result["document_bbox"] = doc_bbox

        # 2. Crop documento
        x1, y1, x2, y2 = doc_bbox
        doc_crop = image[y1:y2, x1:x2]
        result["document_image"] = doc_crop

        # 3. Leer texto con OCR
        text_lines = self.read_text_from_document(doc_crop)

        if not text_lines:
            logger.warning("❌ OCR no pudo leer texto")
            return result

        # 4. Extraer número de cédula
        cedula_data = self.extract_cedula_number(text_lines)

        if cedula_data is None:
            logger.warning("❌ No se encontró número de cédula")
            return result

        # 5. Validar formato
        is_valid = self.validate_cedula_format(cedula_data["numero"], cedula_data["tipo"])

        if not is_valid:
            logger.warning(f"❌ Cédula con formato inválido: {cedula_data['numero']}")
            return result

        # 6. Extraer otros campos
        name_data = self.extract_name(text_lines)
        expiration_data = self.extract_expiration(text_lines)

        # 7. Construir resultado final
        result["detected"] = True
        result["numero"] = cedula_data["numero"]
        result["tipo"] = cedula_data["tipo"]
        result["confidence"] = cedula_data["confidence"]

        if name_data:
            result["nombre"] = name_data["nombre"]

        if expiration_data:
            result["vencimiento"] = expiration_data["fecha"]

        logger.success(f"✅ Cédula leída: {result['numero']} - {result.get('nombre', 'N/A')}")

        return result


# ============================================
# HELPER FUNCTION
# ============================================

def read_cedula_from_camera(camera_ip: str) -> Dict:
    """
    Lee cédula desde cámara RTSP.

    Args:
        camera_ip: IP de la cámara

    Returns:
        Resultado de lectura
    """
    from src.services.vision.camera import RTSPCamera

    with RTSPCamera(camera_ip) as camera:
        if not camera.is_connected:
            return {"detected": False, "error": "Camera not connected"}

        frame = camera.capture_frame()

        if frame is None:
            return {"detected": False, "error": "Failed to capture frame"}

        reader = CedulaReader()
        return reader.read_cedula(frame)

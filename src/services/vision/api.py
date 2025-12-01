"""
API FastAPI para el servicio de OCR.
Este servicio procesa imágenes de placas y cédulas usando YOLO + EasyOCR.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
from datetime import datetime
from typing import Optional,  Literal

app = FastAPI(
    title="SITNOVA OCR Service",
    description="Servicio de visión artificial para detección de placas y lectura de cédulas",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# SCHEMAS
# ============================================

class PlateDetectionRequest(BaseModel):
    """Request para detección de placa"""
    camera_ip: str
    save_image: bool = True


class CedulaDetectionRequest(BaseModel):
    """Request para detección de cédula"""
    camera_ip: str
    save_image: bool = True


class OCRResponse(BaseModel):
    """Response genérico de OCR"""
    detected: bool
    text: Optional[str] = None
    confidence: Optional[float] = None
    image_url: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: dict = {}


# ============================================
# ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check para Docker"""
    return {
        "status": "healthy",
        "service": "sitnova-ocr",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/ocr/plate", response_model=OCRResponse)
async def detect_plate(request: PlateDetectionRequest):
    """
    Detecta y lee una placa vehicular.

    Flow:
    1. Conectar a cámara RTSP
    2. Capturar frame
    3. YOLO detecta vehículo y placa
    4. EasyOCR lee texto de la placa
    5. Validar formato Costa Rica (ABC-123)
    6. Guardar imagen si save_image=True
    """
    logger.info(f"📸 Detectando placa desde: {request.camera_ip}")

    start_time = datetime.now()

    try:
        # TODO: Implementar detección real
        # from src.services.vision.plate_detector import detect_plate_from_camera
        # result = detect_plate_from_camera(request.camera_ip)

        # Mock por ahora
        logger.warning("⚠️  Usando mock - OCR no implementado aún")

        result = {
            "detected": True,
            "text": "ABC-123",
            "confidence": 0.95,
            "image_url": "data/images/plate_mock.jpg",
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "metadata": {
                "camera_ip": request.camera_ip,
                "vehicle_type": "car",
                "detection_method": "mock"
            }
        }

        logger.success(f"✅ Placa detectada: {result['text']} (conf: {result['confidence']})")
        return OCRResponse(**result)

    except Exception as e:
        logger.error(f"❌ Error en detección de placa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr/cedula", response_model=OCRResponse)
async def detect_cedula(request: CedulaDetectionRequest):
    """
    Detecta y lee una cédula de Costa Rica.

    Flow:
    1. Conectar a cámara RTSP
    2. Capturar frame
    3. YOLO detecta documento
    4. EasyOCR lee campos (número, nombre, vencimiento)
    5. Validar formato cédula CR (X-XXXX-XXXX)
    6. Guardar imagen
    """
    logger.info(f"📸 Detectando cédula desde: {request.camera_ip}")

    start_time = datetime.now()

    try:
        # TODO: Implementar detección real
        # from src.services.vision.cedula_reader import read_cedula_from_camera
        # result = read_cedula_from_camera(request.camera_ip)

        # Mock por ahora
        logger.warning("⚠️  Usando mock - OCR no implementado aún")

        result = {
            "detected": True,
            "text": "1-2345-6789",
            "confidence": 0.92,
            "image_url": "data/images/cedula_mock.jpg",
            "processing_time": (datetime.now() - start_time).total_seconds(),
            "metadata": {
                "camera_ip": request.camera_ip,
                "nombre": "María González",
                "vencimiento": "2030-12-31",
                "detection_method": "mock"
            }
        }

        logger.success(f"✅ Cédula detectada: {result['text']} (conf: {result['confidence']})")
        return OCRResponse(**result)

    except Exception as e:
        logger.error(f"❌ Error en detección de cédula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ocr/capture")
async def capture_image(camera_ip: str):
    """
    Captura una imagen sin procesamiento.
    Útil para debugging.
    """
    logger.info(f"📸 Capturando imagen desde: {camera_ip}")

    try:
        # TODO: Implementar captura real
        # from src.services.vision.camera import capture_frame
        # image_path = capture_frame(camera_ip)

        return {
            "success": True,
            "camera_ip": camera_ip,
            "image_url": "data/images/capture_mock.jpg",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Error capturando imagen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """
    Estadísticas del servicio OCR.
    """
    return {
        "total_detections": 0,
        "plates_detected": 0,
        "cedulas_detected": 0,
        "avg_processing_time": 0.0,
        "success_rate": 100.0
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.services.vision.api:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )

"""
Endpoints para operaciones de visión artificial.
Proxy hacia el servicio OCR containerizado.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger
import httpx

from src.config.settings import settings

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class PlateDetectionRequest(BaseModel):
    """Request para detección de placa"""
    camera_id: str
    save_image: bool = True


class CedulaDetectionRequest(BaseModel):
    """Request para detección de cédula"""
    camera_id: str
    save_image: bool = True


# ============================================
# ENDPOINTS
# ============================================

@router.post("/detect-plate")
async def detect_plate(request: PlateDetectionRequest):
    """
    Detecta y lee una placa vehicular desde la cámara especificada.

    Delega al servicio OCR containerizado.
    """
    logger.info(f"🚗 Detectando placa desde cámara: {request.camera_id}")

    try:
        # TODO: Llamar al servicio OCR
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         "http://ocr-service:8001/ocr/plate",
        #         json=request.dict(),
        #         timeout=10.0
        #     )
        #     return response.json()

        # Mock response por ahora
        return {
            "detected": True,
            "plate": "ABC-123",
            "confidence": 0.95,
            "vehicle_type": "car",
            "image_url": "data/images/plate_12345.jpg",
        }

    except Exception as e:
        logger.error(f"❌ Error detectando placa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-cedula")
async def detect_cedula(request: CedulaDetectionRequest):
    """
    Detecta y lee una cédula de Costa Rica desde la cámara especificada.

    Delega al servicio OCR containerizado.
    """
    logger.info(f"🪪 Detectando cédula desde cámara: {request.camera_id}")

    try:
        # TODO: Llamar al servicio OCR
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         "http://ocr-service:8001/ocr/cedula",
        #         json=request.dict(),
        #         timeout=10.0
        #     )
        #     return response.json()

        # Mock response por ahora
        return {
            "detected": True,
            "cedula": "1-2345-6789",
            "nombre": "Juan Pérez Rodríguez",
            "confidence": 0.92,
            "image_url": "data/images/cedula_12345.jpg",
        }

    except Exception as e:
        logger.error(f"❌ Error detectando cédula: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/capture-image")
async def capture_image(camera_id: str):
    """
    Captura una imagen desde la cámara especificada sin procesar.
    """
    logger.info(f"📸 Capturando imagen desde: {camera_id}")

    # TODO: Implementar captura directa de RTSP
    return {
        "success": True,
        "camera_id": camera_id,
        "image_url": f"data/images/capture_{camera_id}.jpg",
        "timestamp": "2025-11-30T12:00:00Z",
    }

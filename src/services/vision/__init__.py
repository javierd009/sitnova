"""
Servicios de vision artificial (OCR).
"""
from src.services.vision.plate_detector import PlateDetector, detect_plate_from_camera
from src.services.vision.cedula_reader import CedulaReader, read_cedula_from_camera
from src.services.vision.camera import RTSPCamera, MockCamera

__all__ = [
    "PlateDetector",
    "detect_plate_from_camera",
    "CedulaReader",
    "read_cedula_from_camera",
    "RTSPCamera",
    "MockCamera"
]

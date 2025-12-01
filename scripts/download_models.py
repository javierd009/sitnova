"""
Script para descargar modelos de IA necesarios para SITNOVA.
"""
import os
from pathlib import Path
from loguru import logger

def download_yolo_model():
    """Descarga modelo YOLOv8 nano."""
    logger.info("📦 Descargando modelo YOLOv8...")

    try:
        from ultralytics import YOLO

        # Crear directorio models si no existe
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)

        model_path = models_dir / "yolov8n.pt"

        if model_path.exists():
            logger.success(f"✅ Modelo ya existe en {model_path}")
            return True

        # Descargar modelo
        logger.info("⏳ Descargando YOLOv8 nano (6MB aprox)...")
        model = YOLO('yolov8n.pt')  # Descarga automáticamente

        # Mover a directorio models
        import shutil
        source = Path.home() / ".cache" / "ultralytics" / "yolov8n.pt"

        if source.exists():
            shutil.copy(source, model_path)
            logger.success(f"✅ Modelo descargado exitosamente: {model_path}")
        else:
            # Si ya está en el directorio actual
            if Path("yolov8n.pt").exists():
                shutil.move("yolov8n.pt", model_path)
                logger.success(f"✅ Modelo movido a: {model_path}")

        return True

    except ImportError:
        logger.error("❌ ultralytics no está instalado. Ejecuta: pip install ultralytics")
        return False
    except Exception as e:
        logger.error(f"❌ Error descargando modelo: {e}")
        return False


def verify_models():
    """Verifica que los modelos estén disponibles."""
    logger.info("🔍 Verificando modelos...")

    models_dir = Path("models")
    yolo_model = models_dir / "yolov8n.pt"

    if yolo_model.exists():
        size_mb = yolo_model.stat().st_size / (1024 * 1024)
        logger.success(f"✅ YOLOv8 nano: {size_mb:.2f} MB")
        return True
    else:
        logger.warning(f"⚠️  YOLOv8 no encontrado en {yolo_model}")
        return False


def test_yolo():
    """Prueba que YOLO funcione correctamente."""
    logger.info("🧪 Probando YOLOv8...")

    try:
        from ultralytics import YOLO
        import numpy as np

        model_path = Path("models") / "yolov8n.pt"

        if not model_path.exists():
            logger.error(f"❌ Modelo no encontrado: {model_path}")
            return False

        # Cargar modelo
        model = YOLO(str(model_path))

        # Crear imagen de prueba (dummy)
        test_image = np.zeros((640, 640, 3), dtype=np.uint8)

        # Hacer predicción
        results = model(test_image, verbose=False)

        logger.success("✅ YOLO funciona correctamente")
        logger.info(f"   - Clases disponibles: {len(model.names)}")
        logger.info(f"   - Modelo: {model.task}")

        return True

    except Exception as e:
        logger.error(f"❌ Error probando YOLO: {e}")
        return False


def test_easyocr():
    """Prueba que EasyOCR funcione correctamente."""
    logger.info("🧪 Probando EasyOCR...")

    try:
        import easyocr
        import numpy as np

        # Crear reader (descarga modelos automáticamente en primera ejecución)
        logger.info("⏳ Inicializando EasyOCR (puede tardar en primera ejecución)...")
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)

        # Crear imagen de prueba
        test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255

        # Intentar OCR
        results = reader.readtext(test_image, detail=0)

        logger.success("✅ EasyOCR funciona correctamente")
        logger.info(f"   - Idiomas: ['en']")
        logger.info(f"   - GPU: False (usando CPU)")

        return True

    except Exception as e:
        logger.error(f"❌ Error probando EasyOCR: {e}")
        return False


if __name__ == "__main__":
    logger.info("🚀 SITNOVA - Descarga de Modelos")
    logger.info("=" * 60)

    # 1. Descargar YOLO
    if download_yolo_model():
        logger.success("✅ Paso 1/4: YOLO descargado")
    else:
        logger.error("❌ Paso 1/4: Error descargando YOLO")

    # 2. Verificar modelos
    if verify_models():
        logger.success("✅ Paso 2/4: Modelos verificados")
    else:
        logger.warning("⚠️  Paso 2/4: Algunos modelos faltan")

    # 3. Test YOLO
    if test_yolo():
        logger.success("✅ Paso 3/4: YOLO probado exitosamente")
    else:
        logger.error("❌ Paso 3/4: Error probando YOLO")

    # 4. Test EasyOCR
    if test_easyocr():
        logger.success("✅ Paso 4/4: EasyOCR probado exitosamente")
    else:
        logger.error("❌ Paso 4/4: Error probando EasyOCR")

    logger.info("=" * 60)
    logger.success("🎉 Descarga de modelos completada!")
    logger.info("")
    logger.info("📋 Próximos pasos:")
    logger.info("  1. Configurar API de IA en .env (ANTHROPIC_API_KEY o OPENAI_API_KEY)")
    logger.info("  2. Configurar Supabase (opcional para pruebas)")
    logger.info("  3. Ejecutar: docker-compose up -d")
    logger.info("  4. Probar: python scripts/test_happy_path.py")

"""
Script para verificar el estado de SITNOVA y sus dependencias.
"""
import os
import sys
from pathlib import Path
from loguru import logger

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


def check_models():
    """Verifica modelos de IA."""
    logger.info("📦 Verificando modelos...")

    models_dir = Path("models")
    yolo_model = models_dir / "yolov8n.pt"

    if yolo_model.exists():
        size_mb = yolo_model.stat().st_size / (1024 * 1024)
        logger.success(f"  ✅ YOLOv8: {size_mb:.2f} MB")
        return True
    else:
        logger.warning(f"  ⚠️  YOLOv8 no encontrado")
        logger.info(f"     Ejecuta: python scripts/download_models.py")
        return False


def check_dependencies():
    """Verifica dependencias Python."""
    logger.info("📚 Verificando dependencias...")

    deps = {
        "ultralytics": "YOLO",
        "easyocr": "OCR",
        "cv2": "OpenCV",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "fastapi": "FastAPI",
        "supabase": "Supabase Client"
    }

    missing = []
    for package, name in deps.items():
        try:
            __import__(package)
            logger.success(f"  ✅ {name}")
        except ImportError:
            logger.warning(f"  ⚠️  {name} no instalado")
            # Map display name back to pip package name
            pip_package = "opencv-python" if package == "cv2" else package
            missing.append(pip_package)

    if missing:
        logger.info(f"     Ejecuta: pip install {' '.join(missing)}")
        return False

    return True


def check_env_config():
    """Verifica configuración en .env"""
    logger.info("⚙️  Verificando configuración...")

    if not Path(".env").exists():
        logger.warning("  ⚠️  Archivo .env no existe")
        logger.info("     Ejecuta: cp .env.example .env")
        return False

    # Leer .env
    env_vars = {}
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    # Verificar IA API
    has_anthropic = bool(env_vars.get("ANTHROPIC_API_KEY"))
    has_openai = bool(env_vars.get("OPENAI_API_KEY"))
    has_google = bool(env_vars.get("GOOGLE_API_KEY"))

    if has_google:
        logger.success("  ✅ API de IA: Google Gemini configurado")
    elif has_anthropic:
        logger.success("  ✅ API de IA: Anthropic configurado")
    elif has_openai:
        logger.success("  ✅ API de IA: OpenAI configurado")
    else:
        logger.warning("  ⚠️  API de IA no configurado")
        logger.info("     Agrega GOOGLE_API_KEY, ANTHROPIC_API_KEY o OPENAI_API_KEY al .env")

    # Verificar Supabase
    has_supabase = bool(env_vars.get("SUPABASE_URL")) and bool(env_vars.get("SUPABASE_SERVICE_ROLE_KEY"))

    if has_supabase:
        logger.success("  ✅ Supabase configurado")
    else:
        logger.warning("  ⚠️  Supabase no configurado (usando mocks)")
        logger.info("     Opcional para pruebas")

    # Verificar hardware
    has_cameras = bool(env_vars.get("CAMERA_ENTRADA_URL")) and "localhost" not in env_vars.get("CAMERA_ENTRADA_URL", "localhost")
    has_hikvision = bool(env_vars.get("HIKVISION_HOST")) and env_vars.get("HIKVISION_HOST") != "localhost"
    has_freepbx = bool(env_vars.get("FREEPBX_HOST")) and env_vars.get("FREEPBX_HOST") != "localhost"
    has_evolution = bool(env_vars.get("EVOLUTION_API_URL")) and "localhost" not in env_vars.get("EVOLUTION_API_URL", "localhost")

    if has_cameras:
        logger.success("  ✅ Cámaras configuradas")
    else:
        logger.info("  ℹ️  Cámaras: usando mocks")

    if has_hikvision:
        logger.success("  ✅ Hikvision configurado")
    else:
        logger.info("  ℹ️  Hikvision: usando mocks")

    if has_freepbx:
        logger.success("  ✅ FreePBX configurado")
    else:
        logger.info("  ℹ️  FreePBX: usando mocks")

    if has_evolution:
        logger.success("  ✅ Evolution API configurado")
    else:
        logger.info("  ℹ️  Evolution: usando mocks")

    return True


def check_docker():
    """Verifica Docker."""
    logger.info("🐳 Verificando Docker...")

    try:
        import subprocess
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            logger.success("  ✅ Docker disponible")

            # Check si hay containers corriendo
            if "sitnova" in result.stdout.lower():
                logger.success("  ✅ Containers SITNOVA corriendo")
            else:
                logger.info("  ℹ️  Containers SITNOVA no corriendo")
                logger.info("     Ejecuta: docker-compose up -d")

            return True
        else:
            logger.warning("  ⚠️  Docker no disponible")
            return False

    except FileNotFoundError:
        logger.warning("  ⚠️  Docker no instalado")
        logger.info("     Opcional: puedes ejecutar sin Docker")
        return False
    except Exception as e:
        logger.warning(f"  ⚠️  Error verificando Docker: {e}")
        return False


def check_database():
    """Verifica schema de base de datos."""
    logger.info("🗄️  Verificando base de datos...")

    schema_file = Path("database/schema-sitnova.sql")

    if schema_file.exists():
        logger.success("  ✅ Schema SQL disponible")
        return True
    else:
        logger.warning("  ⚠️  Schema SQL no encontrado")
        return False


def print_summary(checks):
    """Imprime resumen del estado."""
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 RESUMEN")
    logger.info("=" * 60)

    ready = sum(checks.values())
    total = len(checks)

    logger.info(f"  {ready}/{total} componentes listos")
    logger.info("")

    if checks.get("models") and checks.get("dependencies") and checks.get("env"):
        logger.success("✅ SISTEMA LISTO PARA PRUEBAS BÁSICAS")
        logger.info("")
        logger.info("Puedes ejecutar:")
        logger.info("  python test_simple.py")
        logger.info("  python scripts/test_happy_path.py")
    else:
        logger.warning("⚠️  SISTEMA REQUIERE CONFIGURACIÓN")
        logger.info("")
        logger.info("Próximos pasos:")
        if not checks.get("models"):
            logger.info("  1. python scripts/download_models.py")
        if not checks.get("dependencies"):
            logger.info("  2. pip install -r requirements.txt")
        if not checks.get("env"):
            logger.info("  3. cp .env.example .env y configurar API keys")

    logger.info("")
    logger.info("Ver guía completa en: SETUP-RAPIDO.md")
    logger.info("=" * 60)


if __name__ == "__main__":
    logger.info("🔍 SITNOVA - Verificación de Estado")
    logger.info("=" * 60)
    logger.info("")

    checks = {}

    # Run all checks
    checks["models"] = check_models()
    logger.info("")

    checks["dependencies"] = check_dependencies()
    logger.info("")

    checks["env"] = check_env_config()
    logger.info("")

    checks["docker"] = check_docker()
    logger.info("")

    checks["database"] = check_database()

    # Print summary
    print_summary(checks)

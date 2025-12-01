"""
Script para verificar que Supabase está correctamente configurado.
"""
import os
from dotenv import load_dotenv
from loguru import logger
from supabase import create_client
import sys

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()


def verify_supabase():
    """Verifica conexión y tablas de Supabase."""

    logger.info("🔍 SITNOVA - Verificación de Supabase")
    logger.info("=" * 60)

    # Obtener credenciales
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        logger.error("❌ Credenciales de Supabase no configuradas en .env")
        return False

    logger.info(f"📋 URL: {url}")
    logger.info("")

    # Conectar
    try:
        logger.info("🔌 Conectando...")
        client = create_client(url, key)
        logger.success("✅ Conexión exitosa")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Error conectando: {e}")
        return False

    # Verificar tablas
    logger.info("📊 Verificando tablas...")
    logger.info("")

    tables_to_check = [
        "condominiums",
        "residents",
        "authorized_vehicles",
        "pre_authorized_visitors",
        "access_logs",
        "visitor_sessions",
    ]

    all_ok = True

    for table in tables_to_check:
        try:
            result = client.table(table).select("*").limit(1).execute()
            logger.success(f"  ✅ {table}")
        except Exception as e:
            logger.error(f"  ❌ {table}: {str(e)[:80]}")
            all_ok = False

    logger.info("")
    logger.info("=" * 60)

    if all_ok:
        logger.success("🎉 ¡Supabase configurado correctamente!")
        logger.info("")
        logger.info("📋 Próximos pasos:")
        logger.info("  1. Insertar datos de prueba (condominio, residentes, vehículos)")
        logger.info("  2. Ejecutar: python scripts/seed_database.py")
        logger.info("  3. Probar el sistema con datos reales")
    else:
        logger.warning("⚠️  Algunas tablas no existen")
        logger.info("")
        logger.info("📋 Acción requerida:")
        logger.info("  1. Ve al SQL Editor de Supabase")
        logger.info("  2. Ejecuta: database/schema-sitnova.sql")
        logger.info("  3. Vuelve a ejecutar este script")

    logger.info("")
    logger.info("=" * 60)

    return all_ok


if __name__ == "__main__":
    success = verify_supabase()
    sys.exit(0 if success else 1)

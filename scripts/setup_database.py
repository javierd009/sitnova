"""
Script para configurar la base de datos de SITNOVA en Supabase.
Ejecuta el schema SQL completo.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
import sys

# Load environment
load_dotenv()

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


def setup_database():
    """Ejecuta el schema SQL en Supabase."""

    logger.info("🗄️  SITNOVA - Configuración de Base de Datos")
    logger.info("=" * 60)

    # Verificar que tenemos las credenciales
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados en .env")
        return False

    logger.info(f"📋 URL: {supabase_url}")
    logger.info("")

    # Leer schema SQL
    schema_file = Path("database/schema-sitnova.sql")

    if not schema_file.exists():
        logger.error(f"❌ Schema SQL no encontrado: {schema_file}")
        return False

    logger.info(f"📄 Leyendo schema: {schema_file}")
    schema_sql = schema_file.read_text(encoding='utf-8')
    logger.info(f"   📏 Tamaño: {len(schema_sql)} caracteres")
    logger.info("")

    # Conectar a Supabase
    try:
        from supabase import create_client

        logger.info("🔌 Conectando a Supabase...")
        client = create_client(supabase_url, supabase_key)
        logger.success("✅ Conexión exitosa")
        logger.info("")

    except Exception as e:
        logger.error(f"❌ Error conectando a Supabase: {e}")
        return False

    # IMPORTANTE: Supabase client de Python no soporta ejecutar SQL raw directamente
    # Necesitamos usar la REST API de Supabase o el SQL Editor

    logger.warning("⚠️  El cliente de Python de Supabase no soporta ejecutar SQL raw")
    logger.info("")
    logger.info("Para ejecutar el schema, usa una de estas opciones:")
    logger.info("")
    logger.info("📋 OPCIÓN 1 (Recomendado): SQL Editor de Supabase")
    logger.info("   1. Ve a: https://lgqeeumflbzzmqysqkiq.supabase.co/project/default/sql")
    logger.info("   2. Crea una nueva query")
    logger.info("   3. Copia y pega: database/schema-sitnova.sql")
    logger.info("   4. Haz clic en 'Run'")
    logger.info("")
    logger.info("📋 OPCIÓN 2: psycopg2 (PostgreSQL directo)")
    logger.info("   Requiere instalar: pip install psycopg2-binary")
    logger.info("   Y obtener la connection string de Supabase")
    logger.info("")

    # Copiar el schema al clipboard si está disponible
    try:
        import pyperclip
        pyperclip.copy(schema_sql)
        logger.success("✅ Schema copiado al clipboard! Puedes pegarlo directamente en el SQL Editor")
    except ImportError:
        logger.info("💡 Tip: Instala pyperclip para copiar automáticamente: pip install pyperclip")

    logger.info("")
    logger.info("=" * 60)

    return True


if __name__ == "__main__":
    setup_database()

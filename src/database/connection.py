"""
Cliente de Supabase para SITNOVA.
Singleton para reutilizar la conexión en toda la aplicación.
"""
from typing import Optional
from supabase import create_client, Client
from loguru import logger
from src.config.settings import settings


class SupabaseClient:
    """Singleton de cliente Supabase"""

    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Obtiene la instancia singleton del cliente Supabase.

        Returns:
            Cliente de Supabase configurado
        """
        if cls._instance is None:
            logger.info("🔌 Inicializando conexión a Supabase...")

            if not settings.supabase_url or not settings.supabase_service_role_key:
                logger.warning("⚠️  Credenciales de Supabase no configuradas")
                # En desarrollo, podemos continuar sin Supabase
                if settings.is_development:
                    logger.info("Modo desarrollo: continuando sin Supabase")
                    return None
                raise ValueError("SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY son requeridos")

            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )

            logger.success("✅ Conectado a Supabase")

        return cls._instance


# Función helper para obtener el cliente fácilmente
def get_supabase() -> Client:
    """
    Helper function para obtener el cliente de Supabase.

    Usage:
        from src.database.connection import get_supabase

        supabase = get_supabase()
        result = supabase.table("residents").select("*").execute()
    """
    return SupabaseClient.get_client()

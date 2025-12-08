"""
Helper para obtener configuracion multi-tenant de condominios.

Este modulo centraliza la logica para:
1. Buscar condominio por extension SIP o ID
2. Obtener configuracion de Evolution API por condominio
3. Fallback a configuracion global (settings.py) si no hay config especifica
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger

from src.database.connection import get_supabase
from src.config.settings import settings


@dataclass
class CondoConfig:
    """Configuracion de un condominio."""
    condominium_id: str
    name: str
    slug: str

    # Evolution API (WhatsApp)
    evolution_api_url: str
    evolution_api_key: str
    evolution_instance_name: str

    # Operador
    operator_extension: str
    operator_phone: Optional[str] = None

    # Gate Control
    gate_api_endpoint: Optional[str] = None
    gate_api_key: Optional[str] = None


def get_default_config() -> CondoConfig:
    """
    Retorna la configuracion por defecto desde settings.py.
    Usado cuando no hay configuracion especifica del condominio.
    """
    # DEBUG: Log what we're reading from settings
    logger.info(f"📋 SETTINGS DEBUG - get_default_config():")
    logger.info(f"   evolution_api_url: {settings.evolution_api_url}")
    logger.info(f"   evolution_api_key presente: {bool(settings.evolution_api_key)}")
    logger.info(f"   evolution_instance_name: {settings.evolution_instance_name}")

    return CondoConfig(
        condominium_id="default-condo-id",
        name="Default Condominium",
        slug="default",
        evolution_api_url=settings.evolution_api_url,
        evolution_api_key=settings.evolution_api_key,
        evolution_instance_name=settings.evolution_instance_name,
        operator_extension=settings.operator_extension,
        operator_phone=settings.operator_phone,
    )


async def get_condo_config_by_id(condominium_id: str) -> CondoConfig:
    """
    Obtiene la configuracion de un condominio por su ID.

    Args:
        condominium_id: ID del condominio (UUID o slug)

    Returns:
        CondoConfig con los valores del condominio o defaults
    """
    # Si es el ID default, retornar config global
    if not condominium_id or condominium_id == "default-condo-id":
        logger.debug("Usando configuracion por defecto (default-condo-id)")
        return get_default_config()

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase no disponible, usando config default")
            return get_default_config()

        # Buscar por ID o slug
        result = supabase.table("condominiums").select(
            "id, name, slug, evolution_api_url, evolution_api_key, "
            "evolution_instance_name, operator_extension, gate_api_endpoint, gate_api_key"
        ).or_(
            f"id.eq.{condominium_id},slug.eq.{condominium_id}"
        ).eq("is_active", True).limit(1).execute()

        if result.data and len(result.data) > 0:
            condo = result.data[0]
            logger.info(f"Config encontrada para condominio: {condo.get('name')}")

            return CondoConfig(
                condominium_id=condo.get("id"),
                name=condo.get("name", ""),
                slug=condo.get("slug", ""),
                # Evolution - usar DB o fallback a settings
                evolution_api_url=condo.get("evolution_api_url") or settings.evolution_api_url,
                evolution_api_key=condo.get("evolution_api_key") or settings.evolution_api_key,
                evolution_instance_name=condo.get("evolution_instance_name") or settings.evolution_instance_name,
                # Operador
                operator_extension=condo.get("operator_extension") or settings.operator_extension,
                operator_phone=settings.operator_phone,  # Siempre de settings por ahora
                # Gate
                gate_api_endpoint=condo.get("gate_api_endpoint"),
                gate_api_key=condo.get("gate_api_key"),
            )

        logger.warning(f"Condominio no encontrado: {condominium_id}, usando config default")
        return get_default_config()

    except Exception as e:
        logger.error(f"Error obteniendo config de condominio {condominium_id}: {e}")
        return get_default_config()


async def get_condo_config_by_extension(extension: str) -> CondoConfig:
    """
    Obtiene la configuracion de un condominio por su extension PBX.

    Esto es crucial para multi-tenant: cuando AsterSIPVox recibe una llamada
    a la extension 1000, sabemos que corresponde a un condominio especifico.

    Args:
        extension: Extension PBX (ej: "1000")

    Returns:
        CondoConfig del condominio asociado a esa extension
    """
    if not extension:
        logger.debug("Extension vacia, usando config default")
        return get_default_config()

    try:
        supabase = get_supabase()
        if not supabase:
            logger.warning("Supabase no disponible, usando config default")
            return get_default_config()

        result = supabase.table("condominiums").select(
            "id, name, slug, evolution_api_url, evolution_api_key, "
            "evolution_instance_name, operator_extension, gate_api_endpoint, gate_api_key"
        ).eq("pbx_extension", extension).eq("is_active", True).limit(1).execute()

        if result.data and len(result.data) > 0:
            condo = result.data[0]
            logger.info(f"Config encontrada para extension {extension}: {condo.get('name')}")

            return CondoConfig(
                condominium_id=condo.get("id"),
                name=condo.get("name", ""),
                slug=condo.get("slug", ""),
                evolution_api_url=condo.get("evolution_api_url") or settings.evolution_api_url,
                evolution_api_key=condo.get("evolution_api_key") or settings.evolution_api_key,
                evolution_instance_name=condo.get("evolution_instance_name") or settings.evolution_instance_name,
                operator_extension=condo.get("operator_extension") or settings.operator_extension,
                operator_phone=settings.operator_phone,
                gate_api_endpoint=condo.get("gate_api_endpoint"),
                gate_api_key=condo.get("gate_api_key"),
            )

        logger.warning(f"No hay condominio para extension {extension}, usando config default")
        return get_default_config()

    except Exception as e:
        logger.error(f"Error buscando condominio por extension {extension}: {e}")
        return get_default_config()


async def get_condo_config(
    condominium_id: Optional[str] = None,
    extension: Optional[str] = None
) -> CondoConfig:
    """
    Obtiene la configuracion de un condominio usando cualquier identificador.

    Prioridad:
    1. condominium_id si se proporciona
    2. extension PBX si se proporciona
    3. Config default

    Args:
        condominium_id: ID o slug del condominio
        extension: Extension PBX

    Returns:
        CondoConfig apropiada
    """
    if condominium_id and condominium_id != "default-condo-id":
        return await get_condo_config_by_id(condominium_id)

    if extension:
        return await get_condo_config_by_extension(extension)

    return get_default_config()

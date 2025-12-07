"""
Endpoints CRUD para Condominios (Multi-Tenant).

Permite gestionar condominios y su configuracion:
- Crear/editar condominios
- Configurar Evolution API, Hikvision, FreePBX por condominio
- Mapear extension SIP -> condominium_id
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from loguru import logger

from src.database.connection import get_supabase


router = APIRouter()


# ============================================
# SCHEMAS
# ============================================

class CondominiumBase(BaseModel):
    """Base schema para condominio."""
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=200)
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class CondominiumConfig(BaseModel):
    """Configuracion tecnica del condominio."""
    # PBX/SIP
    pbx_extension: Optional[str] = None
    pbx_caller_id: Optional[str] = None
    operator_extension: Optional[str] = "1002"

    # Evolution API (WhatsApp)
    evolution_api_url: Optional[str] = None
    evolution_api_key: Optional[str] = None
    evolution_instance_name: Optional[str] = None

    # Gate Control
    gate_control_type: Optional[str] = "api"
    gate_api_endpoint: Optional[str] = None
    gate_api_key: Optional[str] = None

    # Hikvision Cameras
    camera_plates_ip: Optional[str] = None
    camera_plates_username: Optional[str] = None
    camera_plates_password: Optional[str] = None


class CondominiumCreate(CondominiumBase):
    """Schema para crear condominio."""
    pass


class CondominiumUpdate(BaseModel):
    """Schema para actualizar condominio."""
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class CondominiumResponse(CondominiumBase):
    """Response con datos del condominio."""
    id: str
    is_active: bool
    subscription_plan: str
    created_at: str


# ============================================
# HELPER: Get condominium by extension
# ============================================

async def get_condominium_by_extension(extension: str) -> Optional[dict]:
    """
    Busca un condominio por su extension PBX.

    Esto es crucial para el multi-tenant: cuando llega una llamada
    a la extension 1000, sabemos que es del condominio X.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            return None

        result = supabase.table("condominiums").select(
            "id, name, slug, pbx_extension, evolution_api_url, evolution_api_key, "
            "evolution_instance_name, operator_extension, gate_api_endpoint, gate_api_key"
        ).eq("pbx_extension", extension).eq("is_active", True).limit(1).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None

    except Exception as e:
        logger.error(f"Error buscando condominio por extension {extension}: {e}")
        return None


# ============================================
# ENDPOINTS
# ============================================

@router.get("")
async def list_condominiums(
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Lista todos los condominios.

    Filtros opcionales:
    - is_active: Solo activos/inactivos
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        query = supabase.table("condominiums").select(
            "id, name, slug, address, city, phone, email, is_active, "
            "subscription_plan, pbx_extension, created_at"
        )

        if is_active is not None:
            query = query.eq("is_active", is_active)

        query = query.order("name").range(offset, offset + limit - 1)
        result = query.execute()

        return {
            "condominiums": result.data,
            "count": len(result.data),
            "offset": offset,
            "limit": limit,
        }

    except Exception as e:
        logger.error(f"Error listando condominios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-extension/{extension}")
async def get_by_extension(extension: str):
    """
    Obtiene un condominio por su extension PBX.

    Usado por el agente de voz para saber a que condominio
    pertenece la llamada entrante.
    """
    condo = await get_condominium_by_extension(extension)

    if not condo:
        raise HTTPException(
            status_code=404,
            detail=f"No condominium found for extension {extension}"
        )

    return {
        "condominium_id": condo["id"],
        "name": condo["name"],
        "slug": condo["slug"],
        "config": {
            "evolution_instance": condo.get("evolution_instance_name"),
            "operator_extension": condo.get("operator_extension", "1002"),
        }
    }


@router.get("/{condominium_id}")
async def get_condominium(condominium_id: str):
    """
    Obtiene un condominio por ID.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        result = supabase.table("condominiums").select("*").eq(
            "id", condominium_id
        ).limit(1).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Condominium not found")

        condo = result.data[0]

        # Ocultar campos sensibles
        sensitive_fields = ["gate_api_key", "evolution_api_key",
                          "camera_plates_password", "camera_cedula_password"]
        for field in sensitive_fields:
            if field in condo and condo[field]:
                condo[field] = "***hidden***"

        return condo

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo condominio {condominium_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_condominium(data: CondominiumCreate):
    """
    Crea un nuevo condominio.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        # Verificar que el slug no exista
        existing = supabase.table("condominiums").select("id").eq(
            "slug", data.slug
        ).limit(1).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Slug '{data.slug}' already exists"
            )

        # Crear condominio
        result = supabase.table("condominiums").insert({
            "name": data.name,
            "slug": data.slug,
            "address": data.address,
            "city": data.city,
            "phone": data.phone,
            "email": data.email,
            "subscription_plan": "trial",
            "is_active": True,
        }).execute()

        if result.data and len(result.data) > 0:
            logger.success(f"Condominio creado: {data.name} ({data.slug})")
            return result.data[0]

        raise HTTPException(status_code=500, detail="Failed to create condominium")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando condominio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{condominium_id}")
async def update_condominium(condominium_id: str, data: CondominiumUpdate):
    """
    Actualiza un condominio existente.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        # Construir datos a actualizar (solo los campos presentes)
        update_data = {k: v for k, v in data.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now().isoformat()

        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")

        result = supabase.table("condominiums").update(update_data).eq(
            "id", condominium_id
        ).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Condominio actualizado: {condominium_id}")
            return result.data[0]

        raise HTTPException(status_code=404, detail="Condominium not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando condominio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{condominium_id}/config")
async def update_condominium_config(condominium_id: str, config: CondominiumConfig):
    """
    Actualiza la configuracion tecnica de un condominio.

    Incluye:
    - PBX/SIP settings
    - Evolution API (WhatsApp)
    - Gate control
    - Hikvision cameras
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        # Construir datos a actualizar
        update_data = {k: v for k, v in config.dict().items() if v is not None}
        update_data["updated_at"] = datetime.now().isoformat()

        result = supabase.table("condominiums").update(update_data).eq(
            "id", condominium_id
        ).execute()

        if result.data and len(result.data) > 0:
            logger.success(f"Config actualizada para condominio: {condominium_id}")
            return {"updated": True, "fields": list(update_data.keys())}

        raise HTTPException(status_code=404, detail="Condominium not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{condominium_id}/stats")
async def get_condominium_stats(condominium_id: str):
    """
    Obtiene estadisticas del condominio.
    """
    try:
        supabase = get_supabase()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database not available")

        # Contar residentes
        residents = supabase.table("residents").select(
            "id", count="exact"
        ).eq("condominium_id", condominium_id).eq("is_active", True).execute()

        # Contar vehiculos
        vehicles = supabase.table("vehicles").select(
            "id", count="exact"
        ).eq("condominium_id", condominium_id).eq("is_active", True).execute()

        # Accesos de hoy
        today = datetime.now().date().isoformat()
        access_today = supabase.table("access_logs").select(
            "id", count="exact"
        ).eq("condominium_id", condominium_id).gte(
            "created_at", f"{today}T00:00:00"
        ).execute()

        return {
            "condominium_id": condominium_id,
            "residents_count": residents.count or 0,
            "vehicles_count": vehicles.count or 0,
            "access_today": access_today.count or 0,
        }

    except Exception as e:
        logger.error(f"Error obteniendo stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HELPER FUNCTION EXPORTS
# ============================================

# Esta funcion se exporta para ser usada por los tools
__all__ = ["get_condominium_by_extension", "router"]

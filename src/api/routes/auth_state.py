"""
Estado de autorizaciones pendientes.
Modulo compartido entre tools.py y webhooks.py

PERSISTENCIA: Usa Supabase para persistir entre reinicios del contenedor.
Fallback a memoria si Supabase no esta disponible.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from loguru import logger

# Try to import Supabase client
try:
    from src.database.connection import get_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available, using in-memory storage")

# Fallback in-memory storage (for development/testing)
_memory_authorizations: Dict[str, Dict[str, Any]] = {}


def _normalize_phone(phone: str) -> str:
    """Normaliza numero de telefono removiendo caracteres especiales."""
    return phone.replace("+", "").replace(" ", "").replace("-", "")


def _get_supabase_client():
    """Obtiene cliente Supabase si esta disponible."""
    if not SUPABASE_AVAILABLE:
        return None
    try:
        client = get_supabase()
        return client
    except Exception as e:
        logger.warning(f"Could not get Supabase client: {e}")
        return None


# ============================================
# SUPABASE OPERATIONS
# ============================================

def _supabase_get_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """Busca autorizacion pendiente en Supabase por telefono."""
    client = _get_supabase_client()
    if not client:
        return None

    try:
        clean_phone = _normalize_phone(phone)
        result = client.table("pending_authorizations").select("*").eq("phone", clean_phone).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error querying Supabase: {e}")
        return None


def _supabase_get_by_apartment(apartment: str) -> Optional[Dict[str, Any]]:
    """Busca autorizacion pendiente en Supabase por apartamento."""
    client = _get_supabase_client()
    if not client:
        return None

    try:
        # Extraer solo numeros para busqueda mas precisa
        apt_numbers = ''.join(filter(str.isdigit, apartment))

        # Buscar con patron flexible (sin quitar espacios del patron)
        apt_search = apartment.lower().strip()
        result = client.table("pending_authorizations").select("*").ilike("apartment", f"%{apt_search}%").order("created_at", desc=True).execute()

        # Si no hay resultados, intentar buscar solo por numero
        if (not result.data or len(result.data) == 0) and apt_numbers:
            logger.info(f"No match con '{apt_search}', intentando con numero: {apt_numbers}")
            result = client.table("pending_authorizations").select("*").ilike("apartment", f"%{apt_numbers}%").order("created_at", desc=True).execute()

        if result.data and len(result.data) > 0:
            # Filter to find exact apartment number match
            for auth in result.data:
                apt_db = auth.get("apartment", "")
                apt_db_numbers = ''.join(filter(str.isdigit, apt_db))
                # Match si los numeros son exactamente iguales
                if apt_numbers and apt_db_numbers == apt_numbers:
                    logger.info(f"Match exacto por numero: {apt_db} (numeros: {apt_numbers})")
                    return auth
            # If no exact match, return most recent
            logger.info(f"Sin match exacto, usando mas reciente: {result.data[0].get('apartment')}")
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Error querying Supabase by apartment: {e}")
        return None


def _supabase_set(phone: str, data: Dict[str, Any]) -> bool:
    """Guarda o actualiza autorizacion en Supabase."""
    client = _get_supabase_client()
    if not client:
        return False

    try:
        clean_phone = _normalize_phone(phone)
        record = {
            "phone": clean_phone,
            "apartment": data.get("apartment"),
            "visitor_name": data.get("visitor_name"),
            "status": data.get("status", "pendiente"),
            "mensaje_personalizado": data.get("mensaje_personalizado"),
            "cedula": data.get("cedula"),
            "placa": data.get("placa"),
            "created_at": data.get("timestamp") or datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
        }

        # Upsert (insert or update)
        result = client.table("pending_authorizations").upsert(
            record, on_conflict="phone"
        ).execute()

        logger.info(f"Supabase upsert success for {clean_phone}")
        return True
    except Exception as e:
        logger.error(f"Error upserting to Supabase: {e}")
        return False


def _supabase_update(phone: str, status: str, mensaje_personalizado: str = None) -> bool:
    """Actualiza estado de autorizacion en Supabase."""
    client = _get_supabase_client()
    if not client:
        return False

    try:
        clean_phone = _normalize_phone(phone)
        update_data = {
            "status": status,
            "responded_at": datetime.now().isoformat(),
        }
        if mensaje_personalizado:
            update_data["mensaje_personalizado"] = mensaje_personalizado

        result = client.table("pending_authorizations").update(update_data).eq("phone", clean_phone).execute()

        logger.info(f"Supabase update success for {clean_phone}: {status}")
        return True
    except Exception as e:
        logger.error(f"Error updating Supabase: {e}")
        return False


def _supabase_get_all() -> Dict[str, Dict[str, Any]]:
    """Obtiene todas las autorizaciones de Supabase."""
    client = _get_supabase_client()
    if not client:
        return {}

    try:
        result = client.table("pending_authorizations").select("*").order("created_at", desc=True).limit(50).execute()

        auths = {}
        for row in result.data or []:
            phone = row.get("phone")
            auths[phone] = {
                "apartment": row.get("apartment"),
                "visitor_name": row.get("visitor_name"),
                "status": row.get("status"),
                "timestamp": row.get("created_at"),
                "mensaje_personalizado": row.get("mensaje_personalizado"),
                "cedula": row.get("cedula"),
                "placa": row.get("placa"),
                "responded_at": row.get("responded_at"),
            }
        return auths
    except Exception as e:
        logger.error(f"Error getting all from Supabase: {e}")
        return {}


def _supabase_cleanup_old() -> int:
    """Limpia autorizaciones expiradas de Supabase."""
    client = _get_supabase_client()
    if not client:
        return 0

    try:
        # Delete expired records that are still pending
        result = client.table("pending_authorizations").delete().lt("expires_at", datetime.now().isoformat()).eq("status", "pendiente").execute()

        count = len(result.data) if result.data else 0
        if count > 0:
            logger.info(f"Cleaned up {count} expired authorizations from Supabase")
        return count
    except Exception as e:
        logger.error(f"Error cleaning up Supabase: {e}")
        return 0


# ============================================
# PUBLIC API (with Supabase + Memory fallback)
# ============================================

def get_pending_authorization(phone: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Busca autorizacion pendiente por telefono.

    Returns:
        Tuple of (key, authorization_dict) or (None, None)
    """
    clean_phone = _normalize_phone(phone)

    # Try Supabase first
    auth = _supabase_get_by_phone(clean_phone)
    if auth:
        return clean_phone, {
            "apartment": auth.get("apartment"),
            "visitor_name": auth.get("visitor_name"),
            "status": auth.get("status"),
            "timestamp": auth.get("created_at"),
            "mensaje_personalizado": auth.get("mensaje_personalizado"),
            "cedula": auth.get("cedula"),
            "placa": auth.get("placa"),
            "responded_at": auth.get("responded_at"),
        }

    # Fallback to memory
    for key, mem_auth in _memory_authorizations.items():
        if clean_phone in key or key in clean_phone:
            return key, mem_auth

    return None, None


def get_authorization_by_apartment(apartment: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Busca autorizacion pendiente por apartamento (retorna la mas reciente).
    """
    # Try Supabase first
    auth = _supabase_get_by_apartment(apartment)
    if auth:
        return auth.get("phone"), {
            "apartment": auth.get("apartment"),
            "visitor_name": auth.get("visitor_name"),
            "status": auth.get("status"),
            "timestamp": auth.get("created_at"),
            "mensaje_personalizado": auth.get("mensaje_personalizado"),
            "cedula": auth.get("cedula"),
            "placa": auth.get("placa"),
            "responded_at": auth.get("responded_at"),
        }

    # Fallback to memory
    apt_normalized = apartment.lower().replace(" ", "")
    matches = []

    for key, mem_auth in _memory_authorizations.items():
        apt_stored = mem_auth.get("apartment", "").lower().replace(" ", "")
        if apt_normalized in apt_stored or apt_stored in apt_normalized:
            matches.append((key, mem_auth))

    if not matches:
        return None, None

    # Sort by timestamp (most recent first)
    matches.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    return matches[0]


def set_pending_authorization(
    phone: str,
    apartment: str,
    visitor_name: str,
    cedula: str = None,
    placa: str = None
) -> str:
    """
    Guarda autorizacion pendiente con datos opcionales de OCR.

    Returns:
        Normalized phone number (key)
    """
    clean_phone = _normalize_phone(phone)
    timestamp = datetime.now().isoformat()

    auth_data = {
        "apartment": apartment,
        "visitor_name": visitor_name,
        "status": "pendiente",
        "timestamp": timestamp,
        "mensaje_personalizado": None,
        "cedula": cedula,
        "placa": placa,
    }

    # Try Supabase first
    if _supabase_set(clean_phone, auth_data):
        logger.info(f"Autorizacion guardada en Supabase: {clean_phone} -> {apartment} ({visitor_name})")
    else:
        # Fallback to memory
        _memory_authorizations[clean_phone] = auth_data
        logger.warning(f"Autorizacion guardada en MEMORIA (fallback): {clean_phone} -> {apartment}")

    if cedula:
        logger.info(f"   Cedula: {cedula}")
    if placa:
        logger.info(f"   Placa: {placa}")

    return clean_phone


def update_authorization(phone: str, status: str, mensaje_personalizado: str = None) -> bool:
    """
    Actualiza estado de autorizacion con mensaje personalizado opcional.

    Returns:
        True if updated successfully
    """
    key, auth = get_pending_authorization(phone)
    if not auth:
        logger.warning(f"No authorization found for {phone}")
        return False

    # Try Supabase first
    if _supabase_update(phone, status, mensaje_personalizado):
        if mensaje_personalizado:
            logger.info(f"Autorizacion actualizada en Supabase: {key} -> {status} (mensaje: {mensaje_personalizado[:50]}...)")
        else:
            logger.info(f"Autorizacion actualizada en Supabase: {key} -> {status}")
        return True

    # Fallback to memory
    if key in _memory_authorizations:
        _memory_authorizations[key]["status"] = status
        _memory_authorizations[key]["responded_at"] = datetime.now().isoformat()
        if mensaje_personalizado:
            _memory_authorizations[key]["mensaje_personalizado"] = mensaje_personalizado
            logger.info(f"Autorizacion actualizada en MEMORIA: {key} -> {status} (mensaje: {mensaje_personalizado[:50]}...)")
        else:
            logger.info(f"Autorizacion actualizada en MEMORIA: {key} -> {status}")
        return True

    return False


def get_all_authorizations() -> Dict[str, Dict[str, Any]]:
    """Retorna todas las autorizaciones (Supabase + memoria)."""
    # Get from Supabase
    supabase_auths = _supabase_get_all()

    # Merge with memory (memory takes precedence for conflicts)
    all_auths = {**supabase_auths, **_memory_authorizations}

    return all_auths


def clear_old_authorizations(max_age_minutes: int = 30) -> int:
    """Limpia autorizaciones viejas."""
    # Clean Supabase
    supabase_count = _supabase_cleanup_old()

    # Clean memory
    now = datetime.now()
    to_delete = []
    for key, auth in _memory_authorizations.items():
        try:
            timestamp = datetime.fromisoformat(auth.get("timestamp", now.isoformat()))
            age = (now - timestamp).total_seconds() / 60
            if age > max_age_minutes:
                to_delete.append(key)
        except Exception:
            pass

    for key in to_delete:
        del _memory_authorizations[key]
        logger.info(f"Autorizacion expirada eliminada de memoria: {key}")

    return supabase_count + len(to_delete)

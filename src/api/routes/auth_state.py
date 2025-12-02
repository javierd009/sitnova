"""
Estado de autorizaciones pendientes.
Módulo compartido entre tools.py y webhooks.py
"""
from datetime import datetime
from loguru import logger

# Almacén temporal de autorizaciones pendientes
# En producción usar Redis o Supabase
pending_authorizations = {}


def get_pending_authorization(phone: str):
    """Busca autorización pendiente por teléfono."""
    # Normalizar número
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    for key, auth in pending_authorizations.items():
        if clean_phone in key or key in clean_phone:
            return key, auth
    return None, None


def get_authorization_by_apartment(apartment: str):
    """Busca autorización pendiente por apartamento (retorna la más reciente)."""
    apt_normalized = apartment.lower().replace(" ", "")
    matches = []

    # Buscar todas las autorizaciones para este apartamento
    for key, auth in pending_authorizations.items():
        apt_stored = auth.get("apartment", "").lower().replace(" ", "")
        if apt_normalized in apt_stored or apt_stored in apt_normalized:
            matches.append((key, auth))

    if not matches:
        return None, None

    # Ordenar por timestamp (más reciente primero)
    matches.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)

    # Retornar la más reciente
    return matches[0]


def set_pending_authorization(phone: str, apartment: str, visitor_name: str):
    """Guarda autorización pendiente."""
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")
    pending_authorizations[clean_phone] = {
        "apartment": apartment,
        "visitor_name": visitor_name,
        "status": "pendiente",
        "timestamp": datetime.now().isoformat(),
    }
    logger.info(f"📋 Autorización pendiente creada: {clean_phone} -> {apartment} ({visitor_name})")
    return clean_phone


def update_authorization(phone: str, status: str):
    """Actualiza estado de autorización."""
    key, auth = get_pending_authorization(phone)
    if auth:
        auth["status"] = status
        auth["responded_at"] = datetime.now().isoformat()
        logger.info(f"📋 Autorización actualizada: {key} -> {status}")
        return True
    return False


def get_all_authorizations():
    """Retorna todas las autorizaciones."""
    return pending_authorizations


def clear_old_authorizations(max_age_minutes: int = 30):
    """Limpia autorizaciones viejas."""
    now = datetime.now()
    to_delete = []
    for key, auth in pending_authorizations.items():
        timestamp = datetime.fromisoformat(auth.get("timestamp", now.isoformat()))
        age = (now - timestamp).total_seconds() / 60
        if age > max_age_minutes:
            to_delete.append(key)

    for key in to_delete:
        del pending_authorizations[key]
        logger.info(f"🗑️ Autorización expirada eliminada: {key}")

    return len(to_delete)

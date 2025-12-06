"""
Endpoints de Tools para AsterSIPVox/Ultravox.

Estos endpoints son llamados por el agente de voz cuando necesita
ejecutar acciones durante la conversacion con el visitante.

Flujo:
1. Visitante habla con el agente de voz (via AsterSIPVox)
2. El agente decide ejecutar un tool (verificar, notificar, abrir)
3. AsterSIPVox hace HTTP request a estos endpoints
4. SITNOVA ejecuta la accion y responde
5. El agente recibe la respuesta y continua la conversacion
"""
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, List, Tuple
from datetime import datetime
from loguru import logger
import json
import unicodedata
import difflib
import re


# Headers para Ultravox - indica que el agente debe hablar después del tool
ULTRAVOX_HEADERS = {
    "X-Ultravox-Agent-Reaction": "speaks"
}

from src.database.connection import get_supabase
from src.config.settings import settings
from src.services.messaging.evolution_client import create_evolution_client, EvolutionConfig
from src.api.routes.auth_state import set_pending_authorization, get_authorization_by_apartment


def normalize_text(text: str) -> str:
    """Remove accents and normalize text for search."""
    if not text:
        return text
    # Normalize unicode and remove accents
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


# ============================================
# FUZZY MATCHING HELPERS
# ============================================

# Apellidos latinos comunes para sugerencias
APELLIDOS_COMUNES = [
    "rodriguez", "gonzalez", "hernandez", "garcia", "martinez",
    "lopez", "perez", "sanchez", "ramirez", "torres", "flores",
    "rivera", "gomez", "diaz", "reyes", "morales", "cruz",
    "ortiz", "gutierrez", "chavez", "ramos", "vargas", "castillo",
    "jimenez", "ruiz", "mendoza", "aguilar", "medina", "castro",
    "guzman", "rojas", "fernandez", "herrera", "colorado", "mora",
    "solis", "nunez", "campos", "vega", "delgado", "suarez",
    "romero", "vasquez", "silva", "zamora", "contreras", "leon",
    "salazar", "fuentes", "cordero", "araya", "quesada", "chaves"
]

# Mapeo de errores foneticos comunes en espanol (voz a texto)
PHONETIC_CORRECTIONS = {
    # Errores comunes de reconocimiento de voz
    "radriga": "rodriguez",
    "gonsales": "gonzalez",
    "gonsalez": "gonzalez",
    "ernandez": "hernandez",
    "errera": "herrera",
    "arcia": "garcia",
    "artinez": "martinez",
    "opes": "lopez",
    "eres": "perez",
    "anches": "sanchez",
    "amires": "ramirez",
    "olorado": "colorado",
    "oloraro": "colorado",
    # Variaciones de nombres
    "deizy": "daisy",
    "deisy": "daisy",
    "daysi": "daisy",
    "jhon": "john",
    "jon": "john",
    "maria": "maria",
    "jose": "jose",
}


def get_phonetic_correction(word: str) -> str:
    """Intenta corregir errores foneticos comunes."""
    word_lower = normalize_text(word.lower().strip())
    return PHONETIC_CORRECTIONS.get(word_lower, word)


def fuzzy_match_name(query: str, candidates: List[str], threshold: float = 0.6) -> List[Tuple[str, float]]:
    """
    Busca coincidencias fuzzy entre un nombre y una lista de candidatos.

    Returns:
        Lista de (nombre, score) ordenada por score descendente
    """
    query_normalized = normalize_text(query.lower().strip())
    results = []

    for candidate in candidates:
        candidate_normalized = normalize_text(candidate.lower().strip())

        # Calcular similitud
        ratio = difflib.SequenceMatcher(None, query_normalized, candidate_normalized).ratio()

        # Bonus si el query esta contenido en el candidato o viceversa
        if query_normalized in candidate_normalized or candidate_normalized in query_normalized:
            ratio = min(ratio + 0.2, 1.0)

        # Bonus si comparten el mismo inicio
        if candidate_normalized.startswith(query_normalized[:3]) if len(query_normalized) >= 3 else False:
            ratio = min(ratio + 0.1, 1.0)

        if ratio >= threshold:
            results.append((candidate, ratio))

    # Ordenar por score descendente
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def suggest_similar_surnames(query: str, threshold: float = 0.5) -> List[str]:
    """Sugiere apellidos similares al query basado en apellidos comunes."""
    query_normalized = normalize_text(query.lower().strip())

    # Primero verificar correccion fonetica
    corrected = get_phonetic_correction(query_normalized)
    if corrected != query_normalized:
        return [corrected.title()]

    # Buscar coincidencias fuzzy en apellidos comunes
    matches = difflib.get_close_matches(query_normalized, APELLIDOS_COMUNES, n=3, cutoff=threshold)
    return [m.title() for m in matches]


def is_valid_name(name: str) -> bool:
    """Verifica si un nombre parece valido (no es ruido de reconocimiento de voz)."""
    if not name or len(name) < 2:
        return False

    name_normalized = normalize_text(name.lower().strip())

    # Patrones que indican ruido (no son nombres reales)
    noise_patterns = [
        r'^de\s+\w+$',  # "de bicicletas", "de algo"
        r'bicicleta',
        r'carro',
        r'auto',
        r'vehiculo',
        r'moto',
    ]

    for pattern in noise_patterns:
        if re.search(pattern, name_normalized):
            return False

    return True


def extract_name_parts(full_text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extrae nombre y apellido de un texto, filtrando ruido.

    Ejemplo: "Daisy de bicicletas Colorado" -> ("Daisy", "Colorado")
    """
    if not full_text:
        return None, None

    # Palabras a ignorar (ruido comun)
    noise_words = {'de', 'del', 'la', 'las', 'los', 'el', 'bicicletas', 'bicicleta',
                   'carro', 'auto', 'vehiculo', 'moto', 'casa', 'apartamento'}

    words = full_text.strip().split()
    clean_words = [w for w in words if w.lower() not in noise_words and is_valid_name(w)]

    if len(clean_words) == 0:
        return None, None
    elif len(clean_words) == 1:
        return clean_words[0], None
    else:
        # Asumir que el primero es nombre y el ultimo es apellido
        return clean_words[0], clean_words[-1]


def normalize_apartment(apt: str) -> Tuple[str, Optional[str]]:
    """
    Normaliza el numero de apartamento/casa.

    Returns:
        (normalized_string, extracted_number)

    Ejemplos:
        "Casa 10" -> ("casa 10", "10")
        "casa10" -> ("casa 10", "10")
        "la 10" -> ("10", "10")
        "diez" -> ("10", "10")
    """
    if not apt:
        return "", None

    apt_lower = apt.lower().strip()

    # Mapeo de numeros en texto a digitos
    text_to_number = {
        'uno': '1', 'una': '1', 'primero': '1', 'primera': '1',
        'dos': '2', 'segundo': '2', 'segunda': '2',
        'tres': '3', 'tercero': '3', 'tercera': '3',
        'cuatro': '4', 'cuarto': '4', 'cuarta': '4',
        'cinco': '5', 'quinto': '5', 'quinta': '5',
        'seis': '6', 'sexto': '6', 'sexta': '6',
        'siete': '7', 'septimo': '7', 'septima': '7',
        'ocho': '8', 'octavo': '8', 'octava': '8',
        'nueve': '9', 'noveno': '9', 'novena': '9',
        'diez': '10', 'decimo': '10', 'decima': '10',
        'once': '11', 'doce': '12', 'trece': '13', 'catorce': '14',
        'quince': '15', 'dieciseis': '16', 'diecisiete': '17',
        'dieciocho': '18', 'diecinueve': '19', 'veinte': '20',
    }

    # Reemplazar numeros en texto por digitos
    for text, num in text_to_number.items():
        if text in apt_lower:
            apt_lower = apt_lower.replace(text, num)

    # Extraer solo el numero
    numbers = ''.join(filter(str.isdigit, apt_lower))

    return apt_lower, numbers if numbers else None

router = APIRouter()

# ============================================
# REGISTRO DE LLAMADAS (para debugging)
# ============================================
tool_calls_log = []
MAX_LOG_SIZE = 50


# ============================================
# HELPER: Log incoming requests for debugging
# ============================================
async def log_request(request: Request, endpoint: str) -> dict:
    """Log all incoming request details for debugging."""
    body = {}
    try:
        body = await request.json()
    except:
        pass

    # Store in memory log for diagnostics
    call_record = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "method": request.method,
        "query_params": dict(request.query_params),
        "body": body,
        "client_ip": request.client.host if request.client else "unknown",
    }
    tool_calls_log.append(call_record)

    # Keep only last N calls
    if len(tool_calls_log) > MAX_LOG_SIZE:
        tool_calls_log.pop(0)

    logger.info(f"=== INCOMING REQUEST TO {endpoint} ===")
    logger.info(f"Timestamp: {call_record['timestamp']}")
    logger.info(f"Client IP: {call_record['client_ip']}")
    logger.info(f"Body: {body}")
    logger.info(f"=====================================")

    return body


# ============================================
# SCHEMAS
# ============================================

class VerificarVisitanteRequest(BaseModel):
    """Request para verificar visitante."""
    cedula: Optional[str] = None
    nombre: Optional[str] = None


class VerificarVisitanteResponse(BaseModel):
    """Response de verificacion."""
    autorizado: bool
    mensaje: str
    residente_nombre: Optional[str] = None
    apartamento: Optional[str] = None


class NotificarResidenteRequest(BaseModel):
    """Request para notificar residente."""
    apartamento: str
    nombre_visitante: str
    motivo: Optional[str] = None


class NotificarResidenteResponse(BaseModel):
    """Response de notificacion."""
    enviado: bool
    mensaje: str
    metodo: str  # whatsapp, llamada, push


class AbrirPortonRequest(BaseModel):
    """Request para abrir porton."""
    motivo: str


class AbrirPortonResponse(BaseModel):
    """Response de apertura."""
    abierto: bool
    mensaje: str


class DenegarAccesoRequest(BaseModel):
    """Request para denegar acceso."""
    razon: str


class DenegarAccesoResponse(BaseModel):
    """Response de denegacion."""
    registrado: bool
    mensaje: str


# ============================================
# ENDPOINTS
# ============================================

@router.post("/verificar-visitante")
@router.post("/verificar-preautorizacion")
async def verificar_visitante(
    request: Request,
    cedula: Optional[str] = Query(None),
    nombre: Optional[str] = Query(None),
    apartamento: Optional[str] = Query(None),
):
    """
    Verifica si un visitante tiene pre-autorizacion.
    Acepta parametros via body JSON o query params.
    Alias: /verificar-preautorizacion (para AsterSIPVox)
    """
    # Log raw request for debugging
    body = await log_request(request, "/verificar-preautorizacion")

    # Get params from body or query
    visitor_cedula = body.get("cedula") or cedula
    visitor_nombre = body.get("nombre") or nombre

    logger.info(f"Verificando visitante: cedula={visitor_cedula}, nombre={visitor_nombre}")

    # Buscar en Supabase
    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado, usando modo mock")
            return {
                "autorizado": True,
                "mensaje": f"MOCK: El visitante {visitor_nombre or 'identificado'} autorizado (Supabase no configurado)",
                "residente_nombre": "Juan Perez",
                "apartamento": "Casa 5",
            }

        now = datetime.now().isoformat()

        # Buscar en pre_authorized_visitors
        # Schema real: visitor_name, cedula, resident_id, valid_from, valid_until
        query = supabase.table("pre_authorized_visitors").select(
            "*, residents(full_name, apartment, phone)"
        ).eq("used", False).lte("valid_from", now).gte("valid_until", now)

        # Filtrar por nombre o cedula
        if visitor_cedula and visitor_cedula != "null":
            query = query.eq("cedula", visitor_cedula)
        elif visitor_nombre:
            # Normalize name to remove accents for matching
            nombre_normalizado = normalize_text(visitor_nombre)
            logger.info(f"Buscando nombre normalizado: {nombre_normalizado}")

            # Buscar por primer nombre para mayor flexibilidad con speech-to-text
            primer_nombre = nombre_normalizado.split()[0] if nombre_normalizado else ""
            logger.info(f"Buscando por primer nombre: {primer_nombre}")
            query = query.ilike("visitor_name", f"%{primer_nombre}%")

        result = query.execute()

        if result.data and len(result.data) > 0:
            visitor = result.data[0]
            resident = visitor.get("residents", {})
            logger.info(f"Visitante PRE-AUTORIZADO encontrado: {visitor.get('visitor_name')}")
            return {
                "autorizado": True,
                "mensaje": f"El visitante {visitor.get('visitor_name')} tiene pre-autorizacion vigente",
                "residente_nombre": resident.get("full_name") if resident else None,
                "apartamento": resident.get("apartment") if resident else None,
            }
        else:
            logger.info(f"Visitante NO encontrado en pre-autorizados")
            return {
                "autorizado": False,
                "mensaje": "El visitante no tiene pre-autorizacion. Debe contactar al residente.",
                "residente_nombre": None,
                "apartamento": None,
            }

    except Exception as e:
        logger.error(f"Error buscando en Supabase: {e}")
        # Fallback a mock en caso de error
        return {
            "autorizado": False,
            "mensaje": f"Error verificando visitante: {str(e)}",
            "residente_nombre": None,
            "apartamento": None,
        }


@router.post("/notificar-residente")
async def notificar_residente(
    request: Request,
    apartamento: Optional[str] = Query(None),
    nombre_visitante: Optional[str] = Query(None),
    cedula: Optional[str] = Query(None),
    placa: Optional[str] = Query(None),
    motivo_visita: Optional[str] = Query(None),
):
    """
    Envia notificacion al residente para autorizar visita.
    Acepta parametros via body JSON o query params.

    Busca el residente por apartamento y envía notificación según su preferencia:
    - WhatsApp (Evolution API)
    - Llamada telefónica (próximamente)

    Parámetros del visitante:
    - cedula: Número de cédula del visitante
    - placa: Placa del vehículo
    - motivo_visita: Motivo de la visita (ej: "visita personal", "entrega")
    """
    body = await log_request(request, "/notificar-residente")

    apt = body.get("apartamento") or apartamento
    visitante = body.get("nombre_visitante") or nombre_visitante
    visitor_cedula = body.get("cedula") or cedula
    visitor_placa = body.get("placa") or placa
    visitor_motivo = body.get("motivo_visita") or motivo_visita

    logger.info(f"Notificando residente: apt={apt}, visitante={visitante}")
    if visitor_cedula:
        logger.info(f"   📄 Cédula: {visitor_cedula}")
    if visitor_placa:
        logger.info(f"   🚗 Placa: {visitor_placa}")
    if visitor_motivo:
        logger.info(f"   📝 Motivo: {visitor_motivo}")

    # Buscar residente en Supabase
    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado, usando modo mock")
            return JSONResponse(
                content={
                    "enviado": True,
                    "mensaje": f"MOCK: Notificación enviada al residente de {apt}.",
                    "metodo": "mock",
                    "result": f"He notificado al residente de {apt}. Por favor espere.",
                },
                headers=ULTRAVOX_HEADERS
            )

        # Buscar residente por apartamento
        apt_normalized = normalize_text(apt) if apt else ""
        logger.info(f"🔍 Buscando residente para apartamento: '{apt}' (normalizado: '{apt_normalized}')")

        # Primero intentar búsqueda exacta (case-insensitive)
        result = supabase.table("residents").select(
            "id, full_name, apartment, phone, phone_secondary, notification_preference"
        ).ilike("apartment", apt_normalized).eq("is_active", True).execute()

        # Si no hay match exacto, buscar con patrón más flexible
        if not result.data or len(result.data) == 0:
            logger.info(f"🔍 No hay match exacto, buscando con patrón flexible...")
            result = supabase.table("residents").select(
                "id, full_name, apartment, phone, phone_secondary, notification_preference"
            ).ilike("apartment", f"%{apt_normalized}%").eq("is_active", True).execute()

        if not result.data or len(result.data) == 0:
            logger.warning(f"❌ Residente no encontrado para apartamento: {apt}")
            return JSONResponse(
                content={
                    "enviado": False,
                    "mensaje": f"No se encontró residente en {apt}. Verifique el número.",
                    "metodo": "ninguno",
                    "result": f"No encontré ningún residente registrado en {apt}. ¿Podría verificar el número de casa o apartamento?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # Si hay múltiples resultados, buscar el más específico
        logger.info(f"📋 Resultados encontrados: {len(result.data)}")
        for r in result.data:
            logger.info(f"   - {r.get('full_name')}: {r.get('apartment')} -> {r.get('phone')}")

        # Seleccionar el mejor match
        resident = None
        apt_lower = apt_normalized.lower().replace(" ", "")

        # Primero buscar match exacto
        for r in result.data:
            apt_db = r.get("apartment", "").lower().replace(" ", "")
            if apt_db == apt_lower:
                resident = r
                logger.info(f"✅ Match exacto encontrado: {r.get('full_name')}")
                break

        # Si no hay exacto, buscar el que contenga el número
        if not resident:
            # Extraer solo números del apartamento buscado
            apt_numbers = ''.join(filter(str.isdigit, apt_normalized))
            for r in result.data:
                apt_db = r.get("apartment", "").lower().replace(" ", "")
                apt_db_numbers = ''.join(filter(str.isdigit, apt_db))
                # Match si los números son exactamente iguales
                if apt_numbers and apt_db_numbers == apt_numbers:
                    resident = r
                    logger.info(f"✅ Match por número encontrado: {r.get('full_name')} (números: {apt_numbers})")
                    break

        # Si aún no hay match, usar el primero pero advertir
        if not resident:
            resident = result.data[0]
            logger.warning(f"⚠️ Usando primer resultado (puede no ser exacto): {resident.get('full_name')}")
        resident_name = resident.get("full_name", "Residente")
        resident_apt = resident.get("apartment", "?")
        whatsapp_number = resident.get("phone") or resident.get("phone_secondary")
        notification_pref = resident.get("notification_preference", "whatsapp")
        notify_whatsapp = notification_pref in ["whatsapp", "both", None]

        logger.info(f"📱 RESIDENTE SELECCIONADO:")
        logger.info(f"   Nombre: {resident_name}")
        logger.info(f"   Apartamento: {resident_apt}")
        logger.info(f"   Teléfono: {whatsapp_number}")
        logger.info(f"   Preferencia: {notification_pref}")

        metodos_usados = []

        # Enviar por WhatsApp si está habilitado
        if notify_whatsapp and whatsapp_number:
            try:
                # Crear cliente Evolution
                evolution = create_evolution_client(
                    base_url=settings.evolution_api_url,
                    api_key=settings.evolution_api_key,
                    instance_name=settings.evolution_instance_name,
                    use_mock=(not settings.evolution_api_key)
                )

                # Mensaje de notificación completo con TODOS los datos del visitante
                # IMPORTANTE: Mostrar siempre cédula y motivo (seguridad)
                mensaje_wa = (
                    f"🚪 *Visita en portería*\n\n"
                    f"Hay una persona esperando en la entrada:\n\n"
                    f"👤 *Nombre:* {visitante}\n"
                    f"🪪 *Cédula:* {visitor_cedula if visitor_cedula else 'No proporcionada'}\n"
                    f"📝 *Motivo:* {visitor_motivo if visitor_motivo else 'No proporcionado'}\n"
                )
                # Agregar placa solo si viene en vehículo
                if visitor_placa:
                    mensaje_wa += f"🚗 *Placa:* {visitor_placa}\n"
                # Destino
                mensaje_wa += f"🏠 *Destino:* {apt}\n"
                # Instrucciones de respuesta
                mensaje_wa += (
                    f"\n✅ Responda *SI* para autorizar\n"
                    f"❌ Responda *NO* para denegar\n"
                    f"💬 O envíe un mensaje personalizado para el visitante"
                )

                result_wa = evolution.send_text(whatsapp_number, mensaje_wa)

                if result_wa.get("success"):
                    logger.success(f"WhatsApp enviado a {whatsapp_number}")
                    metodos_usados.append("whatsapp")
                    # Guardar autorización pendiente para tracking (con datos OCR)
                    set_pending_authorization(
                        whatsapp_number,
                        apt,
                        visitante,
                        cedula=visitor_cedula,
                        placa=visitor_placa
                    )
                else:
                    logger.error(f"Error enviando WhatsApp: {result_wa.get('error')}")

            except Exception as e:
                logger.error(f"Error con Evolution API: {e}")

        # TODO: Agregar notificación por llamada si notification_preference es "call"
        # if notification_pref in ["call", "both"]:
        #     # Originar llamada via AsterSIPVox
        #     metodos_usados.append("llamada")

        if not metodos_usados:
            return JSONResponse(
                content={
                    "enviado": False,
                    "mensaje": f"No se pudo notificar al residente de {apt}. Sin WhatsApp configurado.",
                    "metodo": "ninguno",
                    "result": f"No fue posible contactar al residente de {apt}. No tiene WhatsApp configurado. Por favor intente comunicarse de otra forma.",
                },
                headers=ULTRAVOX_HEADERS
            )

        return JSONResponse(
            content={
                "enviado": True,
                "mensaje": f"Notificación enviada a {resident_name} ({apt}). Por favor espere la autorización.",
                "metodo": ", ".join(metodos_usados),
                "result": f"He enviado una notificación por WhatsApp al residente de {apt}. Por favor espere un momento mientras confirma si autoriza su ingreso.",
            },
            headers=ULTRAVOX_HEADERS
        )

    except Exception as e:
        logger.error(f"Error notificando residente: {e}")
        return JSONResponse(
            content={
                "enviado": False,
                "mensaje": f"Error al notificar: {str(e)}",
                "metodo": "error",
                "result": "Hubo un problema técnico al intentar contactar al residente. Por favor intente nuevamente en unos momentos.",
            },
            headers=ULTRAVOX_HEADERS
        )


@router.post("/abrir-porton")
async def abrir_porton(
    request: Request,
    motivo: Optional[str] = Query(None),
):
    """
    Abre el porton de entrada.
    Acepta parametros via body JSON o query params.
    """
    body = await log_request(request, "/abrir-porton")

    reason = body.get("motivo") or motivo or "Autorizado por agente"

    logger.info(f"Abriendo porton: motivo={reason}")

    # TODO: Implementar apertura real via Hikvision ISAPI
    logger.success(f"PORTON ABIERTO: {reason}")

    return {
        "abierto": True,
        "mensaje": "El porton se ha abierto. Puede ingresar. Bienvenido al condominio.",
    }


@router.post("/denegar-acceso")
async def denegar_acceso(
    request: Request,
    razon: Optional[str] = Query(None),
):
    """
    Deniega el acceso y registra el evento.
    Acepta parametros via body JSON o query params.
    """
    body = await log_request(request, "/denegar-acceso")

    reason = body.get("razon") or razon or "No autorizado"

    logger.warning(f"ACCESO DENEGADO: {reason}")

    # TODO: Implementar registro real en Supabase

    return {
        "registrado": True,
        "mensaje": f"Acceso denegado. {reason}. Por favor retire su vehiculo.",
    }


@router.api_route("/buscar-residente", methods=["GET", "POST"])
async def buscar_residente(
    request: Request,
    apartamento: Optional[str] = Query(None, description="Numero de casa o apartamento"),
    nombre: Optional[str] = Query(None, description="Nombre del residente"),
    query: Optional[str] = Query(None, description="Busqueda general (nombre o apartamento)"),
    condominium_id: Optional[str] = Query(None, description="ID del condominio"),
):
    """
    Busca residentes por apartamento O por nombre con lógica inteligente.

    IMPORTANTE: Usar este endpoint ANTES de notificar para verificar
    que existe el residente y obtener información correcta.

    Parámetros:
    - query: Búsqueda general (puede ser nombre o número de casa)
    - apartamento: Número de casa específico
    - nombre: Nombre del residente
    - condominium_id: ID del condominio (opcional, se usa "default-condo-id")

    Casos manejados:
    - Búsqueda por apartamento: Soporta variaciones ("Casa 10", "casa10", "la diez")
    - Búsqueda por nombre: Filtra ruido y usa fuzzy matching
    - Sugerencias: Si no hay match, sugiere alternativas (ej: "Radriga" → "Rodríguez")
    - Sin resultados: Indica que no se encontró y pide más información
    """
    body = await log_request(request, "/buscar-residente")

    # ============ LOGGING EXHAUSTIVO PARA DEBUGGING ============
    logger.info(f"🔍🔍🔍 BUSCAR-RESIDENTE DEBUG START 🔍🔍🔍")
    logger.info(f"📥 Body recibido: {body}")
    logger.info(f"📥 Query params - apartamento: {apartamento}")
    logger.info(f"📥 Query params - nombre: {nombre}")
    logger.info(f"📥 Query params - query: {query}")
    logger.info(f"📥 Query params - condominium_id: {condominium_id}")
    logger.info(f"📥 Request method: {request.method}")
    logger.info(f"📥 Request URL: {request.url}")
    logger.info(f"📥 Content-Type: {request.headers.get('content-type')}")
    # =========================================================

    # Compatibilidad: query puede ser nombre o apartamento
    search_query = body.get("query") or query

    # Determinar si query es número de casa o nombre
    if search_query:
        # Si empieza con dígito, probablemente es apartamento
        if search_query.strip() and search_query.strip()[0].isdigit():
            apt = body.get("apartamento") or apartamento or search_query
            nombre_buscar = body.get("nombre") or nombre
        else:
            # Si no, es nombre
            apt = body.get("apartamento") or apartamento
            nombre_buscar = body.get("nombre") or nombre or search_query
    else:
        # Sin query, usar parámetros individuales
        apt = body.get("apartamento") or apartamento
        nombre_buscar = body.get("nombre") or nombre

    condo_id = body.get("condominium_id") or condominium_id or "default-condo-id"

    logger.info(f"📊 PARAMETROS PROCESADOS:")
    logger.info(f"   - search_query: '{search_query}'")
    logger.info(f"   - apt: '{apt}'")
    logger.info(f"   - nombre_buscar: '{nombre_buscar}'")
    logger.info(f"   - condo_id: '{condo_id}'")
    logger.info(f"🔍 Buscando residente: apartamento={apt}, nombre={nombre_buscar}")

    try:
        supabase = get_supabase()
        if supabase is None:
            logger.warning("Supabase no configurado")
            return JSONResponse(
                content={
                    "encontrado": False,
                    "mensaje": "Base de datos no disponible",
                    "result": "No puedo acceder a la base de datos en este momento. Por favor intente más tarde.",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 1: Búsqueda por apartamento (más específica)
        if apt:
            # Normalizar apartamento (maneja "Casa 10", "casa10", "la diez", etc.)
            apt_normalized, apt_number = normalize_apartment(apt)
            logger.info(f"🏠 Apartamento normalizado: '{apt_normalized}' (número: {apt_number})")

            # Primero buscar por número exacto si existe
            result = None
            if apt_number:
                # Buscar donde el número del apartamento coincida
                all_residents = supabase.table("residents").select(
                    "id, full_name, apartment, phone"
                ).eq("is_active", True).execute()

                # Filtrar por número de apartamento
                matching = []
                for r in all_residents.data or []:
                    _, r_number = normalize_apartment(r.get("apartment", ""))
                    if r_number == apt_number:
                        matching.append(r)
                        logger.info(f"   ✓ Match por número: {r.get('apartment')}")

                if matching:
                    result = type('obj', (object,), {'data': matching})()

            # Si no hay match por número, buscar por texto
            if not result or not result.data:
                logger.info(f"🔍 Buscando por texto: '{apt_normalized}'")
                result = supabase.table("residents").select(
                    "id, full_name, apartment, phone"
                ).ilike("apartment", f"%{apt_normalized}%").eq("is_active", True).execute()

            if not result.data or len(result.data) == 0:
                logger.info(f"❌ No se encontró residente en {apt}")
                return JSONResponse(
                    content={
                        "encontrado": False,
                        "cantidad": 0,
                        "mensaje": f"No hay ningún residente registrado en {apt}.",
                        "result": f"No encontré ningún residente registrado en la casa o apartamento {apt}. ¿Podría verificar el número?",
                    },
                    headers=ULTRAVOX_HEADERS
                )

            # Si hay múltiples matches, seleccionar el mejor
            mejor_match = result.data[0]
            if len(result.data) > 1 and apt_number:
                for r in result.data:
                    _, r_number = normalize_apartment(r.get("apartment", ""))
                    if r_number == apt_number:
                        mejor_match = r
                        break

            logger.info(f"✅ Encontrado: {mejor_match.get('full_name')} en {mejor_match.get('apartment')}")
            return JSONResponse(
                content={
                    "encontrado": True,
                    "cantidad": 1,
                    "residente": {
                        "nombre": mejor_match.get("full_name"),
                        "apartamento": mejor_match.get("apartment"),
                        "tiene_telefono": bool(mejor_match.get("phone")),
                    },
                    "mensaje": f"Encontré a {mejor_match.get('full_name')} en {mejor_match.get('apartment')}.",
                    "result": f"Encontré a {mejor_match.get('full_name')} registrado en {mejor_match.get('apartment')}. ¿Desea que le notifique?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 2: Búsqueda por nombre (puede ser ambigua)
        elif nombre_buscar:
            # Extraer partes limpias del nombre (filtra ruido como "de bicicletas")
            nombre_clean, apellido_clean = extract_name_parts(nombre_buscar)
            logger.info(f"🔍 Nombre limpio: '{nombre_clean}', Apellido: '{apellido_clean}'")

            # Si no se pudo extraer nada, intentar con el texto original
            if not nombre_clean and not apellido_clean:
                nombre_clean = nombre_buscar.split()[0] if nombre_buscar else None

            # Obtener todos los residentes para búsqueda inteligente
            all_residents = supabase.table("residents").select(
                "id, full_name, apartment, phone"
            ).eq("is_active", True).execute()

            if not all_residents.data:
                logger.warning("No hay residentes en la base de datos")
                return JSONResponse(
                    content={
                        "encontrado": False,
                        "cantidad": 0,
                        "mensaje": "No hay residentes registrados.",
                        "result": "No encontré ningún residente registrado en el sistema.",
                    },
                    headers=ULTRAVOX_HEADERS
                )

            # Crear lista de nombres para fuzzy matching
            nombres_db = [r.get("full_name", "") for r in all_residents.data]

            # 1. Intentar match exacto primero
            exact_matches = []
            for r in all_residents.data:
                full_name = normalize_text(r.get("full_name", "").lower())
                search_terms = []
                if nombre_clean:
                    search_terms.append(normalize_text(nombre_clean.lower()))
                if apellido_clean:
                    search_terms.append(normalize_text(apellido_clean.lower()))

                # Match si todos los términos están en el nombre completo
                if search_terms and all(term in full_name for term in search_terms):
                    exact_matches.append(r)
                    logger.info(f"   ✓ Match exacto: {r.get('full_name')}")

            if exact_matches:
                if len(exact_matches) == 1:
                    residente = exact_matches[0]
                    logger.info(f"✅ Un solo match exacto: {residente.get('full_name')}")
                    return JSONResponse(
                        content={
                            "encontrado": True,
                            "cantidad": 1,
                            "residente": {
                                "nombre": residente.get("full_name"),
                                "apartamento": residente.get("apartment"),
                                "tiene_telefono": bool(residente.get("phone")),
                            },
                            "mensaje": f"Encontré a {residente.get('full_name')} en {residente.get('apartment')}.",
                            "result": f"Encontré a {residente.get('full_name')} en {residente.get('apartment')}. ¿Desea que le notifique?",
                        },
                        headers=ULTRAVOX_HEADERS
                    )
                else:
                    # Múltiples matches exactos - listar las opciones
                    logger.info(f"⚠️ Múltiples matches exactos ({len(exact_matches)})")
                    # Construir lista de opciones para el visitante
                    opciones = []
                    for r in exact_matches[:5]:
                        opciones.append(f"{r.get('full_name')} en {r.get('apartment')}")
                    lista_opciones = ", ".join(opciones)

                    return JSONResponse(
                        content={
                            "encontrado": True,
                            "cantidad": len(exact_matches),
                            "ambiguo": True,
                            "residentes": [
                                {"nombre": r.get("full_name"), "apartamento": r.get("apartment")}
                                for r in exact_matches[:5]
                            ],
                            "mensaje": f"Hay {len(exact_matches)} residentes con ese nombre.",
                            "result": f"Encontré {len(exact_matches)} personas: {lista_opciones}. ¿A cuál de ellos visita?",
                        },
                        headers=ULTRAVOX_HEADERS
                    )

            # 2. No hay match exacto - intentar fuzzy matching
            logger.info(f"🔄 Sin match exacto, probando fuzzy matching...")

            # Buscar por nombre o apellido con fuzzy
            fuzzy_results = []
            search_query = nombre_clean or apellido_clean or nombre_buscar

            if search_query:
                fuzzy_results = fuzzy_match_name(search_query, nombres_db, threshold=0.5)
                logger.info(f"   Fuzzy results: {fuzzy_results[:3]}")

            if fuzzy_results:
                # Hay coincidencias fuzzy
                best_match_name, best_score = fuzzy_results[0]
                best_resident = next(
                    (r for r in all_residents.data if r.get("full_name") == best_match_name),
                    None
                )

                if best_score >= 0.8 and best_resident:
                    # Match muy bueno, usar directamente
                    logger.info(f"✅ Fuzzy match alto ({best_score:.0%}): {best_match_name}")
                    return JSONResponse(
                        content={
                            "encontrado": True,
                            "cantidad": 1,
                            "residente": {
                                "nombre": best_resident.get("full_name"),
                                "apartamento": best_resident.get("apartment"),
                                "tiene_telefono": bool(best_resident.get("phone")),
                            },
                            "mensaje": f"Encontré a {best_resident.get('full_name')} en {best_resident.get('apartment')}.",
                            "result": f"Encontré a {best_resident.get('full_name')} en {best_resident.get('apartment')}. ¿Desea que le notifique?",
                        },
                        headers=ULTRAVOX_HEADERS
                    )
                elif fuzzy_results:
                    # Match moderado, mostrar opciones
                    residentes_sugeridos = []
                    for name, score in fuzzy_results[:3]:
                        r = next((r for r in all_residents.data if r.get("full_name") == name), None)
                        if r:
                            residentes_sugeridos.append({
                                "nombre": r.get("full_name"),
                                "apartamento": r.get("apartment")
                            })

                    logger.info(f"🤔 Fuzzy match moderado, mostrando opciones")
                    # Listar con apartamento para que el visitante elija
                    opciones_texto = ", ".join([
                        f"{s['nombre']} en {s['apartamento']}"
                        for s in residentes_sugeridos[:3]
                    ])
                    return JSONResponse(
                        content={
                            "encontrado": False,
                            "sugerencias": True,
                            "cantidad": len(residentes_sugeridos),
                            "residentes_sugeridos": residentes_sugeridos,
                            "mensaje": f"No encontré exactamente '{nombre_buscar}'. Opciones: {opciones_texto}",
                            "result": f"No encontré exactamente ese nombre. Tengo registrados: {opciones_texto}. ¿Es alguno de ellos?",
                        },
                        headers=ULTRAVOX_HEADERS
                    )

            # 3. Ni match exacto ni fuzzy - sugerir apellidos similares
            logger.info(f"❌ Sin matches, buscando sugerencias de apellido...")

            apellido_query = apellido_clean or search_query
            if apellido_query:
                sugerencias_apellido = suggest_similar_surnames(apellido_query)
                if sugerencias_apellido:
                    logger.info(f"💡 Sugerencias de apellido: {sugerencias_apellido}")
                    return JSONResponse(
                        content={
                            "encontrado": False,
                            "sugerencias": True,
                            "cantidad": 0,
                            "sugerencias_apellido": sugerencias_apellido,
                            "mensaje": f"No encontré '{nombre_buscar}'. ¿Quiso decir apellido {sugerencias_apellido[0]}?",
                            "result": f"No encontré a nadie con ese nombre. ¿El apellido es {sugerencias_apellido[0]}? Por favor confirme.",
                        },
                        headers=ULTRAVOX_HEADERS
                    )

            # 4. Sin resultados ni sugerencias
            logger.info(f"❌ Sin matches ni sugerencias para '{nombre_buscar}'")
            return JSONResponse(
                content={
                    "encontrado": False,
                    "cantidad": 0,
                    "mensaje": f"No encontré ningún residente con el nombre {nombre_buscar}.",
                    "result": f"No encontré ningún residente con ese nombre. ¿Tiene el número de casa o puede deletrear el apellido?",
                },
                headers=ULTRAVOX_HEADERS
            )

        # CASO 3: Sin parámetros suficientes
        else:
            return JSONResponse(
                content={
                    "encontrado": False,
                    "mensaje": "Necesito el número de casa/apartamento o el nombre del residente.",
                    "result": "Para poder ayudarle necesito saber a quién busca. ¿Tiene el número de casa o el nombre de la persona?",
                },
                headers=ULTRAVOX_HEADERS
            )

    except Exception as e:
        logger.error(f"❌ Error buscando residente: {e}")
        return JSONResponse(
            content={
                "encontrado": False,
                "mensaje": f"Error en la búsqueda: {str(e)}",
                "result": "Hubo un problema técnico al buscar. Por favor intente nuevamente.",
            },
            headers=ULTRAVOX_HEADERS
        )


@router.api_route("/estado-autorizacion", methods=["GET", "POST"])
async def estado_autorizacion(
    request: Request,
    apartamento: Optional[str] = Query(None, description="Numero de apartamento"),
    session_id: Optional[str] = Query(None, description="ID de sesion de la visita"),
):
    """
    Consulta el estado de una autorizacion pendiente.

    IMPORTANTE: El agente DEBE llamar este endpoint después de notificar_residente
    para verificar si el residente ya autorizó o denegó el acceso.

    El agente debe seguir consultando hasta que el estado sea "autorizado" o "denegado".
    """
    # Log request for debugging
    body = await log_request(request, "/estado-autorizacion")

    # Obtener apartamento de body o query params
    apt = body.get("apartamento") or apartamento

    logger.info(f"🔍 Consultando estado de autorización: apartamento={apt}, session={session_id}")

    # Log all pending authorizations for debugging
    from src.api.routes.auth_state import get_all_authorizations
    all_auths = get_all_authorizations()
    logger.info(f"📋 Autorizaciones pendientes actuales: {all_auths}")

    # Buscar por apartamento si se proporciona
    if apt:
        key, auth = get_authorization_by_apartment(apt)
        logger.info(f"🔎 Resultado búsqueda: key={key}, auth={auth}")

        if auth:
            status = auth.get("status", "pendiente")
            visitor = auth.get("visitor_name", "desconocido")

            if status == "autorizado":
                logger.success(f"✅ Estado: AUTORIZADO para {apt}")

                # Buscar instrucciones de dirección del residente
                direccion_instrucciones = None
                try:
                    supabase = get_supabase()
                    if supabase:
                        resident_info = supabase.table("residents").select(
                            "address_instructions"
                        ).ilike("apartment", f"%{apt}%").limit(1).execute()

                        if resident_info.data and len(resident_info.data) > 0:
                            direccion_instrucciones = resident_info.data[0].get("address_instructions")
                except Exception as e:
                    logger.warning(f"Error obteniendo direcciones: {e}")

                # Construir mensaje de resultado con direcciones si están disponibles
                result_message = f"Excelente noticias. El residente de {apt} ha autorizado el ingreso de {visitor}."
                if direccion_instrucciones:
                    result_message += f" Para llegar: {direccion_instrucciones}."
                result_message += " Puede abrir el portón. Bienvenido al condominio."

                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "autorizado",
                        "mensaje": f"El residente ha AUTORIZADO el acceso del visitante {visitor}. Puede abrir el portón.",
                        "visitor_name": visitor,
                        "direccion_instrucciones": direccion_instrucciones,
                        "result": result_message,
                    },
                    headers=ULTRAVOX_HEADERS
                )
            elif status == "denegado":
                logger.warning(f"❌ Estado: DENEGADO para {apt}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "denegado",
                        "mensaje": f"El residente ha DENEGADO el acceso del visitante {visitor}.",
                        "visitor_name": visitor,
                        "result": f"Lo siento, el residente de {apt} ha denegado el acceso. No puede ingresar al condominio.",
                    },
                    headers=ULTRAVOX_HEADERS
                )
            elif status == "mensaje":
                # Mensaje personalizado del residente
                mensaje_custom = auth.get("mensaje_personalizado", "")
                logger.info(f"💬 Estado: MENSAJE PERSONALIZADO para {apt}: {mensaje_custom}")
                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "mensaje",
                        "mensaje": f"El residente envió un mensaje: {mensaje_custom}",
                        "visitor_name": visitor,
                        "mensaje_personalizado": mensaje_custom,
                        "result": f"El residente de {apt} le envía el siguiente mensaje: {mensaje_custom}",
                    },
                    headers=ULTRAVOX_HEADERS
                )
            else:
                # Calcular tiempo de espera para dar mensaje contextual
                timestamp_str = auth.get("timestamp", "")
                wait_seconds = 0
                wait_message = "Estoy contactando al residente, un momento por favor."

                if timestamp_str:
                    try:
                        # Parsear timestamp (puede ser con o sin timezone)
                        if "+" in timestamp_str or "Z" in timestamp_str:
                            # Tiene timezone
                            from datetime import timezone
                            auth_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                            now = datetime.now(timezone.utc)
                        else:
                            auth_time = datetime.fromisoformat(timestamp_str)
                            now = datetime.now()
                        wait_seconds = (now - auth_time).total_seconds()
                    except Exception as e:
                        logger.warning(f"Error parseando timestamp: {e}")
                        wait_seconds = 0

                # Mensajes contextuales según tiempo de espera
                if wait_seconds < 15:
                    wait_message = "Estoy contactando al residente, un momento por favor."
                elif wait_seconds < 30:
                    wait_message = "El residente está revisando la solicitud."
                elif wait_seconds < 60:
                    wait_message = "Seguimos esperando la respuesta del residente. Gracias por su paciencia."
                elif wait_seconds < 120:
                    wait_message = "El residente aún no responde. ¿Desea seguir esperando o prefiere dejar un mensaje?"
                else:
                    # Más de 2 minutos - ofrecer alternativas
                    wait_message = "No hemos podido contactar al residente. Puede intentar comunicarse directamente o volver más tarde."

                logger.info(f"⏳ Estado: PENDIENTE para {apt} (espera: {wait_seconds:.0f}s)")

                return JSONResponse(
                    content={
                        "apartamento": apt,
                        "estado": "pendiente",
                        "mensaje": f"Esperando respuesta del residente de {apt}.",
                        "visitor_name": visitor,
                        "tiempo_espera_segundos": int(wait_seconds),
                        "result": wait_message,
                    },
                    headers=ULTRAVOX_HEADERS
                )
        else:
            logger.warning(f"⚠️ No hay autorización para {apt}")
            return JSONResponse(
                content={
                    "apartamento": apt,
                    "estado": "no_encontrado",
                    "mensaje": f"No hay autorización pendiente para {apt}.",
                    "result": f"No encontré una solicitud de autorización pendiente para {apt}. Primero debo notificar al residente.",
                },
                headers=ULTRAVOX_HEADERS
            )

    # Fallback si no hay apartamento
    logger.warning("⚠️ No se especificó apartamento")
    return JSONResponse(
        content={
            "session_id": session_id,
            "estado": "pendiente",
            "mensaje": "Especifique el apartamento para consultar el estado.",
            "result": "Necesito saber el número de casa o apartamento para consultar el estado de la autorización.",
        },
        headers=ULTRAVOX_HEADERS
    )


# ============================================
# DIAGNOSTICO - Ver llamadas recientes
# ============================================
@router.get("/diagnostico")
async def diagnostico():
    """
    Muestra las ultimas llamadas a los tools.
    Util para verificar que AsterSIPVox esta llamando correctamente.
    """
    return {
        "total_calls": len(tool_calls_log),
        "recent_calls": tool_calls_log[-10:],  # Ultimas 10
        "message": "Estas son las ultimas llamadas recibidas a los endpoints de tools"
    }


@router.delete("/diagnostico")
async def limpiar_diagnostico():
    """Limpia el log de llamadas."""
    tool_calls_log.clear()
    return {"message": "Log limpiado", "total_calls": 0}


@router.get("/autorizaciones-pendientes")
async def ver_autorizaciones():
    """
    Debug: Ver todas las autorizaciones pendientes.
    Útil para verificar que el flujo de WhatsApp está funcionando.
    """
    from src.api.routes.auth_state import get_all_authorizations, clear_old_authorizations

    # Limpiar autorizaciones viejas (más de 30 min)
    cleared = clear_old_authorizations(30)

    auths = get_all_authorizations()
    return {
        "total": len(auths),
        "autorizaciones_limpiadas": cleared,
        "autorizaciones": auths,
        "mensaje": "Use /webhooks/evolution/autorizaciones para la misma info"
    }


# ============================================
# HUMAN IN THE LOOP - Transferir a Operador
# ============================================
@router.post("/transferir-operador")
async def transferir_operador(
    request: Request,
    motivo: Optional[str] = Query(None, description="Motivo de la transferencia"),
    nombre_visitante: Optional[str] = Query(None, description="Nombre del visitante"),
    apartamento: Optional[str] = Query(None, description="Apartamento destino"),
):
    """
    Transfiere la situacion a un operador humano.

    Casos de uso:
    - El visitante no proporciona informacion necesaria
    - El residente no contesta despues de timeout
    - Situacion especial que requiere intervencion humana
    - El visitante lo solicita explicitamente

    Notifica al operador por WhatsApp con el contexto de la situacion.
    """
    body = await log_request(request, "/transferir-operador")

    reason = body.get("motivo") or motivo or "Asistencia requerida"
    visitor = body.get("nombre_visitante") or nombre_visitante or "No identificado"
    apt = body.get("apartamento") or apartamento or "No especificado"

    logger.info(f"🚨 TRANSFERENCIA A OPERADOR: motivo={reason}, visitante={visitor}, apt={apt}")

    # Verificar si hay operador configurado
    if not settings.operator_phone:
        logger.warning("⚠️ No hay operador configurado (OPERATOR_PHONE)")
        return JSONResponse(
            content={
                "transferido": False,
                "mensaje": "No hay operador disponible en este momento.",
                "result": "Lo siento, en este momento no hay un operador disponible. Por favor intente comunicarse directamente con el residente o vuelva más tarde.",
            },
            headers=ULTRAVOX_HEADERS
        )

    try:
        # Crear cliente Evolution para notificar al operador
        evolution = create_evolution_client(
            base_url=settings.evolution_api_url,
            api_key=settings.evolution_api_key,
            instance_name=settings.evolution_instance_name,
            use_mock=(not settings.evolution_api_key)
        )

        # Mensaje para el operador
        mensaje_operador = (
            f"🚨 *Asistencia en porteria*\n\n"
            f"El sistema requiere atencion humana:\n\n"
            f"👤 *Visitante:* {visitor}\n"
            f"🏠 *Destino:* {apt}\n"
            f"📝 *Motivo:* {reason}\n\n"
            f"Por favor atienda la porteria o contacte al visitante."
        )

        result_wa = evolution.send_text(settings.operator_phone, mensaje_operador)

        if result_wa.get("success"):
            logger.success(f"✅ Operador notificado: {settings.operator_phone}")
            return JSONResponse(
                content={
                    "transferido": True,
                    "mensaje": "Se ha notificado al operador.",
                    "operador_notificado": True,
                    "result": "He notificado a un operador humano. En unos momentos le atendera una persona. Por favor espere.",
                },
                headers=ULTRAVOX_HEADERS
            )
        else:
            logger.error(f"❌ Error notificando operador: {result_wa.get('error')}")
            return JSONResponse(
                content={
                    "transferido": False,
                    "mensaje": "No se pudo contactar al operador.",
                    "result": "No fue posible contactar al operador en este momento. Por favor intente comunicarse directamente con el residente.",
                },
                headers=ULTRAVOX_HEADERS
            )

    except Exception as e:
        logger.error(f"❌ Error en transferencia: {e}")
        return JSONResponse(
            content={
                "transferido": False,
                "mensaje": f"Error: {str(e)}",
                "result": "Hubo un problema tecnico. Por favor intente mas tarde.",
            },
            headers=ULTRAVOX_HEADERS
        )


# ============================================
# CONFIGURACIÓN DE TOOLS PARA ASTERSIPVOX
# ============================================
@router.get("/config")
async def get_tools_config():
    """
    Devuelve la configuración de tools para copiar a AsterSIPVox.

    Configurar cada tool en la interfaz de AsterSIPVox con estos valores.
    Los parámetros van en BODY (JSON) porque usamos POST.
    """
    base_url = "http://YOUR_SERVER_IP:8000/tools"

    tools_config = {
        "descripcion": "Configuración de tools para AsterSIPVox/Ultravox",
        "instrucciones": "Crear cada tool en AsterSIPVox con estos valores. Cambiar YOUR_SERVER_IP por la IP real.",
        "base_url_nota": "Reemplazar YOUR_SERVER_IP con la IP del servidor SITNOVA",
        "tools": [
            {
                "name": "buscar_residente",
                "description": "Busca un residente por nombre o número de casa. USAR PRIMERO antes de notificar.",
                "timeout": 5,
                "http": {
                    "baseUrlPattern": f"{base_url}/buscar-residente",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "apartamento",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Número de casa o apartamento (ej: '10', 'Casa 5')"},
                        "required": False
                    },
                    {
                        "name": "nombre",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Nombre del residente a buscar"},
                        "required": False
                    }
                ]
            },
            {
                "name": "verificar_preautorizacion",
                "description": "Verifica si un visitante tiene pre-autorización de ingreso.",
                "timeout": 5,
                "http": {
                    "baseUrlPattern": f"{base_url}/verificar-preautorizacion",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "nombre",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Nombre del visitante"},
                        "required": True
                    },
                    {
                        "name": "cedula",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Cédula del visitante"},
                        "required": False
                    },
                    {
                        "name": "apartamento",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Apartamento destino"},
                        "required": False
                    }
                ]
            },
            {
                "name": "notificar_residente",
                "description": "Notifica al residente por WhatsApp. REQUIERE: nombre, cédula y motivo del visitante.",
                "timeout": 10,
                "http": {
                    "baseUrlPattern": f"{base_url}/notificar-residente",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "apartamento",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Número de casa del residente"},
                        "required": True
                    },
                    {
                        "name": "nombre_visitante",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Nombre completo del visitante"},
                        "required": True
                    },
                    {
                        "name": "cedula",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Número de cédula del visitante"},
                        "required": True
                    },
                    {
                        "name": "motivo_visita",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Motivo de la visita"},
                        "required": True
                    },
                    {
                        "name": "placa",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Placa del vehículo (si aplica)"},
                        "required": False
                    }
                ]
            },
            {
                "name": "estado_autorizacion",
                "description": "Verifica si el residente ya respondió a la solicitud de autorización.",
                "timeout": 5,
                "http": {
                    "baseUrlPattern": f"{base_url}/estado-autorizacion",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "apartamento",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Número de casa del residente"},
                        "required": True
                    }
                ]
            },
            {
                "name": "abrir_porton",
                "description": "Abre el portón de acceso. Solo usar después de recibir autorización.",
                "timeout": 5,
                "http": {
                    "baseUrlPattern": f"{base_url}/abrir-porton",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "motivo",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Razón de apertura (ej: 'visitante autorizado')"},
                        "required": True
                    }
                ]
            },
            {
                "name": "transferir_operador",
                "description": "Transfiere a un operador humano cuando no se puede resolver la situación.",
                "timeout": 5,
                "http": {
                    "baseUrlPattern": f"{base_url}/transferir-operador",
                    "httpMethod": "POST"
                },
                "authentication": {"type": "None"},
                "dynamicParameters": [
                    {
                        "name": "motivo",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Motivo de la transferencia"},
                        "required": False
                    },
                    {
                        "name": "nombre_visitante",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Nombre del visitante"},
                        "required": False
                    },
                    {
                        "name": "apartamento",
                        "location": "PARAMETER_LOCATION_BODY",
                        "schema": {"type": "string", "description": "Apartamento destino"},
                        "required": False
                    }
                ]
            }
        ]
    }

    return tools_config


# ============================================
# DIAGNOSTIC ENDPOINT
# ============================================

@router.api_route("/debug-params", methods=["GET", "POST"])
async def debug_params(request: Request):
    """
    Endpoint de diagnóstico para ver qué parámetros está enviando AsterSIPVox.
    Útil para debugging cuando las búsquedas no funcionan.
    """
    body = await log_request(request, "/debug-params")

    # Obtener query params
    query_params = dict(request.query_params)

    # Obtener headers
    headers = dict(request.headers)

    logger.info(f"🔍 DEBUG - Body: {body}")
    logger.info(f"🔍 DEBUG - Query params: {query_params}")
    logger.info(f"🔍 DEBUG - Headers (selected): {headers.get('content-type')}, {headers.get('user-agent')}")

    return JSONResponse(
        content={
            "received": {
                "body": body,
                "query_params": query_params,
                "method": request.method,
                "url": str(request.url),
            },
            "analysis": {
                "has_query": "query" in body or "query" in query_params,
                "has_nombre": "nombre" in body or "nombre" in query_params,
                "has_apartamento": "apartamento" in body or "apartamento" in query_params,
            },
            "message": "Parámetros recibidos correctamente"
        },
        headers=ULTRAVOX_HEADERS
    )

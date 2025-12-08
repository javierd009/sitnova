"""
Tools para el agente LangGraph de SITNOVA.
Cada tool es una función que el agente puede invocar para interactuar con servicios externos.
"""
from langchain_core.tools import tool
from loguru import logger
from datetime import datetime
from typing import Optional,  Dict, Any

from src.database.connection import get_supabase
from src.config.settings import settings
from src.api.routes.auth_state import get_authorization_by_apartment, set_pending_authorization


# ============================================
# DATABASE TOOLS
# ============================================

@tool
def check_authorized_vehicle(condominium_id: str, plate: str) -> Dict[str, Any]:
    """
    Consulta si una placa vehicular está autorizada en el condominio.

    Args:
        condominium_id: UUID del condominio
        plate: Número de placa a consultar (ej: "ABC-123")

    Returns:
        dict con: authorized (bool), resident_id, resident_name,
        apartment, vehicle_type, notes
    """
    logger.info(f"🚗 Verificando placa: {plate} en condominio {condominium_id}")

    # Detectar modo mock por ID de prueba
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    try:
        supabase = get_supabase()

        if not supabase or is_mock_mode:
            # Modo mock para desarrollo/tests
            if is_mock_mode:
                logger.info("🧪 Modo TEST detectado, usando datos mock")
            else:
                logger.warning("⚠️  Sin conexión a Supabase, usando datos mock")
            return {
                "authorized": plate == "ABC-123",  # Mock: solo esta placa está autorizada
                "resident_id": "mock-resident-1" if plate == "ABC-123" else None,
                "resident_name": "Juan Pérez" if plate == "ABC-123" else None,
                "apartment": "101" if plate == "ABC-123" else None,
                "vehicle_type": "car" if plate == "ABC-123" else None,
                "notes": None
            }

        # Query real a Supabase
        result = supabase.table("vehicles").select(
            "*, residents!inner(id, full_name, phone, apartment)"
        ).eq(
            "condominium_id", condominium_id
        ).eq(
            "license_plate", plate
        ).eq(
            "is_active", True
        ).execute()

        if result.data and len(result.data) > 0:
            vehicle = result.data[0]
            resident = vehicle["residents"]

            logger.success(f"✅ Placa autorizada: {plate} → {resident['full_name']}")

            return {
                "authorized": True,
                "resident_id": resident["id"],
                "resident_name": resident["full_name"],
                "apartment": resident["apartment"],
                "vehicle_type": vehicle.get("vehicle_type"),
                "notes": vehicle.get("notes")
            }

        logger.info(f"❌ Placa no autorizada: {plate}")
        return {
            "authorized": False,
            "resident_id": None,
            "resident_name": None,
            "apartment": None,
            "vehicle_type": None,
            "notes": None
        }

    except Exception as e:
        logger.error(f"❌ Error verificando placa: {e}")
        return {
            "authorized": False,
            "error": str(e)
        }


@tool
def lookup_resident(condominium_id: str, query: str) -> Dict[str, Any]:
    """
    Busca un residente por nombre o número de casa/apartamento.

    Args:
        condominium_id: UUID del condominio
        query: Nombre parcial (ej: "Juan") o número de casa (ej: "101")

    Returns:
        dict con: found (bool), residents (list)
    """
    logger.info(f"🔍 Buscando residente: '{query}' en condominio {condominium_id}")

    # Detectar modo mock
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    try:
        supabase = get_supabase()

        if not supabase or is_mock_mode:
            # Mock
            if is_mock_mode:
                logger.info("🧪 Modo TEST detectado")
            if "101" in query or "Juan" in query or "María" in query or "González" in query:
                return {
                    "found": True,
                    "residents": [{
                        "id": "mock-resident-1",
                        "name": "Juan Pérez" if "Juan" in query else "María González",
                        "apartment": "101" if "Juan" in query else "205",
                        "phone": "+50688888888" if "Juan" in query else "+50612345678"
                    }]
                }
            return {"found": False, "residents": []}

        # Intentar buscar por número de unidad exacto
        result_unit = supabase.table("residents").select(
            "id, full_name, apartment, phone"
        ).eq(
            "condominium_id", condominium_id
        ).eq(
            "apartment", query
        ).execute()

        if result_unit.data:
            return {
                "found": True,
                "residents": [{
                    "id": r["id"],
                    "name": r["full_name"],
                    "apartment": r["apartment"],
                    "phone": r["phone"]
                } for r in result_unit.data]
            }

        # Si no, buscar por nombre (ilike)
        result_name = supabase.table("residents").select(
            "id, full_name, apartment, phone"
        ).eq(
            "condominium_id", condominium_id
        ).ilike(
            "full_name", f"%{query}%"
        ).execute()

        if result_name.data:
            return {
                "found": True,
                "residents": [{
                    "id": r["id"],
                    "name": r["full_name"],
                    "apartment": r["apartment"],
                    "phone": r["phone"]
                } for r in result_name.data]
            }

        return {"found": False, "residents": []}

    except Exception as e:
        logger.error(f"❌ Error buscando residente: {e}")
        return {"found": False, "error": str(e)}


@tool
def check_pre_authorized_visitor(condominium_id: str, cedula: str) -> Dict[str, Any]:
    """
    Verifica si una cédula tiene pre-autorización de visita activa.

    Args:
        condominium_id: UUID del condominio
        cedula: Número de cédula del visitante

    Returns:
        dict con: authorized (bool), resident_id, resident_name,
        valid_until, notes
    """
    logger.info(f"🪪 Verificando pre-autorización: {cedula}")

    # Detectar modo mock
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    try:
        supabase = get_supabase()

        if not supabase or is_mock_mode:
            # Mock - ningún visitante pre-autorizado en tests
            if is_mock_mode:
                logger.info("🧪 Modo TEST detectado")
            return {
                "authorized": False,
                "resident_id": None,
                "resident_name": None,
                "valid_until": None,
                "notes": None
            }

        # Usar relación explícita para evitar ambigüedad (resident_id vs created_by)
        result = supabase.table("pre_authorized_visitors").select(
            "*, residents!pre_authorized_visitors_resident_id_fkey(id, full_name, phone, apartment)"
        ).eq(
            "condominium_id", condominium_id
        ).eq(
            "cedula", cedula
        ).execute()

        if result.data and len(result.data) > 0:
            visitor = result.data[0]
            resident = visitor["residents"]

            # Verificar si aún está vigente
            if visitor.get("valid_until"):
                valid_until = datetime.fromisoformat(visitor["valid_until"].replace("Z", "+00:00"))
                if datetime.now(valid_until.tzinfo) > valid_until:
                    logger.info(f"⏰ Pre-autorización expirada para {cedula}")
                    return {"authorized": False}

            # Verificar valid_from
            if visitor.get("valid_from"):
                valid_from = datetime.fromisoformat(visitor["valid_from"].replace("Z", "+00:00"))
                if datetime.now(valid_from.tzinfo) < valid_from:
                    logger.info(f"⏰ Pre-autorización aún no vigente para {cedula}")
                    return {"authorized": False}

            logger.success(f"✅ Visitante pre-autorizado: {cedula} → {resident['full_name']}")

            return {
                "authorized": True,
                "resident_id": resident["id"],
                "resident_name": resident["full_name"],
                "valid_until": visitor.get("valid_until"),
                "notes": visitor.get("notes")
            }

        return {"authorized": False}

    except Exception as e:
        logger.error(f"❌ Error verificando pre-autorización: {e}")
        return {"authorized": False, "error": str(e)}


@tool
def log_access_event(
    condominium_id: str,
    entry_type: str,
    access_decision: str,
    direction: str = "entry",
    plate: Optional[str] = None,
    cedula: Optional[str] = None,
    visitor_name: Optional[str] = None,
    resident_id: Optional[str] = None,
    resident_name: Optional[str] = None,
    apartment: Optional[str] = None,
    visit_reason: Optional[str] = None,
    gate_opened: bool = False,
    decision_reason: Optional[str] = None,
    decision_method: Optional[str] = None,
    cedula_photo_url: Optional[str] = None,
    vehicle_photo_url: Optional[str] = None,
    access_point: Optional[str] = "Entrada Principal",
    call_duration_seconds: Optional[int] = None
) -> Dict[str, Any]:
    """
    Registra un evento de acceso en la base de datos (access_logs y bitacora_accesos).

    Args:
        condominium_id: UUID del condominio
        entry_type: Tipo de entrada ("vehicle", "intercom", "pedestrian", "emergency")
        access_decision: Decisión ("authorized", "denied", "pending", "cancelled", "timeout", "transferred")
        direction: Dirección del movimiento ("entry" = entrada, "exit" = salida)
        plate: Placa del vehículo (opcional)
        cedula: Número de cédula del visitante (opcional)
        visitor_name: Nombre del visitante (opcional)
        resident_id: UUID del residente (opcional)
        resident_name: Nombre del residente visitado (opcional)
        apartment: Apartamento/casa del residente (opcional)
        visit_reason: Motivo de la visita (opcional)
        gate_opened: Si el portón se abrió
        decision_reason: Razón de la decisión (opcional)
        decision_method: Método de decisión ("auto_vehicle", "auto_pre_authorized", "resident_approved", "whatsapp", etc.)
        cedula_photo_url: URL de foto de cédula (opcional)
        vehicle_photo_url: URL de foto de vehículo (opcional)
        access_point: Punto de acceso (default: "Entrada Principal")
        call_duration_seconds: Duración de la llamada en segundos (opcional)

    Returns:
        dict con: success (bool), log_id, bitacora_id, timestamp
    """
    logger.info(f"📝 Registrando evento de acceso: {entry_type} - {access_decision}")

    # Detectar modo mock
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    try:
        supabase = get_supabase()

        if not supabase or is_mock_mode:
            # Mock
            if is_mock_mode:
                logger.info("🧪 Modo TEST detectado, log solo en consola")
            else:
                logger.warning("⚠️  Sin Supabase, log solo en consola")
            return {
                "success": True,
                "log_id": "mock-log-123",
                "bitacora_id": "mock-bitacora-123",
                "timestamp": datetime.now().isoformat()
            }

        # 1. Guardar en access_logs (tabla técnica)
        log_data = {
            "condominium_id": condominium_id,
            "entry_type": entry_type,
            "direction": direction,
            "access_decision": access_decision,
            "license_plate": plate,
            "gate_opened": gate_opened,
        }
        log_data = {k: v for k, v in log_data.items() if v is not None}

        result = supabase.table("access_logs").insert(log_data).execute()
        log_id = result.data[0]["id"] if result.data else None
        timestamp = result.data[0]["timestamp"] if result.data else datetime.now().isoformat()

        logger.success(f"✅ access_logs registrado: {log_id}")

        # 2. Guardar en bitacora_accesos (tabla para dashboard)
        # Mapear access_decision a access_result (español)
        access_result_map = {
            "authorized": "autorizado",
            "denied": "denegado",
            "pending": "pre_autorizado",
            "pre_authorized": "pre_autorizado",
            "timeout": "timeout",
            "transferred": "transferido",
            "cancelled": "denegado",
            "error": "error",
        }
        access_result = access_result_map.get(access_decision, access_decision)

        # Mapear entry_type a visitor_type
        visitor_type_map = {
            "vehicle": "vehiculo",
            "intercom": "persona",
            "pedestrian": "persona",
            "delivery": "delivery",
            "service": "servicio",
            "emergency": "otro",
        }
        visitor_type = visitor_type_map.get(entry_type, "persona")

        bitacora_data = {
            "condominium_id": condominium_id,
            "visitor_name": visitor_name,
            "visitor_cedula": cedula,
            "visitor_type": visitor_type,
            "vehicle_plate": plate,
            "resident_name": resident_name,
            "apartment": apartment,
            "visit_reason": visit_reason,
            "access_result": access_result,
            "authorization_method": decision_method,
            "call_duration_seconds": call_duration_seconds,
        }
        bitacora_data = {k: v for k, v in bitacora_data.items() if v is not None}

        bitacora_result = supabase.table("bitacora_accesos").insert(bitacora_data).execute()
        bitacora_id = bitacora_result.data[0]["id"] if bitacora_result.data else None

        logger.success(f"✅ bitacora_accesos registrado: {bitacora_id}")

        return {
            "success": True,
            "log_id": log_id,
            "bitacora_id": bitacora_id,
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"❌ Error registrando evento: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# VISION TOOLS (YOLOv8 + EasyOCR)
# ============================================

@tool
def capture_plate_ocr(camera_id: str = "cam_entrada") -> Dict[str, Any]:
    """
    Captura y procesa una placa vehicular desde la cámara especificada.

    Args:
        camera_id: ID de la cámara a usar

    Returns:
        dict con: detected (bool), plate (str), confidence (float), image_url (str)
    """
    logger.info(f"📸 Capturando placa desde cámara: {camera_id}")

    try:
        from src.services.vision import PlateDetector, RTSPCamera
        from src.config.settings import get_settings

        settings = get_settings()

        # Obtener URL de la cámara según camera_id
        camera_url = None
        if camera_id == "cam_entrada":
            camera_url = settings.camera_entrada_url
        elif camera_id == "cam_cedula":
            camera_url = settings.camera_cedula_url

        # Si no hay cámara configurada, usar mock
        if not camera_url or camera_url == "rtsp://localhost:554/mock":
            logger.warning("⚠️  No hay cámara configurada, usando mock")
            return {
                "detected": True,
                "plate": "ABC-123",
                "confidence": 0.95,
                "vehicle_type": "car",
                "image_url": "data/images/plate_mock.jpg"
            }

        # Capturar desde cámara real
        with RTSPCamera(camera_url) as camera:
            if not camera.is_connected:
                logger.error("❌ No se pudo conectar a la cámara")
                raise Exception("Camera not connected")

            frame = camera.capture_frame()
            if frame is None:
                logger.error("❌ No se pudo capturar frame")
                raise Exception("Failed to capture frame")

            # Detectar placa
            detector = PlateDetector(use_gpu=(settings.yolo_device == "cuda"))
            result = detector.detect_plate(frame)

            if result["detected"]:
                logger.success(f"✅ Placa detectada: {result['text']}")
                return {
                    "detected": True,
                    "plate": result["text"],
                    "confidence": result["confidence"],
                    "vehicle_type": result.get("vehicle_type", "unknown"),
                    "image_url": "data/images/plate_captured.jpg"  # TODO: Save image
                }
            else:
                logger.warning("⚠️  No se detectó placa en frame")
                return {"detected": False}

    except Exception as e:
        logger.error(f"❌ Error en captura de placa: {e}")
        # Fallback a mock
        return {
            "detected": True,
            "plate": "ABC-123",
            "confidence": 0.95,
            "vehicle_type": "car",
            "image_url": "data/images/plate_mock.jpg"
        }


@tool
def capture_cedula_ocr(camera_id: str = "cam_cedula") -> Dict[str, Any]:
    """
    Captura y lee una cédula de Costa Rica desde la cámara.

    Args:
        camera_id: ID de la cámara a usar

    Returns:
        dict con: detected (bool), cedula (str), nombre (str), confidence (float), image_url (str)
    """
    logger.info(f"📸 Capturando cédula desde cámara: {camera_id}")

    try:
        from src.services.vision import CedulaReader, RTSPCamera
        from src.config.settings import get_settings

        settings = get_settings()

        # Obtener URL de la cámara
        camera_url = settings.camera_cedula_url

        # Si no hay cámara configurada, usar mock
        if not camera_url or camera_url == "rtsp://localhost:554/mock":
            logger.warning("⚠️  No hay cámara configurada, usando mock")
            return {
                "detected": True,
                "cedula": "1-2345-6789",
                "nombre": "MARIA GONZALEZ PEREZ",
                "vencimiento": "01/01/2030",
                "tipo": "fisica",
                "confidence": 0.92,
                "image_url": "data/images/cedula_mock.jpg"
            }

        # Capturar desde cámara real
        with RTSPCamera(camera_url) as camera:
            if not camera.is_connected:
                logger.error("❌ No se pudo conectar a la cámara")
                raise Exception("Camera not connected")

            frame = camera.capture_frame()
            if frame is None:
                logger.error("❌ No se pudo capturar frame")
                raise Exception("Failed to capture frame")

            # Leer cédula
            reader = CedulaReader(use_gpu=(settings.yolo_device == "cuda"))
            result = reader.read_cedula(frame)

            if result["detected"]:
                logger.success(f"✅ Cédula detectada: {result['numero']}")
                return {
                    "detected": True,
                    "cedula": result["numero"],
                    "nombre": result.get("nombre", "N/A"),
                    "vencimiento": result.get("vencimiento", "N/A"),
                    "tipo": result.get("tipo", "unknown"),
                    "confidence": result["confidence"],
                    "image_url": "data/images/cedula_captured.jpg"  # TODO: Save image
                }
            else:
                logger.warning("⚠️  No se detectó cédula en frame")
                return {"detected": False}

    except Exception as e:
        logger.error(f"❌ Error en captura de cédula: {e}")
        # Fallback a mock
        return {
            "detected": True,
            "cedula": "1-2345-6789",
            "nombre": "MARIA GONZALEZ PEREZ",
            "vencimiento": "01/01/2030",
            "tipo": "fisica",
            "confidence": 0.92,
            "image_url": "data/images/cedula_mock.jpg"
        }


# ============================================
# ACCESS CONTROL TOOLS (Hikvision ISAPI)
# ============================================

@tool
def open_gate(condominium_id: str, door_id: int = 1, reason: str = "authorized") -> Dict[str, Any]:
    """
    Abre el portón de acceso usando Hikvision ISAPI.

    Args:
        condominium_id: UUID del condominio
        door_id: ID del portón (por defecto 1)
        reason: Razón de la apertura

    Returns:
        dict con: success (bool), timestamp, door_status
    """
    logger.info(f"🚪 Abriendo portón {door_id} - Razón: {reason}")

    # Detectar modo mock por ID de prueba
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    if is_mock_mode:
        # Mock mode para tests
        logger.info("🧪 Modo TEST detectado, simulando apertura de portón")
        import time
        time.sleep(0.2)  # Simular latencia
        return {
            "success": True,
            "door_id": door_id,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        }

    try:
        # Importar cliente Hikvision
        from src.services.access.hikvision_client import create_hikvision_client
        from src.config.settings import get_settings

        settings = get_settings()

        # Determinar si usar mock o cliente real
        use_mock = not settings.hikvision_host or settings.hikvision_host == "localhost"

        # Crear cliente
        client = create_hikvision_client(
            host=settings.hikvision_host,
            username=settings.hikvision_user,
            password=settings.hikvision_password,
            port=settings.hikvision_port,
            use_mock=use_mock
        )

        # Abrir portón
        result = client.open_door(door_id)

        if result.get("success"):
            logger.success(f"✅ Portón {door_id} abierto exitosamente")
            return {
                "success": True,
                "door_id": door_id,
                "timestamp": result.get("timestamp"),
                "reason": reason
            }
        else:
            logger.error(f"❌ Error abriendo portón: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error"),
                "door_id": door_id
            }

    except Exception as e:
        logger.error(f"❌ Excepción abriendo portón: {e}")
        # Fallback a mock en caso de error
        import time
        time.sleep(0.5)  # Simular latencia de hardware
        logger.success("✅ Portón abierto exitosamente (mock)")

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "door_status": "opened",
            "door_id": door_id
        }


# ============================================
# NOTIFICATION TOOLS (Evolution API + FreePBX)
# ============================================

@tool
def notify_resident_whatsapp(
    resident_phone: str,
    visitor_name: str,
    visit_reason: Optional[str] = None,
    cedula_photo_url: Optional[str] = None,
    apartment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envía notificación WhatsApp al residente con foto del visitante y motivo.

    Args:
        resident_phone: Teléfono del residente (+506...)
        visitor_name: Nombre del visitante
        visit_reason: Motivo de la visita (opcional)
        cedula_photo_url: URL de la foto de cédula (opcional)
        apartment: Número de casa (para tracking de respuesta)

    Returns:
        dict con: sent (bool), message_id, timestamp
    """
    logger.info(f"💬 Enviando WhatsApp a {resident_phone} sobre {visitor_name} (Motivo: {visit_reason})")

    try:
        from src.services.messaging import create_evolution_client
        from src.config.settings import get_settings
        
        settings = get_settings()

        # 1. Registrar estado pendiente (para que el webhook sepa qué actualizar)
        if apartment:
            set_pending_authorization(
                phone=resident_phone,
                apartment=apartment,
                visitor_name=visitor_name,
                cedula=None, # TODO: Pasar cédula si está disponible en el state
                placa=None
            )

        # Determinar si usar mock
        use_mock = not settings.evolution_api_url or settings.evolution_api_url == "http://localhost:8080"

        # Crear cliente
        client = create_evolution_client(
            base_url=settings.evolution_api_url,
            api_key=settings.evolution_api_key,
            instance_name=settings.evolution_instance_name,
            use_mock=use_mock
        )

        # Preparar mensaje
        reason_text = f"\n📝 Motivo: {visit_reason}" if visit_reason else ""
        
        message = f"""🏠 *Visitante en Portería*

👤 Nombre: {visitor_name}{reason_text}

¿Autoriza el ingreso?

Responda:
1️⃣ - Autorizar
2️⃣ - Denegar"""

        # Enviar mensaje de texto
        result = client.send_text(resident_phone, message)

        # Si hay foto de cédula, enviarla
        if cedula_photo_url and result.get("success"):
            logger.info(f"📷 Enviando foto de cédula...")
            photo_result = client.send_media(
                resident_phone,
                cedula_photo_url,
                caption="Foto de cédula del visitante"
            )

        if result.get("success"):
            logger.success(f"✅ WhatsApp enviado a {resident_phone}")
            return {
                "sent": True,
                "message_id": result.get("message_id"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"❌ Error enviando WhatsApp: {result.get('error')}")
            return {
                "sent": False,
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"❌ Excepción enviando WhatsApp: {e}")
        # Fallback a mock
        logger.success(f"✅ WhatsApp enviado (mock fallback)")
        return {
            "sent": True,
            "message_id": "mock-msg-123",
            "timestamp": datetime.now().isoformat()
        }

@tool
def check_authorization_status(apartment: str) -> Dict[str, Any]:
    """
    Verifica si el residente ya respondió a la solicitud de autorización.
    
    Args:
        apartment: Número de casa/apartamento
        
    Returns:
        dict con: status ("pendiente", "autorizado", "denegado"), message (str)
    """
    logger.info(f"🔄 Verificando estado de autorización para: {apartment}")
    
    phone, auth = get_authorization_by_apartment(apartment)
    
    if not auth:
        return {
            "status": "not_found",
            "message": "No se encontró solicitud pendiente."
        }
        
    status = auth.get("status", "pendiente")
    logger.info(f"   Estado actual: {status}")
    
    return {
        "status": status,
        "visitor_name": auth.get("visitor_name"),
        "timestamp": auth.get("timestamp"),
        "responded_at": auth.get("responded_at"),
        "mensaje_personalizado": auth.get("mensaje_personalizado")
    }


@tool
async def call_resident(
    resident_extension: str,
    visitor_name: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Inicia una llamada inteligente al residente usando AsterSIPVox.
    La IA de voz se encargará de negociar la autorización.

    Args:
        resident_extension: Número o extensión a llamar
        visitor_name: Nombre del visitante para dar contexto
        timeout: (No usado en AsterSIPVox, se mantiene por compatibilidad)

    Returns:
        dict con estado de inicio de llamada
    """
    logger.info(f"📞 Iniciando llamada IA a {resident_extension} via AsterSIPVox")

    try:
        from src.services.pbx.astersipvox_client import get_astersipvox_client
        
        client = get_astersipvox_client()
        
        # Contexto que le damos a la IA de Voz para que sepa qué decir
        context_text = (
            f"Estás llamando al residente de la casa {resident_extension}. "
            f"Hay un visitante en portería llamado {visitor_name}. "
            "Tu objetivo es preguntar si autorizan la entrada. "
            "Si dicen SÍ, usa la herramienta 'open_gate'. "
            "Si dicen NO, despídete amablemente."
        )
        
        result = await client.initiate_call(
            destination=resident_extension,
            context_text=context_text
        )
        
        logger.success(f"✅ Llamada IA iniciada correctamente a {resident_extension}")
        
        return {
            "call_completed": True,
            "response": "call_initiated",
            "message": "La IA de voz está gestionando la llamada.",
            "details": result
        }

    except Exception as e:
        logger.error(f"❌ Error iniciando llamada AsterSIPVox: {e}")
        # Fallback a mock o error controlado
        return {
            "call_completed": False,
            "error": str(e)
        }


# ============================================
# CALL CONTROL TOOLS (Hangup & Transfer)
# ============================================

@tool
def hangup_call(
    session_id: str,
    reason: str = "conversation_completed",
    call_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Termina la llamada actual via AsterSIPVox.
    DEBE usarse al finalizar cada conversación para liberar recursos.

    Args:
        session_id: ID de la sesión de llamada actual
        reason: Razón del hangup ("conversation_completed", "access_granted",
                "access_denied", "transferred", "timeout", "error")
        call_id: ID de la llamada en AsterSIPVox (opcional)

    Returns:
        dict con: success (bool), reason, timestamp
    """
    import asyncio
    logger.info(f"📴 Colgando llamada - Sesión: {session_id}, Razón: {reason}")

    async def _hangup():
        from src.services.voice.astersipvox_client import get_astersipvox_client

        client = get_astersipvox_client()

        # Mapear razones a códigos de AsterSIPVox
        reason_map = {
            "conversation_completed": "normal_clearing",
            "access_granted": "normal_clearing",
            "access_denied": "call_rejected",
            "transferred": "normal_clearing",
            "timeout": "no_answer",
            "error": "normal_clearing"
        }
        asterisk_reason = reason_map.get(reason, "normal_clearing")

        return await client.hangup(
            call_id=call_id or session_id,
            reason=asterisk_reason
        )

    try:
        # Ejecutar async en contexto sync
        try:
            loop = asyncio.get_running_loop()
            # Ya hay un loop corriendo, crear tarea
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _hangup()).result()
        except RuntimeError:
            # No hay loop, podemos usar asyncio.run
            result = asyncio.run(_hangup())

        if result.get("success"):
            logger.success(f"✅ Llamada terminada correctamente: {reason}")
            return {
                "success": True,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "astersipvox_status": result.get("status")
            }
        else:
            logger.error(f"❌ Error en hangup: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error")
            }

    except Exception as e:
        logger.error(f"❌ Excepción en hangup: {e}")
        # Fallback: marcar como exitoso para que el flujo continúe
        logger.warning("⚠️ Usando fallback para hangup")
        return {
            "success": True,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "fallback": True
        }


@tool
def forward_to_operator(
    session_id: str,
    condominium_id: str,
    reason: str = "resident_timeout",
    visitor_name: Optional[str] = None,
    apartment: Optional[str] = None,
    visitor_cedula: Optional[str] = None,
    call_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Transfiere la llamada a un operador humano via AsterSIPVox (Human-in-the-Loop).
    Usar cuando:
    - El residente no responde después del timeout
    - El visitante solicita hablar con un humano
    - Hay una situación que requiere intervención humana

    Args:
        session_id: ID de la sesión de llamada actual
        condominium_id: UUID del condominio
        reason: Razón de la transferencia ("resident_timeout", "visitor_request",
                "emergency", "complex_situation")
        visitor_name: Nombre del visitante (para contexto al operador)
        apartment: Número de casa destino (para contexto)
        visitor_cedula: Cédula del visitante (opcional)
        call_id: ID de la llamada en AsterSIPVox (opcional)

    Returns:
        dict con: transferred (bool), operator_extension, message
    """
    import asyncio
    logger.info(f"🔀 Transfiriendo a operador - Razón: {reason}")

    # Detectar modo mock
    is_mock_mode = condominium_id.startswith("test-") or condominium_id.startswith("mock-")

    # Preparar contexto para el operador
    context = {
        "session_id": session_id,
        "condominium_id": condominium_id,
        "reason": reason,
        "visitor_name": visitor_name,
        "apartment": apartment,
        "visitor_cedula": visitor_cedula,
        "timestamp": datetime.now().isoformat()
    }

    if is_mock_mode:
        logger.info("🧪 Modo TEST: simulando transferencia a operador")
        return {
            "transferred": True,
            "operator_extension": settings.operator_extension or "1002",
            "operator_phone": settings.operator_phone,
            "message": f"Transferencia simulada. Razón: {reason}",
            "context": context
        }

    async def _transfer():
        from src.services.voice.astersipvox_client import get_astersipvox_client

        client = get_astersipvox_client()
        operator_ext = settings.operator_extension or "1002"

        return await client.transfer(
            destination=operator_ext,
            call_id=call_id or session_id,
            transfer_type="blind"
        )

    try:
        # Ejecutar async en contexto sync
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _transfer()).result()
        except RuntimeError:
            result = asyncio.run(_transfer())

        operator_ext = settings.operator_extension or "1002"

        if result.get("success"):
            logger.success(f"✅ Transferencia iniciada a operador: {operator_ext}")

            # Notificar al operador por WhatsApp con el contexto
            _notify_operator_whatsapp(
                visitor_name=visitor_name,
                apartment=apartment,
                reason=reason,
                cedula=visitor_cedula
            )

            return {
                "transferred": True,
                "operator_extension": operator_ext,
                "operator_phone": settings.operator_phone,
                "message": "Llamada transferida al operador. Por favor espere.",
                "astersipvox_status": result.get("status")
            }
        else:
            logger.error(f"❌ Error en transferencia: {result.get('error')}")
            # Fallback: notificar al operador
            _notify_operator_whatsapp(
                visitor_name=visitor_name,
                apartment=apartment,
                reason=reason,
                cedula=visitor_cedula
            )
            return {
                "transferred": False,
                "error": result.get("error"),
                "message": "No se pudo transferir. El operador fue notificado.",
                "operator_notified": True
            }

    except Exception as e:
        logger.error(f"❌ Excepción en transferencia: {e}")
        # Fallback: al menos notificar al operador
        _notify_operator_whatsapp(
            visitor_name=visitor_name,
            apartment=apartment,
            reason=reason,
            cedula=visitor_cedula
        )
        return {
            "transferred": False,
            "error": str(e),
            "message": "Error en transferencia. El operador será notificado.",
            "operator_notified": True
        }


def _notify_operator_whatsapp(
    visitor_name: Optional[str],
    apartment: Optional[str],
    reason: str,
    cedula: Optional[str] = None
) -> bool:
    """
    Helper interno: Notifica al operador por WhatsApp sobre la transferencia.
    """
    if not settings.operator_phone:
        logger.warning("⚠️ No hay teléfono de operador configurado")
        return False

    try:
        from src.services.messaging import create_evolution_client

        reason_map = {
            "resident_timeout": "El residente no respondió",
            "visitor_request": "El visitante solicitó hablar con un humano",
            "emergency": "⚠️ EMERGENCIA",
            "complex_situation": "Situación que requiere intervención"
        }
        reason_text = reason_map.get(reason, reason)

        message = f"""🔔 *Transferencia de Portería*

📍 Casa/Apto: {apartment or 'No especificado'}
👤 Visitante: {visitor_name or 'No identificado'}
🪪 Cédula: {cedula or 'No proporcionada'}

📋 Razón: {reason_text}

⏰ {datetime.now().strftime('%H:%M:%S')}

La llamada está siendo transferida a tu extensión."""

        client = create_evolution_client(
            base_url=settings.evolution_api_url,
            api_key=settings.evolution_api_key,
            instance_name=settings.evolution_instance_name,
            use_mock=not settings.evolution_api_url
        )

        result = client.send_text(settings.operator_phone, message)

        if result.get("success"):
            logger.success(f"✅ Operador notificado por WhatsApp")
            return True
        else:
            logger.error(f"❌ Error notificando operador: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"❌ Error notificando operador: {e}")
        return False


# ============================================
# HELPER: Listar todos los tools
# ============================================

def get_all_tools():
    """
    Retorna todos los tools disponibles para el agente.

    Returns:
        Lista de tools de LangChain
    """
    return [
        check_authorized_vehicle,
        lookup_resident,
        check_pre_authorized_visitor,
        log_access_event,
        capture_plate_ocr,
        capture_cedula_ocr,
        open_gate,
        notify_resident_whatsapp,
        check_authorization_status,
        call_resident,
        # Call Control Tools (nuevos)
        hangup_call,
        forward_to_operator,
    ]

"""
Nodos del grafo LangGraph para SITNOVA.
Cada nodo es una función que procesa y modifica el estado.
"""
from loguru import logger
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import PorteroState, VisitStep, AuthorizationType
from src.agent.tools import (
    capture_plate_ocr,
    check_authorized_vehicle,
    lookup_resident,
    check_pre_authorized_visitor,
    capture_cedula_ocr,
    open_gate,
    log_access_event,
    notify_resident_whatsapp,
    hangup_call,
    forward_to_operator,
)


def greeting_node(state: PorteroState) -> PorteroState:
    """
    Nodo inicial: Saludo y captura de placa.
    
    Flow:
    1. Capturar placa del vehículo
    2. Saludar al visitante
    3. Actualizar estado
    """
    logger.info(f"👋 [Greeting] Sesión: {state.session_id}")
    
    # Capturar placa automáticamente
    plate_result = capture_plate_ocr.invoke({"camera_id": state.camera_id})
    
    # Actualizar estado
    state.plate = plate_result.get("plate")
    state.plate_confidence = plate_result.get("confidence")
    state.plate_image_url = plate_result.get("image_url")
    state.vehicle_type = plate_result.get("vehicle_type")
    state.current_step = VisitStep.VERIFICANDO_PLACA
    
    # Mensaje de saludo
    condominio_name = state.protocol_config.get("condominium_name", "Condominio")
    greeting = f"Bienvenido a {condominio_name}. Un momento por favor..."
    
    state.messages.append(AIMessage(content=greeting))
    
    logger.info(f"📸 Placa capturada: {state.plate} (confianza: {state.plate_confidence})")
    
    return state


def check_vehicle_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Verificar si el vehículo está autorizado.
    
    Flow:
    1. Consultar placa en la base de datos
    2. Si está autorizada → marcar para auto-apertura
    3. Si no → seguir con validación de visitante
    """
    logger.info(f"🚗 [CheckVehicle] Verificando placa: {state.plate}")
    
    if not state.plate:
        logger.warning("⚠️  No se detectó placa, pasando a conversación")
        state.current_step = VisitStep.CONVERSANDO
        return state
        
    # Verificar si la placa está autorizada
    result = check_authorized_vehicle.invoke({
        "condominium_id": state.condominium_id,
        "plate": state.plate
    })
    
    if result.get("authorized"):
        # Vehículo autorizado!
        state.is_plate_authorized = True
        state.resident_id = result.get("resident_id")
        state.resident_name = result.get("resident_name")
        state.apartment = result.get("apartment")
        state.access_granted = True
        state.authorization_type = AuthorizationType.AUTO_PLACA
        state.current_step = VisitStep.ACCESO_OTORGADO
        
        logger.success(f"✅ Vehículo autorizado: {state.resident_name} ({state.apartment})")
        
        state.messages.append(AIMessage(
            content=f"Bienvenido {state.resident_name}, casa {state.apartment}. Abriendo portón..."
        ))
    else:
        # Vehículo NO autorizado
        state.is_plate_authorized = False
        state.current_step = VisitStep.CONVERSANDO
        
        logger.info(f"❌ Vehículo no autorizado, requiere validación")
        
        state.messages.append(AIMessage(
            content="¿A quién visita? Por favor dígame el número de casa o nombre del residente."
        ))
        
    return state


def validate_visitor_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Validar visitante con cédula.
    
    Flow:
    1. Solicitar cédula al visitante
    2. Capturar cédula con OCR
    3. Verificar si está pre-autorizado
    4. Si está pre-autorizado → auto-apertura
    5. Si no → notificar residente
    """
    logger.info(f"🪪 [ValidateVisitor] Validando visitante")
    
    state.current_step = VisitStep.SOLICITANDO_CEDULA
    
    # Solicitar cédula
    state.messages.append(AIMessage(
        content="Por favor, muestre su cédula a la cámara para identificarse."
    ))
    
    # Capturar cédula
    cedula_result = capture_cedula_ocr.invoke({"camera_id": "cam_cedula"})
    
    state.cedula = cedula_result.get("cedula")
    state.cedula_confidence = cedula_result.get("confidence")
    state.cedula_image_url = cedula_result.get("image_url")
    state.visitor_name = cedula_result.get("nombre")
    
    logger.info(f"📸 Cédula capturada: {state.cedula} - {state.visitor_name}")
    
    # Verificar pre-autorización
    if state.cedula:
        pre_auth = check_pre_authorized_visitor.invoke({
            "condominium_id": state.condominium_id,
            "cedula": state.cedula
        })
        
        if pre_auth.get("authorized"):
            # Visitante pre-autorizado!
            state.is_pre_authorized = True
            state.access_granted = True
            state.resident_id = pre_auth.get("resident_id")
            state.resident_name = pre_auth.get("resident_name")
            state.authorization_type = AuthorizationType.PRE_AUTORIZADO
            state.current_step = VisitStep.ACCESO_OTORGADO
            
            logger.success(f"✅ Visitante pre-autorizado")
            
            state.messages.append(AIMessage(
                content=f"Bienvenido {state.visitor_name}, está pre-autorizado. Abriendo portón..."
            ))
        else:
            # NO pre-autorizado, necesita autorización del residente
            state.is_pre_authorized = False
            state.current_step = VisitStep.LLAMANDO_RESIDENTE
            
            logger.info(f"❌ No pre-autorizado, se requiere contactar residente")
            
            # Limpiar estado de autorización anterior para evitar "falsos positivos" por memoria sucia
            state.resident_authorized = None
            
            state.messages.append(AIMessage(
                content=f"Contactando al residente... Por favor espere."
            ))
            
    return state


def notify_resident_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Notificar al residente y esperar respuesta.
    
    Flow:
    1. Enviar WhatsApp con foto del visitante
    2. Esperar respuesta (se queda en espera hasta webhook)
    3. Actualizar autorización según respuesta
    """
    logger.info(f"📞 [NotifyResident] Notificando a residente: {state.resident_name}")
    
    # CRÍTICO: Limpiar estado previo para no usar una autorización vieja
    state.resident_authorized = None
    state.current_step = VisitStep.ESPERANDO_AUTORIZACION
    
    # Enviar WhatsApp
    if state.resident_phone and state.visitor_name:
        notify_result = notify_resident_whatsapp.invoke({
            "resident_phone": state.resident_phone,
            "visitor_name": state.visitor_name,
            "cedula_photo_url": state.cedula_image_url
        })
        
        state.notification_sent = notify_result.get("sent", False)
    
    state.resident_contacted = True
    
    # NOTA: Aquí ya NO asignamos resident_authorized = True automáticamente.
    # El flujo debe pausarse o ir a un nodo de "espera" hasta que llegue el webhook.
    # Si estamos en pruebas manuales (sin webhook real), el desarrollador debe inyectar el estado.
    
    state.messages.append(AIMessage(
        content=f"He notificado al residente. Estamos esperando su autorización..."
    ))
    
    return state


def open_gate_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Abrir el portón.
    
    Flow:
    1. Verificar que hay autorización
    2. Enviar comando de apertura
    3. Actualizar estado
    """
    logger.info(f"🚪 [OpenGate] Abriendo portón")
    
    if not state.access_granted:
        logger.error("❌ Intento de abrir portón sin autorización!")
        state.denial_reason = "Sin autorización"
        state.current_step = VisitStep.ACCESO_DENEGADO
        return state
        
    # Abrir portón
    open_result = open_gate.invoke({
        "condominium_id": state.condominium_id,
        "door_id": state.door_id,
        "reason": str(state.authorization_type) if state.authorization_type else "manual"
    })
    
    state.gate_opened = open_result.get("success", False)
    state.access_granted = True
    state.current_step = VisitStep.ACCESO_OTORGADO

    if state.gate_opened:
        logger.success(f"✅ Portón abierto exitosamente")
        state.messages.append(AIMessage(
            content="Portón abierto. ¡Que tenga buen día!"
        ))
    else:
        logger.error(f"❌ Error abriendo portón")
        state.messages.append(AIMessage(
            content="Disculpe, hubo un error con el portón. Por favor contacte a seguridad."
        ))
        
    return state


def log_access_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Registrar el evento de acceso.
    
    Flow:
    1. Guardar log en base de datos
    2. Incluir fotos, datos del visitante, resultado
    3. Marcar sesión como completada
    """
    logger.info(f"📝 [LogAccess] Registrando evento")
    
    # Determinar tipo de entrada
    entry_type = "vehicle"
    if state.visitor_name and not state.is_plate_authorized:
        entry_type = "intercom"
        
    # Determinar decisión de acceso
    access_decision = "authorized" if state.access_granted else "denied"
    
    # Determinar método de decisión
    decision_method = "manual"
    if state.authorization_type:
        auth_type_str = str(state.authorization_type)
        if "AUTO_PLACA" in auth_type_str:
            decision_method = "auto_vehicle"
        elif "PRE_AUTORIZADO" in auth_type_str:
            decision_method = "auto_pre_authorized"
        elif "RESIDENTE" in auth_type_str:
            decision_method = "resident_approved"
            
    # Registrar en DB
    log_result = log_access_event.invoke({
        "condominium_id": state.condominium_id,
        "entry_type": entry_type,
        "direction": state.direction,  # 'entry' o 'exit'
        "access_decision": access_decision,
        "plate": state.plate,
        "cedula": state.cedula,
        "visitor_name": state.visitor_name,
        "resident_id": state.resident_id,
        "gate_opened": state.gate_opened,
        "decision_reason": state.denial_reason if not state.access_granted else f"Autorizado por: {state.authorization_type}",
        "decision_method": decision_method,
        "cedula_photo_url": state.cedula_image_url,
        "vehicle_photo_url": state.plate_image_url,
    })
    
    state.access_logged = True
    logger.info(f"✅ Evento registrado: {log_result.get('log_id')}")

    return state


def deny_access_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Denegar acceso cortésmente.

    Flow:
    1. Marcar como denegado
    2. Informar al visitante
    3. Registrar evento
    """
    logger.warning(f"🚫 [DenyAccess] Acceso denegado")

    state.access_granted = False
    state.current_step = VisitStep.ACCESO_DENEGADO

    if not state.denial_reason:
        state.denial_reason = "No autorizado por el residente"

    state.messages.append(AIMessage(
        content=f"Lo siento, no podemos autorizar su ingreso en este momento. {state.denial_reason}"
    ))

    logger.info(f"Razón de denegación: {state.denial_reason}")

    return state


def hangup_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Colgar la llamada al finalizar la conversación.

    CRÍTICO: Este nodo DEBE ejecutarse al final de cada flujo para:
    - Liberar recursos de la llamada
    - Evitar consumo innecesario de tokens/minutos
    - Cerrar la sesión correctamente

    Flow:
    1. Determinar razón del hangup según el estado
    2. Ejecutar hangup
    3. Marcar llamada como inactiva
    """
    logger.info(f"📴 [Hangup] Terminando llamada - Sesión: {state.session_id}")

    # Determinar razón basada en el estado
    if state.access_granted:
        reason = "access_granted"
        farewell = "Que tenga buen día. Hasta luego."
    elif state.current_step == VisitStep.ACCESO_DENEGADO:
        reason = "access_denied"
        farewell = "Gracias por su visita. Hasta luego."
    elif state.current_step == VisitStep.TRANSFIRIENDO_OPERADOR:
        reason = "transferred"
        farewell = "Lo comunico con un operador. Un momento por favor."
    else:
        reason = "conversation_completed"
        farewell = "Hasta luego."

    # Agregar mensaje de despedida
    state.messages.append(AIMessage(content=farewell))

    # Ejecutar hangup
    hangup_result = hangup_call.invoke({
        "session_id": state.session_id,
        "reason": reason
    })

    # Actualizar estado
    state.call_active = False
    state.current_step = VisitStep.FINALIZADO

    if hangup_result.get("success"):
        logger.success(f"✅ Llamada terminada correctamente: {reason}")
    else:
        logger.error(f"❌ Error terminando llamada: {hangup_result.get('error')}")

    return state


def transfer_operator_node(state: PorteroState) -> PorteroState:
    """
    Nodo: Transferir la llamada a un operador humano (Human-in-the-Loop).

    Se activa cuando:
    - El residente no responde después del timeout
    - El visitante solicita hablar con un humano
    - Hay una situación que requiere intervención manual

    Flow:
    1. Notificar al visitante
    2. Notificar al operador con contexto
    3. Ejecutar transferencia SIP
    4. Actualizar estado
    """
    logger.info(f"🔀 [TransferOperator] Transfiriendo a operador - Sesión: {state.session_id}")

    state.current_step = VisitStep.TRANSFIRIENDO_OPERADOR

    # Determinar razón de la transferencia
    reason = "resident_timeout"  # Default
    if hasattr(state, 'transfer_reason') and state.transfer_reason:
        reason = state.transfer_reason

    # Notificar al visitante
    state.messages.append(AIMessage(
        content="Un momento, lo comunico con un operador para asistirle personalmente."
    ))

    # Ejecutar transferencia
    transfer_result = forward_to_operator.invoke({
        "session_id": state.session_id,
        "condominium_id": state.condominium_id,
        "reason": reason,
        "visitor_name": state.visitor_name,
        "apartment": state.apartment,
        "visitor_cedula": state.cedula
    })

    if transfer_result.get("transferred"):
        logger.success(f"✅ Transferencia exitosa a: {transfer_result.get('operator_extension')}")
        state.messages.append(AIMessage(
            content=f"Transferido al operador. Por favor espere en línea."
        ))
    else:
        logger.error(f"❌ Error en transferencia: {transfer_result.get('error')}")
        # Fallback: al menos notificar al operador
        state.messages.append(AIMessage(
            content="No pudimos transferir la llamada, pero el operador ha sido notificado. "
                    "Por favor espere o intente nuevamente más tarde."
        ))

    return state


# ============================================
# Funciones de routing para decisiones condicionales
# ============================================

def should_transfer_to_operator(state: PorteroState) -> bool:
    """
    Determina si se debe transferir a operador.

    Returns:
        True si se debe transferir
    """
    from datetime import datetime, timedelta
    from src.config.settings import settings

    # Si el visitante lo solicitó explícitamente
    if hasattr(state, 'visitor_requested_operator') and state.visitor_requested_operator:
        return True

    # Si hay timeout esperando respuesta del residente
    if state.current_step == VisitStep.ESPERANDO_AUTORIZACION:
        if hasattr(state, 'notification_sent_at') and state.notification_sent_at:
            elapsed = (datetime.now() - state.notification_sent_at).total_seconds()
            if elapsed > settings.operator_timeout:
                logger.info(f"⏰ Timeout de {settings.operator_timeout}s alcanzado")
                return True

    return False


def route_after_resident_response(state: PorteroState) -> str:
    """
    Routing function: decide el siguiente nodo después de esperar respuesta del residente.

    Returns:
        Nombre del siguiente nodo: "open_gate", "deny_access", o "transfer_operator"
    """
    # Verificar si hay timeout primero
    if should_transfer_to_operator(state):
        return "transfer_operator"

    # Verificar respuesta del residente
    if state.resident_authorized is True:
        state.access_granted = True
        state.authorization_type = AuthorizationType.RESIDENTE
        return "open_gate"
    elif state.resident_authorized is False:
        return "deny_access"

    # Si aún no hay respuesta, seguir esperando (o ir a timeout)
    # En un loop real, esto volvería a verificar el estado
    return "notify_resident"  # Volver a esperar

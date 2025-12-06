"""
Prompts centralizados para el agente de voz SITNOVA.

Este archivo contiene todos los prompts del sistema para el portero virtual.
Centralizar aquí permite fácil mantenimiento y evita duplicación.
"""

# ============================================
# SYSTEM PROMPT PRINCIPAL DEL PORTERO
# ============================================

SYSTEM_PROMPT_PORTERO = """You are a voice agent operating as a security guard for a residential condominium in Costa Rica. You speak Spanish with Costa Rican expressions. You are professional, direct, and efficient.

YOUR ROLE: Security access control. You verify visitor identity and contact residents for authorization. This is a security system, not customer service.

CRITICAL RULES - DO NOT IGNORE:
1. If there is silence, WAIT. Do NOT repeatedly ask "are you there" or "hello".
2. You MUST collect these three pieces of data before contacting the resident:
   - Full name of visitor
   - Cedula number (national ID)
   - Reason for visit
   If any is missing, ask for it before proceeding.

RESIDENT LOOKUP:
- If they say a name like "Vengo donde Juan Perez", use the lookup_resident tool with the name parameter.
- If they say a house number, use lookup_resident with the query parameter set to the number.
- If the resident is not found, ask for clarification.

MANDATORY PROTOCOL - Follow in exact order:
1. Greet and ask who they are visiting: "Buenas a quien visita"
2. Use lookup_resident tool to find the resident
3. Collect ALL visitor data: full name, cedula, visit reason
4. Use notify_resident tool with all three required fields
5. Wait for resident response and communicate decision

TOOL USAGE:
- lookup_resident: Pass either name or house number in the query parameter
- notify_resident: Requires apartamento, nombre_visitante, cedula, and visit_reason
- estado_autorizacion: Check if resident responded using apartamento parameter
- abrir_porton: Only use after authorization confirmed
- transferir_operador: Last resort if unable to proceed

RESPONSE STYLE - Keep responses very brief:
- "Buenas a quien visita"
- "Numero de casa"
- "Su nombre completo"
- "Cedula" then read back digits individually: "uno dos tres cuatro cinco"
- "Motivo de visita"
- "Un momento"
- "Autorizado puede pasar"
- "No autorizado"

Do NOT use lists, bullets, or formatting in your speech.
Do NOT give long explanations.
Do NOT share resident phone numbers or personal data.
Do NOT invent or guess information.

CEDULA FORMAT: When visitor gives cedula, repeat it back as individual digits for confirmation.
Example: If they say "one two three four five", respond "confirmo uno dos tres cuatro cinco".

SECURITY BOUNDARIES:
Your only job is access control. If asked about anything else politely decline: "Solo manejo acceso al condominio".
If you cannot verify information after reasonable attempts, use transferir_operador tool.
"""


# ============================================
# MENSAJES DE ESPERA CONTEXTUALES
# ============================================

MENSAJES_ESPERA = {
    "inicial": "Estoy contactando al residente, un momento por favor.",
    "corto": "El residente está revisando la solicitud.",
    "medio": "Seguimos esperando la respuesta del residente. Gracias por su paciencia.",
    "largo": "El residente aún no responde. ¿Desea seguir esperando o prefiere dejar un mensaje?",
    "timeout": "No hemos podido contactar al residente. Puede intentar comunicarse directamente o volver más tarde.",
}


# ============================================
# RESPUESTAS PREDEFINIDAS
# ============================================

RESPUESTAS = {
    "saludo": "Buenas, ¿a quién visita?",
    "pedir_apellido": "¿El apellido?",
    "pedir_casa": "¿Número de casa?",
    "pedir_nombre": "¿Su nombre completo?",
    "pedir_cedula": "¿Cédula?",
    "pedir_motivo": "¿Motivo de visita?",
    "notificando": "Un momento, le notifico.",
    "autorizado": "Autorizado, puede pasar.",
    "denegado": "No fue autorizado.",
    "sin_info": "Necesito nombre o número de casa.",
    "no_colabora": "Sin esa información no puedo ayudarle.",
    "ofrecer_operador": "¿Le comunico con un operador?",
    "transferir": "Le comunico con un operador.",
    "despedida_denegado": "Buen día.",
}


# ============================================
# PROMPT PARA CONTEXTO DE VISITANTE
# ============================================

def build_visitor_context_prompt(
    plate: str = None,
    name: str = None,
    vehicle_type: str = None,
    resident_name: str = None,
    apartment: str = None,
) -> str:
    """
    Construye el contexto del visitante para agregar al prompt.

    Args:
        plate: Placa del vehículo (detectada por OCR)
        name: Nombre del visitante (si lo dio previamente)
        vehicle_type: Tipo de vehículo
        resident_name: Nombre del residente que busca
        apartment: Número de casa/apartamento

    Returns:
        String con el contexto formateado
    """
    lines = []

    if plate:
        lines.append(f"- Placa del vehículo: {plate}")
    if name:
        lines.append(f"- Nombre del visitante: {name}")
    if vehicle_type:
        lines.append(f"- Tipo de vehículo: {vehicle_type}")
    if resident_name:
        lines.append(f"- Dice que visita a: {resident_name}")
    if apartment:
        lines.append(f"- Casa/Apartamento destino: {apartment}")

    if not lines:
        return "\nCONTEXTO: Sin información previa del visitante."

    return "\nCONTEXTO DEL VISITANTE ACTUAL:\n" + "\n".join(lines)


def get_full_system_prompt(
    plate: str = None,
    name: str = None,
    vehicle_type: str = None,
    resident_name: str = None,
    apartment: str = None,
) -> str:
    """
    Obtiene el prompt completo del sistema con contexto del visitante.

    Returns:
        System prompt completo listo para usar
    """
    context = build_visitor_context_prompt(
        plate=plate,
        name=name,
        vehicle_type=vehicle_type,
        resident_name=resident_name,
        apartment=apartment,
    )

    return SYSTEM_PROMPT_PORTERO + context

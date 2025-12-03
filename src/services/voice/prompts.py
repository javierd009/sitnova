"""
Prompts centralizados para el agente de voz SITNOVA.

Este archivo contiene todos los prompts del sistema para el portero virtual.
Centralizar aquí permite fácil mantenimiento y evita duplicación.
"""

# ============================================
# SYSTEM PROMPT PRINCIPAL DEL PORTERO
# ============================================

SYSTEM_PROMPT_PORTERO = """Sos el portero virtual de un condominio en Costa Rica. Hablás español tico, sos directo y rápido.

FLUJO OBLIGATORIO:
1. Saludar → "Buenas, ¿a quién visita?"
2. Buscar residente (por nombre o casa)
3. Pedir: nombre del visitante, cédula, motivo
4. Notificar al residente
5. Esperar respuesta y comunicar resultado

DATOS OBLIGATORIOS (pedir en orden):
- ¿Su nombre completo?
- ¿Número de cédula?
- ¿Motivo de la visita?

NO notificar sin estos 3 datos.

RESPUESTAS CORTAS:
- "Buenas, ¿a quién visita?"
- "¿Sabe el número de casa?"
- "¿Su nombre completo?"
- "¿Cédula?"
- "¿Motivo de visita?"
- "Un momento, le notifico."
- "Autorizado, puede pasar."
- "No fue autorizado."

PROHIBIDO:
- Leer código o texto técnico
- Dar teléfonos de residentes
- Inventar información
- Explicaciones largas

HERRAMIENTAS:
- buscar-residente: nombre O casa
- notificar-residente: con nombre, cédula, motivo
- estado-autorizacion: ver respuesta
- abrir-porton: si autorizado
- transferir-operador: último recurso
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

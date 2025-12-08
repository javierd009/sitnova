"""
Grafo de LangGraph para el agente SITNOVA.
Define el flujo de estados y decisiones del portero virtual.
"""
from typing import Optional, Literal
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from loguru import logger

from src.agent.state import PorteroState, VisitStep
from src.agent.nodes import (
    greeting_node,
    check_vehicle_node,
    validate_visitor_node,
    notify_resident_node,
    open_gate_node,
    log_access_node,
    deny_access_node,
    hangup_node,
    transfer_operator_node,
    should_transfer_to_operator,
)
from src.config.settings import settings


# ============================================
# ROUTING FUNCTIONS
# ============================================

def route_after_vehicle_check(state: PorteroState) -> Literal["open_gate", "validate_visitor"]:
    """
    Decide el siguiente paso después de verificar el vehículo.

    Returns:
        "open_gate" si está autorizado por placa
        "validate_visitor" si necesita validación adicional
    """
    if state.is_plate_authorized:
        logger.info("→ Routing: Placa autorizada → open_gate")
        return "open_gate"

    logger.info("→ Routing: Placa no autorizada → validate_visitor")
    return "validate_visitor"


def route_after_visitor_validation(state: PorteroState) -> Literal["open_gate", "notify_resident", "deny_access"]:
    """
    Decide el siguiente paso después de validar al visitante.

    Returns:
        "open_gate" si está pre-autorizado
        "notify_resident" si necesita autorización del residente
        "deny_access" si hay algún problema
    """
    if state.is_pre_authorized:
        logger.info("→ Routing: Pre-autorizado → open_gate")
        return "open_gate"

    if state.resident_id:
        logger.info("→ Routing: Notificar residente → notify_resident")
        return "notify_resident"

    logger.warning("→ Routing: Sin datos suficientes → deny_access")
    return "deny_access"


def route_after_resident_response(state: PorteroState) -> Literal["open_gate", "deny_access", "transfer_operator"]:
    """
    Decide según la respuesta del residente.

    Returns:
        "open_gate" si autorizó
        "deny_access" si denegó
        "transfer_operator" si hay timeout o el visitante lo solicitó
    """
    # Primero verificar si hay timeout o solicitud de transferencia
    if should_transfer_to_operator(state):
        logger.info("→ Routing: Timeout/Solicitud → transfer_operator")
        return "transfer_operator"

    if state.resident_authorized is True:
        logger.info("→ Routing: Residente autorizó → open_gate")
        return "open_gate"

    if state.resident_authorized is False:
        logger.warning("→ Routing: Residente denegó → deny_access")
        return "deny_access"

    # Si aún no hay respuesta clara, default a deny
    logger.warning("→ Routing: Sin respuesta clara → deny_access")
    return "deny_access"


def route_after_log_access(state: PorteroState) -> Literal["hangup", "transfer_operator"]:
    """
    Decide si colgar la llamada o transferir después de registrar el acceso.

    Returns:
        "hangup" para terminar la llamada normalmente
        "transfer_operator" si se necesita intervención humana
    """
    # Si ya se está transfiriendo, ir a transfer
    if state.current_step == VisitStep.TRANSFIRIENDO_OPERADOR:
        logger.info("→ Routing: Ya transfiriendo → transfer_operator")
        return "transfer_operator"

    # Por defecto, colgar la llamada
    logger.info("→ Routing: Log completo → hangup")
    return "hangup"


# ============================================
# GRAPH CREATION
# ============================================

def create_sitnova_graph() -> StateGraph:
    """
    Crea y configura el grafo del agente SITNOVA.

    Flow:
    START → greeting → check_vehicle
                            ├→ authorized? → open_gate → log_access → hangup → END
                            └→ not_authorized → validate_visitor
                                                    ├→ pre_authorized? → open_gate → log_access → hangup → END
                                                    └→ not_pre_authorized → notify_resident
                                                                                ├→ authorized? → open_gate → log_access → hangup → END
                                                                                ├→ denied? → deny_access → log_access → hangup → END
                                                                                └→ timeout? → transfer_operator → hangup → END

    IMPORTANTE: Todos los flujos terminan en hangup para:
    - Liberar recursos de la llamada
    - Evitar consumo innecesario de tokens/minutos

    Returns:
        StateGraph compilado listo para ejecutar
    """
    logger.info("🏗️  Creando grafo de LangGraph...")

    # Crear el grafo
    workflow = StateGraph(PorteroState)

    # ============================================
    # AGREGAR NODOS
    # ============================================
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("check_vehicle", check_vehicle_node)
    workflow.add_node("validate_visitor", validate_visitor_node)
    workflow.add_node("notify_resident", notify_resident_node)
    workflow.add_node("open_gate", open_gate_node)
    workflow.add_node("log_access", log_access_node)
    workflow.add_node("deny_access", deny_access_node)
    # Nuevos nodos para call control
    workflow.add_node("hangup", hangup_node)
    workflow.add_node("transfer_operator", transfer_operator_node)

    # ============================================
    # CONFIGURAR ENTRY POINT
    # ============================================
    workflow.set_entry_point("greeting")

    # ============================================
    # AGREGAR EDGES
    # ============================================

    # greeting → check_vehicle (siempre)
    workflow.add_edge("greeting", "check_vehicle")

    # check_vehicle → conditional (placa autorizada o no)
    workflow.add_conditional_edges(
        "check_vehicle",
        route_after_vehicle_check,
        {
            "open_gate": "open_gate",
            "validate_visitor": "validate_visitor"
        }
    )

    # validate_visitor → conditional (pre-autorizado, notificar, o denegar)
    workflow.add_conditional_edges(
        "validate_visitor",
        route_after_visitor_validation,
        {
            "open_gate": "open_gate",
            "notify_resident": "notify_resident",
            "deny_access": "deny_access"
        }
    )

    # notify_resident → conditional (autorizado, denegado, o transferir)
    workflow.add_conditional_edges(
        "notify_resident",
        route_after_resident_response,
        {
            "open_gate": "open_gate",
            "deny_access": "deny_access",
            "transfer_operator": "transfer_operator"
        }
    )

    # open_gate → log_access
    workflow.add_edge("open_gate", "log_access")

    # deny_access → log_access
    workflow.add_edge("deny_access", "log_access")

    # transfer_operator → hangup (después de transferir, terminamos nuestra parte)
    workflow.add_edge("transfer_operator", "hangup")

    # log_access → hangup (CRÍTICO: siempre colgar después de loguear)
    workflow.add_edge("log_access", "hangup")

    # hangup → END (finalización limpia)
    workflow.add_edge("hangup", END)

    logger.success("✅ Grafo creado exitosamente (con hangup y transfer)")

    return workflow


# ============================================
# GRAPH COMPILATION
# ============================================

def compile_graph(with_checkpointer: bool = True) -> StateGraph:
    """
    Compila el grafo con o sin checkpointing.

    Args:
        with_checkpointer: Si True, usa SQLite para persistir estado

    Returns:
        Grafo compilado listo para usar
    """
    workflow = create_sitnova_graph()

    if with_checkpointer:
        logger.info(f"💾 Configurando checkpointer: {settings.checkpoint_db_path}")
        conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
        memory = SqliteSaver(conn)
        app = workflow.compile(checkpointer=memory)
        logger.success("✅ Grafo compilado con checkpointing")
    else:
        app = workflow.compile()
        logger.success("✅ Grafo compilado sin checkpointing")

    return app


# ============================================
# SINGLETON INSTANCE
# ============================================

_graph_instance = None


def get_graph():
    """
    Obtiene la instancia singleton del grafo.

    Returns:
        Grafo compilado
    """
    global _graph_instance

    if _graph_instance is None:
        _graph_instance = compile_graph(with_checkpointer=True)
        logger.info("✅ Grafo global inicializado")

    return _graph_instance


# ============================================
# HELPER PARA EJECUTAR EL GRAFO
# ============================================

def run_session(initial_state: PorteroState, session_id: Optional[str] = None):
    """
    Ejecuta una sesión completa del agente.

    Args:
        initial_state: Estado inicial de la sesión
        session_id: ID opcional para checkpoint (si no se provee, usa initial_state.session_id)

    Returns:
        Estado final después de ejecutar el grafo
    """
    graph = get_graph()

    # Configuración para checkpointing
    config = {
        "configurable": {
            "thread_id": session_id or initial_state.session_id
        }
    }

    logger.info(f"🚀 Iniciando sesión: {initial_state.session_id}")

    # Ejecutar el grafo
    final_state = None
    for step_output in graph.stream(initial_state.__dict__, config):
        for node_name, node_state in step_output.items():
            logger.debug(f"  Node '{node_name}' ejecutado")
            final_state = node_state

    logger.success(f"✅ Sesión completada: {initial_state.session_id}")

    return final_state

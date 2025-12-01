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


def route_after_resident_response(state: PorteroState) -> Literal["open_gate", "deny_access"]:
    """
    Decide según la respuesta del residente.

    Returns:
        "open_gate" si autorizó
        "deny_access" si denegó o no respondió
    """
    if state.resident_authorized:
        logger.info("→ Routing: Residente autorizó → open_gate")
        return "open_gate"

    logger.warning("→ Routing: Residente no autorizó → deny_access")
    return "deny_access"


def should_log_access(state: PorteroState) -> Literal["log_access", END]:
    """
    Decide si debe registrar el acceso antes de terminar.

    Returns:
        "log_access" si aún no se ha registrado
        END si ya se registró
    """
    if not state.access_logged:
        logger.info("→ Routing: Registrar acceso → log_access")
        return "log_access"

    logger.info("→ Routing: Ya registrado → END")
    return END


# ============================================
# GRAPH CREATION
# ============================================

def create_sitnova_graph() -> StateGraph:
    """
    Crea y configura el grafo del agente SITNOVA.

    Flow:
    START → greeting → check_vehicle
                            ├→ authorized? → open_gate → log_access → END
                            └→ not_authorized → validate_visitor
                                                    ├→ pre_authorized? → open_gate → log_access → END
                                                    └→ not_pre_authorized → notify_resident
                                                                                ├→ authorized? → open_gate → log_access → END
                                                                                └→ denied? → deny_access → log_access → END

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

    # notify_resident → conditional (autorizado o denegado)
    workflow.add_conditional_edges(
        "notify_resident",
        route_after_resident_response,
        {
            "open_gate": "open_gate",
            "deny_access": "deny_access"
        }
    )

    # open_gate → log_access
    workflow.add_edge("open_gate", "log_access")

    # deny_access → log_access
    workflow.add_edge("deny_access", "log_access")

    # log_access → END
    workflow.add_edge("log_access", END)

    logger.success("✅ Grafo creado exitosamente")

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

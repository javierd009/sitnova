"""
Test del Happy Path: Vehículo autorizado → Abrir portón

Este script prueba el flujo más simple end-to-end sin necesidad de Supabase.
Usa datos mock para validar que el grafo funciona correctamente.
"""
import sys
import os
from datetime import datetime

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from loguru import logger
from src.agent.state import PorteroState, VisitStep
from src.agent.graph import run_session


def test_authorized_vehicle():
    """
    Test: Vehículo con placa autorizada debe abrir portón automáticamente.

    Flujo esperado:
    1. greeting → captura placa "ABC-123"
    2. check_vehicle → encuentra placa autorizada
    3. open_gate → abre portón
    4. log_access → registra evento
    5. END

    Expected: access_granted=True, gate_opened=True
    """
    logger.info("=" * 60)
    logger.info("🧪 TEST: Happy Path - Vehículo Autorizado")
    logger.info("=" * 60)

    # Estado inicial
    initial_state = PorteroState(
        session_id="test-session-001",
        condominium_id="test-condo-123",
        camera_id="cam_entrada",
        door_id=1,
        started_at=datetime.now(),
        last_activity=datetime.now(),
        protocol_config={
            "condominium_name": "Condominio Test"
        }
    )

    logger.info(f"📋 Estado inicial:")
    logger.info(f"  - Session ID: {initial_state.session_id}")
    logger.info(f"  - Condominio: {initial_state.condominium_id}")
    logger.info(f"  - Paso: {initial_state.current_step}")

    # Ejecutar el grafo
    logger.info("\n🚀 Ejecutando grafo...")
    logger.info("-" * 60)

    final_state = run_session(initial_state)

    # Validar resultados
    logger.info("-" * 60)
    logger.info("\n📊 Resultados:")
    logger.info(f"  - Placa capturada: {final_state.get('plate', 'N/A')}")
    logger.info(f"  - Placa autorizada: {final_state.get('is_plate_authorized', False)}")
    logger.info(f"  - Residente: {final_state.get('resident_name', 'N/A')}")
    logger.info(f"  - Apartamento: {final_state.get('apartment', 'N/A')}")
    logger.info(f"  - Acceso otorgado: {final_state.get('access_granted', False)}")
    logger.info(f"  - Portón abierto: {final_state.get('gate_opened', False)}")
    logger.info(f"  - Evento registrado: {final_state.get('access_logged', False)}")
    logger.info(f"  - Paso final: {final_state.get('current_step', 'N/A')}")

    # Assertions
    success = True

    if not final_state.get('plate'):
        logger.error("❌ FAIL: No se capturó placa")
        success = False

    if not final_state.get('is_plate_authorized'):
        logger.error("❌ FAIL: Placa no fue autorizada (debería estar en mock)")
        success = False

    if not final_state.get('access_granted'):
        logger.error("❌ FAIL: Acceso no fue otorgado")
        success = False

    if not final_state.get('gate_opened'):
        logger.error("❌ FAIL: Portón no se abrió")
        success = False

    if not final_state.get('access_logged'):
        logger.error("❌ FAIL: Evento no fue registrado")
        success = False

    if final_state.get('current_step') != VisitStep.ACCESO_OTORGADO:
        logger.error(f"❌ FAIL: Paso final incorrecto: {final_state.get('current_step')}")
        success = False

    # Resultado final
    logger.info("\n" + "=" * 60)
    if success:
        logger.success("✅ TEST PASSED: Flujo completo exitoso")
        logger.info("\n📋 Resumen:")
        logger.info("  1. ✅ Placa capturada")
        logger.info("  2. ✅ Placa verificada y autorizada")
        logger.info("  3. ✅ Portón abierto")
        logger.info("  4. ✅ Evento registrado")
    else:
        logger.error("❌ TEST FAILED: Revisar logs arriba")

    logger.info("=" * 60)

    return success


def test_unauthorized_visitor():
    """
    Test: Visitante no autorizado con residente que autoriza.

    Este test simula un flujo donde:
    1. La placa ABC-123 está autorizada (mock)
    2. El residente ya está contactado y autorizó
    3. Debe abrir el portón exitosamente

    Flujo: greeting → check_vehicle → open_gate → log_access
    """
    logger.info("\n" + "=" * 60)
    logger.info("🧪 TEST: Flujo Autorizado por Residente")
    logger.info("=" * 60)

    initial_state = PorteroState(
        session_id="test-session-002",
        condominium_id="test-condo-123",
        resident_id="test-resident-456",
        resident_name="María González",
        resident_phone="+50612345678",
        apartment="205",
        camera_id="cam_entrada",
        door_id=1,
        started_at=datetime.now(),
        last_activity=datetime.now(),
        protocol_config={"condominium_name": "Condominio Test"},
        # Pre-autorización del residente
        resident_contacted=True,
        resident_authorized=True
    )

    logger.info("🚀 Ejecutando grafo...")
    final_state = run_session(initial_state)

    logger.info("\n📊 Resultados:")
    logger.info(f"  - Placa capturada: {final_state.get('plate', 'N/A')}")
    logger.info(f"  - Residente: {final_state.get('resident_name', 'N/A')}")
    logger.info(f"  - Residente contactado: {final_state.get('resident_contacted', False)}")
    logger.info(f"  - Autorizado: {final_state.get('resident_authorized', False)}")
    logger.info(f"  - Acceso otorgado: {final_state.get('access_granted', False)}")
    logger.info(f"  - Portón abierto: {final_state.get('gate_opened', False)}")

    success = (
        final_state.get('plate') and
        final_state.get('access_granted') and
        final_state.get('gate_opened')
    )

    if success:
        logger.success("✅ TEST PASSED: Flujo autorizado completo")
    else:
        logger.error("❌ TEST FAILED: Revisar logs")

    logger.info("=" * 60)

    return success


if __name__ == "__main__":
    logger.info("\n🎯 SITNOVA - Tests End-to-End\n")

    # Test 1: Happy Path
    test1 = test_authorized_vehicle()

    # Test 2: Visitor Flow
    test2 = test_unauthorized_visitor()

    # Resumen
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMEN DE TESTS")
    logger.info("=" * 60)
    logger.info(f"Test 1 (Vehículo autorizado): {'✅ PASS' if test1 else '❌ FAIL'}")
    logger.info(f"Test 2 (Visitante): {'✅ PASS' if test2 else '❌ FAIL'}")
    logger.info("=" * 60)

    # Exit code
    exit(0 if test1 and test2 else 1)

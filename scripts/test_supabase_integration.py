"""
Test de integración con Supabase.
Verifica que los tools del agente se conectan correctamente a la base de datos.
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


def test_supabase_integration():
    """Test de integración con Supabase."""

    logger.info("🧪 SITNOVA - Test de Integración con Supabase")
    logger.info("=" * 60)

    # Obtener el condominium_id de los datos de prueba
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    client = create_client(supabase_url, supabase_key)

    # Obtener ID del condominio de prueba
    condo = client.table("condominiums").select("id").eq("slug", "los-almendros").execute()
    if not condo.data:
        logger.error("❌ No se encontró el condominio de prueba. Ejecuta primero: python scripts/seed_data.py")
        return False

    condominium_id = condo.data[0]["id"]
    logger.info(f"📋 Usando condominio: {condominium_id}")
    logger.info("")

    tests_passed = 0
    tests_failed = 0

    # ============================================
    # TEST 1: check_authorized_vehicle - Placa autorizada
    # ============================================
    logger.info("🧪 TEST 1: Verificar placa autorizada (ABC-123)")

    try:
        from src.agent.tools import check_authorized_vehicle

        result = check_authorized_vehicle.invoke({
            "condominium_id": condominium_id,
            "plate": "ABC-123"
        })

        if result.get("authorized"):
            logger.success(f"   ✅ PASSED: Placa ABC-123 autorizada")
            logger.info(f"      Residente: {result.get('resident_name')}")
            logger.info(f"      Casa: {result.get('apartment')}")
            tests_passed += 1
        else:
            logger.error(f"   ❌ FAILED: Placa ABC-123 debería estar autorizada")
            logger.error(f"      Resultado: {result}")
            tests_failed += 1

    except Exception as e:
        logger.error(f"   ❌ FAILED: Error en check_authorized_vehicle: {e}")
        tests_failed += 1

    # ============================================
    # TEST 2: check_authorized_vehicle - Placa NO autorizada
    # ============================================
    logger.info("")
    logger.info("🧪 TEST 2: Verificar placa NO autorizada (ZZZ-999)")

    try:
        result = check_authorized_vehicle.invoke({
            "condominium_id": condominium_id,
            "plate": "ZZZ-999"
        })

        if not result.get("authorized"):
            logger.success(f"   ✅ PASSED: Placa ZZZ-999 correctamente no autorizada")
            tests_passed += 1
        else:
            logger.error(f"   ❌ FAILED: Placa ZZZ-999 no debería estar autorizada")
            tests_failed += 1

    except Exception as e:
        logger.error(f"   ❌ FAILED: Error: {e}")
        tests_failed += 1

    # ============================================
    # TEST 3: check_pre_authorized_visitor - Cédula pre-autorizada
    # ============================================
    logger.info("")
    logger.info("🧪 TEST 3: Verificar cédula pre-autorizada (1-2345-6789)")

    try:
        from src.agent.tools import check_pre_authorized_visitor

        result = check_pre_authorized_visitor.invoke({
            "condominium_id": condominium_id,
            "cedula": "1-2345-6789"
        })

        if result.get("authorized"):
            logger.success(f"   ✅ PASSED: Cédula 1-2345-6789 pre-autorizada")
            logger.info(f"      Residente anfitrión: {result.get('resident_name')}")
            tests_passed += 1
        else:
            logger.error(f"   ❌ FAILED: Cédula 1-2345-6789 debería estar pre-autorizada")
            logger.error(f"      Resultado: {result}")
            tests_failed += 1

    except Exception as e:
        logger.error(f"   ❌ FAILED: Error: {e}")
        tests_failed += 1

    # ============================================
    # TEST 4: check_pre_authorized_visitor - Cédula NO pre-autorizada
    # ============================================
    logger.info("")
    logger.info("🧪 TEST 4: Verificar cédula NO pre-autorizada (9-9999-9999)")

    try:
        result = check_pre_authorized_visitor.invoke({
            "condominium_id": condominium_id,
            "cedula": "9-9999-9999"
        })

        if not result.get("authorized"):
            logger.success(f"   ✅ PASSED: Cédula 9-9999-9999 correctamente no autorizada")
            tests_passed += 1
        else:
            logger.error(f"   ❌ FAILED: Cédula 9-9999-9999 no debería estar pre-autorizada")
            tests_failed += 1

    except Exception as e:
        logger.error(f"   ❌ FAILED: Error: {e}")
        tests_failed += 1

    # ============================================
    # TEST 5: log_access_event - Registrar evento de acceso
    # ============================================
    logger.info("")
    logger.info("🧪 TEST 5: Registrar evento de acceso")

    try:
        from src.agent.tools import log_access_event

        result = log_access_event.invoke({
            "condominium_id": condominium_id,
            "entry_type": "vehicle",
            "access_decision": "authorized",
            "plate": "ABC-123",
            "decision_reason": "Test de integración",
            "decision_method": "auto_vehicle",
            "gate_opened": True,
        })

        if result.get("success"):
            logger.success(f"   ✅ PASSED: Evento registrado")
            logger.info(f"      Log ID: {result.get('log_id')}")
            tests_passed += 1
        else:
            logger.error(f"   ❌ FAILED: No se pudo registrar el evento")
            logger.error(f"      Error: {result.get('error')}")
            tests_failed += 1

    except Exception as e:
        logger.error(f"   ❌ FAILED: Error: {e}")
        tests_failed += 1

    # ============================================
    # RESUMEN
    # ============================================
    logger.info("")
    logger.info("=" * 60)
    total = tests_passed + tests_failed

    if tests_failed == 0:
        logger.success(f"🎉 TODOS LOS TESTS PASARON: {tests_passed}/{total}")
    else:
        logger.warning(f"⚠️  RESULTADOS: {tests_passed} passed, {tests_failed} failed de {total}")

    logger.info("")

    return tests_failed == 0


if __name__ == "__main__":
    success = test_supabase_integration()
    sys.exit(0 if success else 1)

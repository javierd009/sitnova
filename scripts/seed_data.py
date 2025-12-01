"""
Script para insertar datos de prueba en Supabase.
Crea un condominio, residentes, vehículos y visitantes pre-autorizados.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Configurar logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


def seed_database():
    """Inserta datos de prueba en Supabase."""

    logger.info("🌱 SITNOVA - Seed Data")
    logger.info("=" * 60)

    # Verificar credenciales
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados en .env")
        return False

    try:
        from supabase import create_client

        logger.info("🔌 Conectando a Supabase...")
        client = create_client(supabase_url, supabase_key)
        logger.success("✅ Conexión exitosa")
        logger.info("")

    except Exception as e:
        logger.error(f"❌ Error conectando a Supabase: {e}")
        return False

    # ============================================
    # 1. CREAR CONDOMINIO DE PRUEBA
    # ============================================
    logger.info("🏢 Creando condominio de prueba...")

    condominium_data = {
        "name": "Residencial Los Almendros",
        "slug": "los-almendros",
        "address": "500m Norte del Hospital San Juan de Dios",
        "city": "San José",
        "state": "Costa Rica",
        "phone": "+506 2222-3333",
        "email": "admin@losalmendros.cr",
        "subscription_plan": "pro",
        "subscription_status": "active",
        "max_residents": 100,
        "max_access_points": 2,
        "whatsapp_enabled": True,
        "push_enabled": True,
        "is_active": True,
    }

    try:
        # Verificar si ya existe
        existing = client.table("condominiums").select("id").eq("slug", "los-almendros").execute()

        if existing.data:
            condominium_id = existing.data[0]["id"]
            logger.info(f"   ℹ️  Condominio ya existe: {condominium_id}")
        else:
            result = client.table("condominiums").insert(condominium_data).execute()
            condominium_id = result.data[0]["id"]
            logger.success(f"   ✅ Condominio creado: {condominium_id}")

    except Exception as e:
        logger.error(f"   ❌ Error creando condominio: {e}")
        return False

    # ============================================
    # 2. CREAR RESIDENTES DE PRUEBA
    # ============================================
    logger.info("")
    logger.info("👥 Creando residentes de prueba...")

    residents_data = [
        {
            "condominium_id": condominium_id,
            "first_name": "Juan",
            "last_name": "Pérez García",
            "email": "juan.perez@email.com",
            "phone_primary": "+50688881111",
            "phone_mobile": "+50688881111",
            "unit_number": "101",
            "unit_type": "house",
            "is_active": True,
            "is_owner": True,
        },
        {
            "condominium_id": condominium_id,
            "first_name": "María",
            "last_name": "González Solís",
            "email": "maria.gonzalez@email.com",
            "phone_primary": "+50688882222",
            "phone_mobile": "+50688882222",
            "unit_number": "102",
            "unit_type": "house",
            "is_active": True,
            "is_owner": True,
        },
        {
            "condominium_id": condominium_id,
            "first_name": "Carlos",
            "last_name": "Rodríguez Mora",
            "email": "carlos.rodriguez@email.com",
            "phone_primary": "+50688883333",
            "phone_mobile": "+50688883333",
            "unit_number": "103",
            "unit_type": "apartment",
            "building": "Torre A",
            "floor": "3",
            "is_active": True,
            "is_owner": False,
        },
    ]

    resident_ids = {}

    for resident in residents_data:
        try:
            # Verificar si ya existe
            existing = client.table("residents").select("id").eq(
                "condominium_id", condominium_id
            ).eq(
                "unit_number", resident["unit_number"]
            ).execute()

            if existing.data:
                resident_ids[resident["unit_number"]] = existing.data[0]["id"]
                logger.info(f"   ℹ️  Residente {resident['first_name']} ya existe")
            else:
                result = client.table("residents").insert(resident).execute()
                resident_ids[resident["unit_number"]] = result.data[0]["id"]
                logger.success(f"   ✅ Residente creado: {resident['first_name']} {resident['last_name']} (Casa {resident['unit_number']})")

        except Exception as e:
            logger.error(f"   ❌ Error creando residente {resident['first_name']}: {e}")

    # ============================================
    # 3. CREAR VEHÍCULOS AUTORIZADOS
    # ============================================
    logger.info("")
    logger.info("🚗 Creando vehículos autorizados...")

    vehicles_data = [
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("101"),
            "license_plate": "ABC-123",
            "brand": "Toyota",
            "model": "Corolla",
            "year": 2022,
            "color": "Blanco",
            "vehicle_type": "car",
            "auto_authorize": True,
            "is_active": True,
        },
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("101"),
            "license_plate": "DEF-456",
            "brand": "Honda",
            "model": "CR-V",
            "year": 2021,
            "color": "Negro",
            "vehicle_type": "car",
            "auto_authorize": True,
            "is_active": True,
        },
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("102"),
            "license_plate": "GHI-789",
            "brand": "Hyundai",
            "model": "Tucson",
            "year": 2023,
            "color": "Gris",
            "vehicle_type": "car",
            "auto_authorize": True,
            "is_active": True,
        },
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("103"),
            "license_plate": "MOT-001",
            "brand": "Yamaha",
            "model": "MT-07",
            "year": 2022,
            "color": "Azul",
            "vehicle_type": "motorcycle",
            "auto_authorize": True,
            "is_active": True,
        },
    ]

    for vehicle in vehicles_data:
        if not vehicle["resident_id"]:
            continue

        try:
            # Verificar si ya existe
            existing = client.table("vehicles").select("id").eq(
                "condominium_id", condominium_id
            ).eq(
                "license_plate", vehicle["license_plate"]
            ).execute()

            if existing.data:
                logger.info(f"   ℹ️  Vehículo {vehicle['license_plate']} ya existe")
            else:
                result = client.table("vehicles").insert(vehicle).execute()
                logger.success(f"   ✅ Vehículo creado: {vehicle['license_plate']} ({vehicle['brand']} {vehicle['model']})")

        except Exception as e:
            logger.error(f"   ❌ Error creando vehículo {vehicle['license_plate']}: {e}")

    # ============================================
    # 4. CREAR VISITANTES PRE-AUTORIZADOS
    # ============================================
    logger.info("")
    logger.info("🪪 Creando visitantes pre-autorizados...")

    # Fechas de vigencia
    now = datetime.now()
    valid_from = now.isoformat()
    valid_until = (now + timedelta(days=30)).isoformat()

    pre_authorized_data = [
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("101"),
            "full_name": "Pedro Jiménez López",
            "phone": "+50688884444",
            "id_type": "cedula",
            "id_number": "1-2345-6789",
            "vehicle_plate": "XYZ-999",
            "valid_from": valid_from,
            "valid_until": valid_until,
            "auto_authorize": True,
            "visitor_type": "family",
            "purpose": "Visita familiar",
        },
        {
            "condominium_id": condominium_id,
            "resident_id": resident_ids.get("102"),
            "full_name": "Ana Martínez Vargas",
            "phone": "+50688885555",
            "id_type": "cedula",
            "id_number": "2-3456-7890",
            "valid_from": valid_from,
            "valid_until": valid_until,
            "auto_authorize": True,
            "visitor_type": "service",
            "purpose": "Servicio de limpieza",
        },
    ]

    for visitor in pre_authorized_data:
        if not visitor["resident_id"]:
            continue

        try:
            # Verificar si ya existe
            existing = client.table("pre_authorized_visitors").select("id").eq(
                "condominium_id", condominium_id
            ).eq(
                "id_number", visitor["id_number"]
            ).execute()

            if existing.data:
                logger.info(f"   ℹ️  Visitante {visitor['full_name']} ya existe")
            else:
                result = client.table("pre_authorized_visitors").insert(visitor).execute()
                logger.success(f"   ✅ Visitante pre-autorizado: {visitor['full_name']} (Cédula: {visitor['id_number']})")

        except Exception as e:
            logger.error(f"   ❌ Error creando visitante {visitor['full_name']}: {e}")

    # ============================================
    # 5. CREAR PROTOCOLO DE ATENCIÓN
    # ============================================
    logger.info("")
    logger.info("📋 Creando protocolo de atención...")

    protocol_data = {
        "condominium_id": condominium_id,
        "name": "Protocolo Estándar",
        "description": "Protocolo de atención estándar para Residencial Los Almendros",
        "protocol_config": {
            "greeting": {
                "message": "Bienvenido a Residencial Los Almendros. ¿A quién visita?",
                "voice_settings": {
                    "language": "es-CR",
                    "speed": 1.0,
                    "tone": "professional"
                }
            },
            "visitor_flow": {
                "check_pre_authorized": True,
                "check_vehicle_plate": True,
                "require_resident_approval": True,
                "max_wait_time_seconds": 30,
                "retry_call_times": 2
            },
            "business_hours": {
                "enabled": True,
                "start": "06:00",
                "end": "22:00",
                "timezone": "America/Costa_Rica"
            }
        },
        "auto_authorize_known_vehicles": True,
        "require_cedula_always": True,
        "require_resident_approval": True,
        "is_default": True,
        "is_active": True,
    }

    try:
        existing = client.table("attention_protocols").select("id").eq(
            "condominium_id", condominium_id
        ).eq(
            "name", "Protocolo Estándar"
        ).execute()

        if existing.data:
            logger.info(f"   ℹ️  Protocolo ya existe")
        else:
            result = client.table("attention_protocols").insert(protocol_data).execute()
            logger.success(f"   ✅ Protocolo creado: {protocol_data['name']}")

    except Exception as e:
        logger.error(f"   ❌ Error creando protocolo: {e}")

    # ============================================
    # RESUMEN
    # ============================================
    logger.info("")
    logger.info("=" * 60)
    logger.success("🎉 Seed data completado!")
    logger.info("")
    logger.info("📊 Resumen:")
    logger.info(f"   🏢 Condominio: Residencial Los Almendros")
    logger.info(f"   🆔 ID: {condominium_id}")
    logger.info(f"   👥 Residentes: 3")
    logger.info(f"   🚗 Vehículos: 4")
    logger.info(f"   🪪 Visitantes pre-autorizados: 2")
    logger.info("")
    logger.info("📋 Datos de prueba para testing:")
    logger.info(f"   Placa autorizada: ABC-123 → Juan Pérez (Casa 101)")
    logger.info(f"   Placa autorizada: GHI-789 → María González (Casa 102)")
    logger.info(f"   Cédula pre-autorizada: 1-2345-6789 → Pedro Jiménez")
    logger.info("")

    return True


if __name__ == "__main__":
    seed_database()

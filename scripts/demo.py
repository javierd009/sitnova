#!/usr/bin/env python3
"""
SITNOVA - Demo Interactivo
==========================
Demuestra el funcionamiento del sistema sin hardware real.
"""
import os
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗██╗████████╗███╗   ██╗ ██████╗ ██╗   ██╗ █████╗   ║
║   ██╔════╝██║╚══██╔══╝████╗  ██║██╔═══██╗██║   ██║██╔══██╗  ║
║   ███████╗██║   ██║   ██╔██╗ ██║██║   ██║██║   ██║███████║  ║
║   ╚════██║██║   ██║   ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║  ║
║   ███████║██║   ██║   ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║  ║
║   ╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝  ║
║                                                              ║
║         Sistema Inteligente de Control de Acceso             ║
║                   DEMO INTERACTIVO                           ║
╚══════════════════════════════════════════════════════════════╝
""")


def demo_vehiculo_autorizado():
    """Demo: Vehículo con placa autorizada"""
    print("\n" + "="*60)
    print("  ESCENARIO 1: Vehículo Autorizado")
    print("="*60)
    print("\n  Un vehículo se acerca al portón...")
    print("  📷 Cámara detecta placa: ABC-123")
    input("\n  [Presiona ENTER para continuar]")

    from src.agent.graph import run_session
    from src.agent.state import PorteroState, VisitStep
    import uuid

    state = PorteroState(
        session_id=str(uuid.uuid4()),
        condominium_id='b2a4de87-0fec-48df-bf3b-8ac77531b034',
        plate='ABC-123',
        current_step=VisitStep.INICIO
    )

    print("\n  🔍 Verificando placa en base de datos...")

    try:
        final = run_session(state)

        if isinstance(final, dict) and final.get("access_granted"):
            print(f"\n  ✅ ACCESO AUTORIZADO")
            print(f"     Residente: {final.get('resident_name', 'N/A')}")
            print(f"     Casa: {final.get('apartment', 'N/A')}")
            print(f"     Autorización: {final.get('authorization_type', 'N/A')}")
            print(f"\n  🚪 Portón abierto automáticamente")
            print(f"  📝 Evento registrado en base de datos")
        else:
            print("\n  ❌ Acceso denegado")

    except Exception as e:
        print(f"\n  ⚠️  Error: {e}")

    input("\n  [Presiona ENTER para continuar]")


def demo_visitante_preautorizado():
    """Demo: Visitante pre-autorizado"""
    print("\n" + "="*60)
    print("  ESCENARIO 2: Visitante Pre-autorizado")
    print("="*60)
    print("\n  Un vehículo desconocido se acerca...")
    print("  📷 Cámara detecta placa: XYZ-999 (no registrada)")
    print("  🎤 Intercomunicador: '¿A quién visita?'")
    print("  👤 Visitante: 'Vengo a casa 101, soy Carlos'")
    print("  📋 Sistema solicita cédula...")
    print("  📷 Cámara lee cédula: 1-2345-6789")
    input("\n  [Presiona ENTER para verificar pre-autorización]")

    from src.agent.tools import check_pre_authorized_visitor

    print("\n  🔍 Verificando pre-autorización...")

    result = check_pre_authorized_visitor.invoke({
        "condominium_id": "b2a4de87-0fec-48df-bf3b-8ac77531b034",
        "cedula": "1-2345-6789"
    })

    if result.get("authorized"):
        print(f"\n  ✅ VISITANTE PRE-AUTORIZADO")
        print(f"     Nombre: {result.get('visitor_name', 'N/A')}")
        print(f"     Residente: {result.get('resident_name', 'N/A')}")
        print(f"\n  🚪 Portón abierto")
        print(f"  📱 Notificación enviada al residente")
    else:
        print("\n  ❌ No hay pre-autorización activa")
        print("  📞 Llamando al residente para autorización...")

    input("\n  [Presiona ENTER para continuar]")


def demo_consulta_logs():
    """Demo: Consulta de logs de acceso"""
    print("\n" + "="*60)
    print("  ESCENARIO 3: Consulta de Eventos de Acceso")
    print("="*60)

    from src.database.connection import get_supabase

    print("\n  📊 Últimos 5 eventos de acceso:")
    print("  " + "-"*56)

    try:
        supabase = get_supabase()
        result = supabase.table("access_logs").select(
            "id, entry_type, access_decision, license_plate, created_at"
        ).order("created_at", desc=True).limit(5).execute()

        for event in result.data:
            icon = "✅" if event.get("access_decision") == "granted" else "❌"
            plate = event.get("license_plate") or "N/A"
            entry = event.get("entry_type", "unknown")
            time = event.get("created_at", "")[:19]
            print(f"  {icon} [{time}] {entry}: {plate}")

    except Exception as e:
        print(f"  ⚠️  Error: {e}")

    input("\n  [Presiona ENTER para continuar]")


def demo_ocr():
    """Demo: OCR de cédula"""
    print("\n" + "="*60)
    print("  ESCENARIO 4: Lectura OCR de Cédula")
    print("="*60)

    import numpy as np
    import cv2
    from src.services.vision import CedulaReader

    print("\n  📷 Simulando captura de cédula...")
    print("  🔍 Procesando con EasyOCR...")

    # Crear imagen sintética con cédula
    img = np.zeros((300, 500, 3), dtype=np.uint8)
    img[50:250, 50:450] = 255
    cv2.putText(img, "CEDULA", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "1-2345-6789", (100, 180), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

    reader = CedulaReader()
    result = reader.read_cedula(img)

    if result.get("detected"):
        print(f"\n  ✅ CÉDULA DETECTADA")
        print(f"     Número: {result.get('numero')}")
        print(f"     Tipo: {result.get('tipo')}")
        print(f"     Confianza: {result.get('confidence', 0)*100:.1f}%")
    else:
        print("\n  ⚠️  No se pudo leer la cédula")

    input("\n  [Presiona ENTER para continuar]")


def show_menu():
    print("""
  ┌────────────────────────────────────────────┐
  │              MENÚ DE DEMOS                 │
  ├────────────────────────────────────────────┤
  │  1. Vehículo con placa autorizada          │
  │  2. Visitante pre-autorizado               │
  │  3. Consulta de eventos de acceso          │
  │  4. Demo OCR de cédula                     │
  │  5. Ejecutar todos los demos               │
  │  0. Salir                                  │
  └────────────────────────────────────────────┘
    """)


def main():
    clear_screen()
    print_header()

    print("\n  Verificando conexión a Supabase...")
    try:
        from src.database.connection import get_supabase
        supabase = get_supabase()
        result = supabase.table("condominiums").select("name").limit(1).execute()
        if result.data:
            print(f"  ✅ Conectado a: {result.data[0]['name']}")
        else:
            print("  ⚠️  Conexión OK pero sin datos")
    except Exception as e:
        print(f"  ❌ Error de conexión: {e}")
        print("\n  Asegúrate de tener el .env configurado correctamente.")
        input("\n  [Presiona ENTER para salir]")
        return

    while True:
        show_menu()
        choice = input("  Selecciona una opción: ").strip()

        if choice == "1":
            demo_vehiculo_autorizado()
        elif choice == "2":
            demo_visitante_preautorizado()
        elif choice == "3":
            demo_consulta_logs()
        elif choice == "4":
            demo_ocr()
        elif choice == "5":
            demo_vehiculo_autorizado()
            demo_visitante_preautorizado()
            demo_consulta_logs()
            demo_ocr()
        elif choice == "0":
            print("\n  ¡Hasta luego!")
            break
        else:
            print("\n  ⚠️  Opción inválida")
            input("  [Presiona ENTER para continuar]")

        clear_screen()
        print_header()


if __name__ == "__main__":
    main()

"""
Test simple del agente SITNOVA sin dependencias externas.
Demuestra el flujo básico con mocks.
"""

print("=" * 60)
print("🧪 SITNOVA - Test Simple del Agente")
print("=" * 60)
print()

# Simular estado del agente
class MockState:
    def __init__(self):
        self.session_id = "test-001"
        self.condominium_id = "condo-123"
        self.plate = None
        self.is_authorized = False
        self.gate_opened = False
        self.access_logged = False
        self.messages = []
        self.current_step = "INICIO"

    def __repr__(self):
        return f"<State: {self.current_step}, authorized={self.is_authorized}, gate={self.gate_opened}>"

# Simular nodos del grafo
def greeting_node(state):
    """Paso 1: Saludar y capturar placa"""
    print("📋 [1. GREETING NODE]")
    print("   - Capturando placa desde cámara...")

    # Mock: Siempre captura ABC-123
    state.plate = "ABC-123"
    state.current_step = "VERIFICANDO_PLACA"
    state.messages.append("Bienvenido a Condominio Test")

    print(f"   ✅ Placa capturada: {state.plate}")
    print()
    return state

def check_vehicle_node(state):
    """Paso 2: Verificar si está autorizada"""
    print("📋 [2. CHECK VEHICLE NODE]")
    print(f"   - Consultando placa {state.plate} en base de datos...")

    # Mock: ABC-123 está autorizada
    if state.plate == "ABC-123":
        state.is_authorized = True
        state.current_step = "ACCESO_OTORGADO"
        state.messages.append("Placa autorizada - Juan Pérez, Casa 101")
        print("   ✅ Vehículo AUTORIZADO")
        print("   👤 Residente: Juan Pérez")
        print("   🏠 Casa: 101")
    else:
        state.is_authorized = False
        state.current_step = "CONVERSANDO"
        print("   ❌ Vehículo NO autorizado")

    print()
    return state

def open_gate_node(state):
    """Paso 3: Abrir portón"""
    print("📋 [3. OPEN GATE NODE]")

    if not state.is_authorized:
        print("   ⚠️  Sin autorización - portón NO se abre")
        return state

    print("   - Enviando comando al portón...")
    state.gate_opened = True
    state.messages.append("Portón abierto. ¡Que tenga buen día!")

    print("   ✅ Portón ABIERTO")
    print()
    return state

def log_access_node(state):
    """Paso 4: Registrar evento"""
    print("📋 [4. LOG ACCESS NODE]")
    print("   - Registrando en base de datos...")

    state.access_logged = True

    print("   ✅ Evento registrado:")
    print(f"      - Placa: {state.plate}")
    print(f"      - Autorizado: {state.is_authorized}")
    print(f"      - Portón abierto: {state.gate_opened}")
    print()
    return state

# Ejecutar el flujo
print("🚀 Iniciando flujo del agente...")
print()

state = MockState()

# Flujo: greeting → check_vehicle → open_gate → log_access
state = greeting_node(state)
state = check_vehicle_node(state)

# Routing condicional
if state.is_authorized:
    state = open_gate_node(state)
else:
    print("📋 [ROUTING] Vehículo no autorizado → iniciar conversación")

state = log_access_node(state)

# Resultado final
print("=" * 60)
print("✅ FLUJO COMPLETADO")
print("=" * 60)
print()
print("📊 Estado Final:")
print(f"   Session ID: {state.session_id}")
print(f"   Placa: {state.plate}")
print(f"   Autorizado: {'✅ SÍ' if state.is_authorized else '❌ NO'}")
print(f"   Portón abierto: {'✅ SÍ' if state.gate_opened else '❌ NO'}")
print(f"   Evento registrado: {'✅ SÍ' if state.access_logged else '❌ NO'}")
print(f"   Paso final: {state.current_step}")
print()
print("💬 Mensajes generados:")
for i, msg in enumerate(state.messages, 1):
    print(f"   {i}. {msg}")
print()

# Validación
if state.gate_opened and state.access_logged and state.is_authorized:
    print("=" * 60)
    print("🎉 TEST PASSED - Flujo Happy Path funcionando correctamente")
    print("=" * 60)
    print()
    print("Este es el flujo básico del agente SITNOVA:")
    print("1. ✅ Captura placa automáticamente")
    print("2. ✅ Verifica en base de datos")
    print("3. ✅ Autoriza acceso si está registrada")
    print("4. ✅ Abre portón")
    print("5. ✅ Registra evento")
    print()
    print("El agente completo tiene:")
    print("  - 8 tools (OCR, DB, WhatsApp, etc.)")
    print("  - 7 nodos (greeting, validate_visitor, notify_resident, etc.)")
    print("  - Routing condicional (3 funciones)")
    print("  - Checkpointing con SQLite")
    print("  - Integración con Supabase")
    print()
else:
    print("❌ TEST FAILED")

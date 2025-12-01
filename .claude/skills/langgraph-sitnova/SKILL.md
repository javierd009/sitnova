---
name: langgraph-sitnova
description: LangGraph framework skill for implementing SITNOVA's stateful AI operator with StateGraph, tools, and conditional routing for security gate automation.
license: MIT
---

# LangGraph Skill for SITNOVA

## Purpose

This skill provides comprehensive guidance for implementing SITNOVA (Sistema Inteligente de Control de Acceso) using LangGraph, a framework for building stateful, multi-actor applications with LLMs. LangGraph enables the creation of complex conditional flows through **StateGraph** - a state machine that manages the virtual operator's decision-making process.

SITNOVA is a virtual operator system for security gates in Costa Rica that simulates human operator functions: answering calls, identifying visitors through OCR (license plates and cédulas), consulting residents, and controlling gate access. LangGraph's checkpointing and conditional routing capabilities make it ideal for managing the complex state transitions required in this real-time security system.

## When to Use

Activate this skill when:

- Implementing the SITNOVA virtual operator state machine
- Designing StateGraph flows for security gate scenarios
- Creating tools for OCR, database queries, notifications, or gate control
- Integrating Ultravox voice AI with LangGraph state management
- Building conditional routing logic for visitor authorization
- Implementing multi-tenant state isolation for different condominiums
- Debugging graph execution or state persistence issues
- Optimizing latency in real-time gate control systems

## Core Concepts

### StateGraph Architecture

LangGraph uses a **StateGraph** to manage state transitions:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import AnyMessage

class OperatorState(TypedDict):
    """State for SITNOVA virtual operator"""
    # Conversation
    messages: Annotated[list[AnyMessage], "Conversation history"]

    # Call context
    condominium_id: str
    caller_phone: str
    call_sid: str

    # Identification data
    plate_number: str | None
    plate_ocr_confidence: float | None
    cedula_number: str | None
    cedula_ocr_data: dict | None

    # Visitor info
    visitor_name: str | None
    visitor_purpose: str | None
    resident_id: str | None
    resident_name: str | None

    # Authorization
    is_authorized: bool
    authorization_method: Literal["pre_authorized", "resident_approved", "protocol_auto", "denied"] | None

    # Actions taken
    gate_opened: bool
    notification_sent: bool
    access_logged: bool
```

### Graph Flow Design

```
START
  ↓
greeting_node → analyze_request → check_vehicle
  ↓                                    ↓
  ├─ known_vehicle? → YES → auto_authorize → open_gate → log_access → END
  ↓                    ↓
  └─ NO → validate_visitor → capture_cedula
           ↓                      ↓
           ├─ pre_authorized? → YES → open_gate → log_access → END
           ↓                     ↓
           └─ NO → notify_resident → wait_approval
                    ↓                    ↓
                    └─────────────────→ approved? → YES → open_gate → log_access → END
                                         ↓
                                         NO → polite_denial → log_access → END
```

### Conditional Routing

Use routing functions to determine next node:

```python
def route_after_vehicle_check(state: OperatorState) -> Literal["auto_authorize", "validate_visitor"]:
    """Route based on vehicle recognition"""
    if state["plate_number"] and state["plate_ocr_confidence"] > 0.85:
        # Check if vehicle is authorized
        vehicle = check_authorized_vehicle(
            state["condominium_id"],
            state["plate_number"]
        )
        if vehicle:
            return "auto_authorize"
    return "validate_visitor"

def route_after_visitor_validation(state: OperatorState) -> Literal["open_gate", "notify_resident"]:
    """Route based on visitor authorization"""
    if state["is_authorized"]:
        return "open_gate"
    return "notify_resident"
```

## How to Use

### Step 1: Define State Structure

Create a TypedDict with all possible state variables:

```python
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import AnyMessage

class OperatorState(TypedDict):
    # Core conversation
    messages: Annotated[list[AnyMessage], "Message history with reducer"]

    # Multi-tenant context
    condominium_id: str  # Tenant isolation
    protocol_config: dict  # Per-condominium rules

    # Identification
    plate_number: str | None
    cedula_number: str | None

    # Authorization
    is_authorized: bool
    authorization_reason: str | None

    # Actions
    gate_opened: bool
    access_logged: bool
```

**Key Points:**
- Use `Annotated` for lists to enable message history merging
- Include tenant context for multi-tenant isolation
- Use `| None` for optional fields discovered during flow
- Add boolean flags for tracking actions taken

### Step 2: Create Tools

Define tools using `@tool` decorator for LangGraph:

```python
from langchain_core.tools import tool
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

@tool
def check_authorized_vehicle(condominium_id: str, plate: str) -> dict:
    """Check if vehicle is authorized in the condominium.

    Args:
        condominium_id: UUID of the condominium
        plate: License plate number (e.g., ABC-123)

    Returns:
        dict with vehicle info or None if not found
    """
    result = supabase.table("vehicles").select(
        "*, residents!inner(name, phone, unit_number)"
    ).eq("condominium_id", condominium_id).eq("plate_number", plate).eq("is_active", True).execute()

    if result.data:
        return result.data[0]
    return None

@tool
def check_pre_authorized_visitor(condominium_id: str, cedula: str) -> dict:
    """Check if visitor is pre-authorized.

    Args:
        condominium_id: UUID of the condominium
        cedula: Costa Rica ID number from OCR

    Returns:
        dict with visitor authorization or None
    """
    result = supabase.table("pre_authorized_visitors").select(
        "*, residents!inner(name, phone, unit_number)"
    ).eq("condominium_id", condominium_id).eq("visitor_cedula", cedula).eq("is_active", True).execute()

    if result.data:
        visitor = result.data[0]
        # Check if still valid (valid_until)
        from datetime import datetime
        if visitor["valid_until"]:
            valid_until = datetime.fromisoformat(visitor["valid_until"])
            if datetime.now() > valid_until:
                return None
        return visitor
    return None

@tool
def notify_resident_whatsapp(resident_phone: str, visitor_name: str, cedula_photo_url: str) -> bool:
    """Send WhatsApp notification to resident with visitor photo.

    Args:
        resident_phone: Resident's phone (+506...)
        visitor_name: Name from conversation
        cedula_photo_url: URL of cedula photo from Supabase Storage

    Returns:
        bool indicating success
    """
    # Integration with Evolution API (WhatsApp)
    import httpx

    response = httpx.post(
        f"{os.getenv('EVOLUTION_API_URL')}/message/sendMedia/sitnova",
        headers={"apikey": os.getenv("EVOLUTION_API_KEY")},
        json={
            "number": resident_phone,
            "mediaMessage": {
                "mediatype": "image",
                "media": cedula_photo_url,
                "caption": f"🔔 Visitante en portón: {visitor_name}\n\n¿Autoriza el ingreso? Responde SÍ o NO"
            }
        }
    )
    return response.status_code == 200

@tool
def open_gate(condominium_id: str, method: str = "api") -> bool:
    """Trigger gate opening mechanism.

    Args:
        condominium_id: UUID of the condominium
        method: "api", "relay", or "sip" based on gate_control_type

    Returns:
        bool indicating success
    """
    # Get gate config for this condominium
    result = supabase.table("condominiums").select("gate_config").eq("id", condominium_id).execute()

    if not result.data:
        return False

    gate_config = result.data[0]["gate_config"]

    if method == "api":
        # HTTP call to gate API
        import httpx
        response = httpx.post(
            gate_config["api_endpoint"],
            headers={"Authorization": f"Bearer {gate_config['api_key']}"},
            json={"action": "open"}
        )
        return response.status_code == 200

    elif method == "relay":
        # GPIO relay control (local)
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(gate_config["gpio_pin"], GPIO.OUT)
        GPIO.output(gate_config["gpio_pin"], GPIO.HIGH)
        import time
        time.sleep(2)  # Keep open 2 seconds
        GPIO.output(gate_config["gpio_pin"], GPIO.LOW)
        return True

    return False

@tool
def log_access_event(
    condominium_id: str,
    event_type: str,
    plate: str | None,
    cedula: str | None,
    resident_id: str | None,
    authorized: bool,
    gate_opened: bool,
    cedula_photo_url: str | None,
    vehicle_photo_url: str | None
) -> dict:
    """Log access event to database.

    Args:
        condominium_id: UUID of the condominium
        event_type: "vehicle_entry", "visitor_entry", "delivery"
        plate: License plate if captured
        cedula: Cedula number if captured
        resident_id: Associated resident UUID if known
        authorized: Whether access was authorized
        gate_opened: Whether gate was actually opened
        cedula_photo_url: URL of cedula photo
        vehicle_photo_url: URL of vehicle/plate photo

    Returns:
        dict with created log entry
    """
    log_data = {
        "condominium_id": condominium_id,
        "event_type": event_type,
        "plate_number": plate,
        "cedula_number": cedula,
        "resident_id": resident_id,
        "authorized": authorized,
        "gate_opened": gate_opened,
        "cedula_photo_url": cedula_photo_url,
        "vehicle_photo_url": vehicle_photo_url,
        "timestamp": "now()"
    }

    result = supabase.table("access_logs").insert(log_data).execute()
    return result.data[0]

@tool
def capture_plate_ocr(camera_ip: str) -> dict:
    """Capture and process license plate via Hikvision camera + OCR.

    Args:
        camera_ip: IP of plate recognition camera

    Returns:
        dict with plate number and confidence
    """
    # Integration with local OCR service (YOLOv8 + EasyOCR)
    import httpx

    response = httpx.post(
        "http://localhost:8001/ocr/plate",
        json={"camera_ip": camera_ip},
        timeout=5.0
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "plate": data["text"],
            "confidence": data["confidence"],
            "image_url": data["image_url"]
        }
    return {"plate": None, "confidence": 0.0}

@tool
def capture_cedula_ocr(camera_ip: str) -> dict:
    """Capture and extract data from Costa Rica cédula (ID card).

    Args:
        camera_ip: IP of document camera

    Returns:
        dict with cedula data (number, name, expiry, photo_url)
    """
    import httpx

    response = httpx.post(
        "http://localhost:8001/ocr/cedula",
        json={"camera_ip": camera_ip},
        timeout=5.0
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "cedula": data["numero"],
            "nombre": data["nombre"],
            "vencimiento": data["vencimiento"],
            "photo_url": data["image_url"],
            "confidence": data["confidence"]
        }
    return {"cedula": None, "confidence": 0.0}
```

**Tool Design Best Practices:**
- Include clear docstrings with Args and Returns
- Return structured dicts (not just primitives) for rich data
- Handle errors gracefully (return None/False instead of raising)
- Use timeout for external API calls (OCR, gate control)
- Log all actions to Supabase for audit trail

### Step 3: Implement Nodes

Nodes are functions that modify state and optionally return messages:

```python
from langchain_core.messages import HumanMessage, AIMessage

def greeting_node(state: OperatorState) -> OperatorState:
    """Initial greeting and vehicle detection"""
    # Trigger plate OCR immediately
    plate_result = capture_plate_ocr(state["camera_plate_ip"])

    state["plate_number"] = plate_result["plate"]
    state["plate_ocr_confidence"] = plate_result["confidence"]

    # Add greeting message
    greeting = "Hola, bienvenido a [Condominio]. ¿En qué puedo ayudarle?"
    state["messages"].append(AIMessage(content=greeting))

    return state

def validate_visitor_node(state: OperatorState) -> OperatorState:
    """Ask visitor to identify themselves"""
    # Trigger cedula capture
    cedula_result = capture_cedula_ocr(state["camera_cedula_ip"])

    state["cedula_number"] = cedula_result["cedula"]
    state["cedula_ocr_data"] = cedula_result

    # Check if pre-authorized
    if cedula_result["cedula"]:
        pre_auth = check_pre_authorized_visitor(
            state["condominium_id"],
            cedula_result["cedula"]
        )

        if pre_auth:
            state["is_authorized"] = True
            state["authorization_method"] = "pre_authorized"
            state["resident_id"] = pre_auth["resident_id"]
            state["resident_name"] = pre_auth["residents"]["name"]

            msg = f"Bienvenido {cedula_result['nombre']}, está pre-autorizado. Abriendo portón..."
            state["messages"].append(AIMessage(content=msg))
        else:
            state["is_authorized"] = False
            msg = "Por favor espere mientras contacto al residente..."
            state["messages"].append(AIMessage(content=msg))

    return state

def notify_resident_node(state: OperatorState) -> OperatorState:
    """Send notification to resident and wait for approval"""
    # Send WhatsApp with cedula photo
    sent = notify_resident_whatsapp(
        state["resident_phone"],
        state["visitor_name"],
        state["cedula_ocr_data"]["photo_url"]
    )

    state["notification_sent"] = sent

    if sent:
        msg = "He notificado al residente. Por favor espere su autorización..."
        state["messages"].append(AIMessage(content=msg))
    else:
        msg = "No pude contactar al residente. Por política del condominio, debo negar el acceso."
        state["is_authorized"] = False
        state["authorization_method"] = "denied"
        state["messages"].append(AIMessage(content=msg))

    return state

def open_gate_node(state: OperatorState) -> OperatorState:
    """Open the gate"""
    success = open_gate(state["condominium_id"])

    state["gate_opened"] = success

    if success:
        msg = "Portón abierto. ¡Que tenga buen día!"
        state["messages"].append(AIMessage(content=msg))
    else:
        msg = "Disculpe, hubo un error con el portón. Por favor contacte a seguridad."
        state["messages"].append(AIMessage(content=msg))

    return state

def log_access_node(state: OperatorState) -> OperatorState:
    """Log the access event"""
    event_type = "vehicle_entry" if state["plate_number"] else "visitor_entry"

    log_entry = log_access_event(
        condominium_id=state["condominium_id"],
        event_type=event_type,
        plate=state["plate_number"],
        cedula=state["cedula_number"],
        resident_id=state["resident_id"],
        authorized=state["is_authorized"],
        gate_opened=state["gate_opened"],
        cedula_photo_url=state["cedula_ocr_data"].get("photo_url") if state["cedula_ocr_data"] else None,
        vehicle_photo_url=state.get("vehicle_photo_url")
    )

    state["access_logged"] = True
    return state
```

### Step 4: Assemble the Graph

Create the StateGraph and add nodes/edges:

```python
from langgraph.graph import StateGraph, END

# Create graph
workflow = StateGraph(OperatorState)

# Add nodes
workflow.add_node("greeting", greeting_node)
workflow.add_node("validate_visitor", validate_visitor_node)
workflow.add_node("notify_resident", notify_resident_node)
workflow.add_node("open_gate", open_gate_node)
workflow.add_node("log_access", log_access_node)

# Set entry point
workflow.set_entry_point("greeting")

# Add conditional edges
workflow.add_conditional_edges(
    "greeting",
    route_after_vehicle_check,
    {
        "auto_authorize": "open_gate",
        "validate_visitor": "validate_visitor"
    }
)

workflow.add_conditional_edges(
    "validate_visitor",
    route_after_visitor_validation,
    {
        "open_gate": "open_gate",
        "notify_resident": "notify_resident"
    }
)

# Add regular edges
workflow.add_edge("notify_resident", "open_gate")  # After approval
workflow.add_edge("open_gate", "log_access")
workflow.add_edge("log_access", END)

# Compile
app = workflow.compile()
```

### Step 5: Execute with Checkpointing

Use checkpointing for state persistence:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Create checkpointer
memory = SqliteSaver.from_conn_string("sitnova_checkpoints.db")

# Compile with checkpointing
app = workflow.compile(checkpointer=memory)

# Execute
config = {"configurable": {"thread_id": call_sid}}

initial_state = {
    "messages": [],
    "condominium_id": "uuid-123",
    "caller_phone": "+50612345678",
    "call_sid": "CA123abc",
    "camera_plate_ip": "192.168.1.100",
    "camera_cedula_ip": "192.168.1.101",
    "is_authorized": False,
    "gate_opened": False,
    "access_logged": False
}

# Run the graph
for output in app.stream(initial_state, config):
    for node_name, node_output in output.items():
        print(f"Node '{node_name}' output:")
        print(node_output)
```

### Step 6: Integrate with Ultravox Webhooks

Connect LangGraph to Ultravox voice AI:

```python
from fastapi import FastAPI, Request
from langgraph.graph import StateGraph
import json

app = FastAPI()

# Compiled LangGraph
sitnova_graph = workflow.compile(checkpointer=memory)

@app.post("/ultravox/webhook")
async def ultravox_webhook(request: Request):
    """Handle Ultravox call events"""
    payload = await request.json()
    event = payload["event"]

    if event == "call.started":
        # Initialize state for new call
        call_sid = payload["callSid"]
        condominium_id = payload["customParams"]["condominium_id"]

        initial_state = {
            "messages": [],
            "condominium_id": condominium_id,
            "call_sid": call_sid,
            "caller_phone": payload["from"],
            "is_authorized": False,
            "gate_opened": False,
            "access_logged": False
        }

        # Start graph execution
        config = {"configurable": {"thread_id": call_sid}}
        result = sitnova_graph.invoke(initial_state, config)

        return {"status": "processing"}

    elif event == "call.transcript":
        # User spoke - update state
        call_sid = payload["callSid"]
        user_message = payload["transcript"]

        # Get current state from checkpoint
        config = {"configurable": {"thread_id": call_sid}}
        state = sitnova_graph.get_state(config)

        # Add user message
        state.values["messages"].append(HumanMessage(content=user_message))

        # Continue execution
        sitnova_graph.update_state(config, state.values)

        return {"status": "updated"}

    elif event == "call.ended":
        # Ensure access was logged
        call_sid = payload["callSid"]
        config = {"configurable": {"thread_id": call_sid}}
        state = sitnova_graph.get_state(config)

        if not state.values["access_logged"]:
            # Force log
            log_access_node(state.values)

        return {"status": "completed"}
```

## Advanced Patterns

### Multi-Tenant State Isolation

Ensure each condominium's state is isolated:

```python
def get_graph_config(condominium_id: str, call_sid: str):
    """Generate config with tenant isolation"""
    return {
        "configurable": {
            "thread_id": f"{condominium_id}:{call_sid}",
            "tenant_id": condominium_id
        }
    }

# Usage
config = get_graph_config("condo-uuid-123", "CA123abc")
result = app.invoke(initial_state, config)
```

### Dynamic Protocol Loading

Load condominium-specific protocols:

```python
def load_protocol_node(state: OperatorState) -> OperatorState:
    """Load protocol configuration for this condominium"""
    result = supabase.table("attention_protocols").select("*").eq(
        "condominium_id", state["condominium_id"]
    ).eq("is_active", True).execute()

    if result.data:
        protocol = result.data[0]
        state["protocol_config"] = {
            "allow_deliveries": protocol["allow_deliveries"],
            "require_resident_approval": protocol["require_resident_approval"],
            "auto_open_for_residents": protocol["auto_open_for_residents"],
            "max_wait_time": protocol["max_wait_time_seconds"]
        }

    return state

# Add to graph
workflow.add_node("load_protocol", load_protocol_node)
workflow.set_entry_point("load_protocol")
workflow.add_edge("load_protocol", "greeting")
```

### Timeout Handling

Handle resident response timeouts:

```python
import asyncio
from datetime import datetime, timedelta

async def wait_for_approval_node(state: OperatorState) -> OperatorState:
    """Wait for resident approval with timeout"""
    max_wait = state["protocol_config"]["max_wait_time"]
    start_time = datetime.now()

    while (datetime.now() - start_time).seconds < max_wait:
        # Check for approval in database
        result = supabase.table("notifications").select("response").eq(
            "call_sid", state["call_sid"]
        ).eq("notification_type", "visitor_approval").execute()

        if result.data and result.data[0]["response"]:
            response = result.data[0]["response"]
            state["is_authorized"] = response == "approved"
            state["authorization_method"] = "resident_approved"
            return state

        await asyncio.sleep(2)  # Poll every 2 seconds

    # Timeout - deny by default
    state["is_authorized"] = False
    state["authorization_method"] = "denied"
    state["messages"].append(AIMessage(
        content="El residente no respondió a tiempo. Por seguridad, debo negar el acceso."
    ))

    return state
```

## Common Pitfalls

### 1. State Mutation Issues

❌ **Wrong:** Mutating state directly
```python
def bad_node(state: OperatorState):
    state["messages"].append(...)  # Mutates original
    return state
```

✅ **Correct:** Return new state object
```python
def good_node(state: OperatorState) -> OperatorState:
    new_messages = state["messages"] + [AIMessage(content="...")]
    return {**state, "messages": new_messages}
```

### 2. Missing Conditional Routes

❌ **Wrong:** Returning string from node
```python
def node(state):
    return "next_node"  # Won't work
```

✅ **Correct:** Use routing function
```python
def route_function(state) -> Literal["next_node", "other_node"]:
    return "next_node"

workflow.add_conditional_edges("current", route_function, {...})
```

### 3. Forgetting to Log Access

Always ensure access events are logged, even on errors:

```python
# Add error handling node
def error_handler_node(state: OperatorState) -> OperatorState:
    """Log access even on error"""
    if not state["access_logged"]:
        log_access_event(...)
        state["access_logged"] = True
    return state

# Add to all terminal paths
workflow.add_edge("open_gate", "log_access")
workflow.add_edge("polite_denial", "log_access")
workflow.add_edge("error_handler", "log_access")
```

### 4. Blocking OCR Calls

❌ **Wrong:** Synchronous OCR blocks execution
```python
def node(state):
    result = capture_plate_ocr()  # Blocks for 500ms
    return state
```

✅ **Better:** Use async with timeout
```python
async def node(state):
    try:
        result = await asyncio.wait_for(
            capture_plate_ocr_async(),
            timeout=1.0
        )
    except asyncio.TimeoutError:
        result = {"plate": None, "confidence": 0.0}
    return state
```

## Debugging

### Visualize Graph

```python
from IPython.display import Image, display

display(Image(app.get_graph().draw_mermaid_png()))
```

### Inspect State at Each Step

```python
for step in app.stream(initial_state, config):
    print(f"Step: {step}")
    print(f"State: {json.dumps(step, indent=2)}")
```

### View Checkpoint History

```python
# Get all checkpoints for a thread
config = {"configurable": {"thread_id": "CA123abc"}}
checkpoints = memory.list(config)

for checkpoint in checkpoints:
    print(f"Checkpoint ID: {checkpoint.id}")
    print(f"State: {checkpoint.state}")
```

## Performance Optimization

### Latency Targets

SITNOVA requires low latency for gate control:
- **Plate OCR:** < 500ms
- **Cedula OCR:** < 1000ms
- **Gate opening:** < 200ms
- **Total flow (known vehicle):** < 1.5s

**Optimization strategies:**
1. Run OCR locally (not cloud API)
2. Parallel tool execution where possible
3. Cache protocol configurations
4. Use connection pooling for Supabase
5. Optimize image resolution for OCR (640x480 sufficient)

### Parallel Tool Execution

```python
import asyncio

async def parallel_capture_node(state: OperatorState) -> OperatorState:
    """Capture plate and cedula in parallel"""
    plate_task = capture_plate_ocr_async(state["camera_plate_ip"])
    cedula_task = capture_cedula_ocr_async(state["camera_cedula_ip"])

    plate_result, cedula_result = await asyncio.gather(
        plate_task, cedula_task
    )

    state["plate_number"] = plate_result["plate"]
    state["cedula_number"] = cedula_result["cedula"]

    return state
```

## Reference Files

- See [references/langgraph-docs.md](references/langgraph-docs.md) for complete LangGraph documentation
- See [references/sitnova-flows.md](references/sitnova-flows.md) for all scenario flow diagrams
- See [scripts/test_graph.py](scripts/test_graph.py) for executable test suite
- See [examples/ultravox_integration.py](examples/ultravox_integration.py) for complete webhook handler

## Examples

### Example 1: Known Vehicle Auto-Authorization

```python
initial_state = {
    "messages": [],
    "condominium_id": "condo-123",
    "call_sid": "CA123",
    "plate_number": "ABC-123",  # Pre-captured
    "plate_ocr_confidence": 0.95,
    "is_authorized": False,
    "gate_opened": False
}

result = app.invoke(initial_state, config)

# Expected flow:
# greeting → route_after_vehicle_check → auto_authorize → open_gate → log_access → END
```

### Example 2: Unknown Visitor Requiring Approval

```python
initial_state = {
    "messages": [],
    "condominium_id": "condo-123",
    "call_sid": "CA456",
    "plate_number": None,
    "cedula_number": "1-2345-6789",  # From OCR
    "visitor_name": "Juan Pérez",
    "resident_id": "resident-789",
    "resident_phone": "+50612345678",
    "is_authorized": False,
    "gate_opened": False
}

result = app.invoke(initial_state, config)

# Expected flow:
# greeting → validate_visitor → notify_resident → wait_approval → open_gate → log_access → END
```

### Example 3: Delivery Person

```python
initial_state = {
    "messages": [],
    "condominium_id": "condo-123",
    "call_sid": "CA789",
    "visitor_name": "Amazon Delivery",
    "visitor_purpose": "delivery",
    "protocol_config": {"allow_deliveries": True},
    "is_authorized": False,
    "gate_opened": False
}

result = app.invoke(initial_state, config)

# Expected flow with delivery protocol:
# greeting → validate_visitor → check_delivery_protocol → open_gate → log_access → END
```

## Integration Checklist

When implementing SITNOVA with LangGraph:

- [ ] Define `OperatorState` TypedDict with all required fields
- [ ] Create tools for: OCR, database queries, notifications, gate control, logging
- [ ] Implement nodes for each major step in the flow
- [ ] Add conditional routing functions for decision points
- [ ] Assemble StateGraph with proper edges
- [ ] Configure checkpointing with SqliteSaver
- [ ] Integrate with Ultravox webhooks (call.started, call.transcript, call.ended)
- [ ] Add error handling and timeout logic
- [ ] Test all three scenarios: known vehicle, unknown visitor, delivery
- [ ] Optimize for latency (< 1.5s for known vehicles)
- [ ] Implement multi-tenant isolation
- [ ] Add comprehensive logging to `access_logs` table
- [ ] Deploy OCR service locally (YOLOv8 + EasyOCR)
- [ ] Configure Hikvision camera integration
- [ ] Set up WhatsApp notifications (Evolution API)

## Resources

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **SITNOVA Project:** See [PROYECTO-SITNOVA.md](../../PROYECTO-SITNOVA.md)
- **Database Schema:** See [database/schema-sitnova.sql](../../database/schema-sitnova.sql)
- **Supabase Setup:** See [database/SUPABASE-SETUP.md](../../database/SUPABASE-SETUP.md)
- **Ultravox Integration:** https://ultravox.ai/docs
- **YOLOv8 + EasyOCR:** See backend OCR service implementation

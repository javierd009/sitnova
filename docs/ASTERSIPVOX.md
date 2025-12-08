# AsterSIPVox - Documentación de Integración

> **IMPORTANTE**: Este archivo documenta una pieza crítica del stack de SITNOVA.
> AsterSIPVox es la plataforma que conecta la IA de voz (Ultravox) con el sistema telefónico (PBX).

## ¿Qué es AsterSIPVox?

AsterSIPVox es una plataforma que permite crear asistentes virtuales con IA que se integran con sistemas PBX basados en SIP (Asterisk, FreeSWITCH, etc.). Funciona como un bridge entre:

- **Ultravox AI** - Motor de voz con IA
- **FreePBX/Asterisk** - Central telefónica
- **APIs externas** - Para herramientas personalizadas

El asistente virtual se registra como una extensión más del PBX, permitiendo:
- Recibir llamadas entrantes
- Realizar llamadas salientes
- Transferir llamadas
- Ejecutar herramientas (tools) durante la conversación

## Arquitectura en SITNOVA

```
┌─────────────────────────────────────────────────────────────────┐
│                    STACK COMPLETO SITNOVA                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   VERCEL    │    │   DOCKER    │    │  SUPABASE   │        │
│   │  (Frontend) │    │ (Portainer) │    │ (Database)  │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                              │                                  │
│                              ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    ASTERSIPVOX                          │  │
│   │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │  │
│   │  │  Ultravox   │◄──►│   Bridge    │◄──►│   FreePBX   │  │  │
│   │  │  Voice AI   │    │   (SIP)     │    │  (Asterisk) │  │  │
│   │  └─────────────┘    └─────────────┘    └─────────────┘  │  │
│   │         │                                                │  │
│   │         ▼                                                │  │
│   │  ┌─────────────────────────────────────────────────┐    │  │
│   │  │              TOOLS (HTTP APIs)                  │    │  │
│   │  │  - buscar_residente    - abrir_porton          │    │  │
│   │  │  - notificar_residente - estado_autorizacion   │    │  │
│   │  │  - transferir_operador - colgar_llamada        │    │  │
│   │  └─────────────────────────────────────────────────┘    │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Configuración de Extensiones

### Parámetros de Conexión PBX

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `Username` | Extensión o usuario SIP | `205` |
| `Password` | Contraseña de la extensión | `****` |
| `Host` | IP o dominio del PBX | `192.168.1.50` |
| `Enabled` | Activa/desactiva registro | `true` |

### Configuración de IA

| Parámetro | Descripción | Valor Recomendado |
|-----------|-------------|-------------------|
| `Language Hint` | Idioma inicial | `es-CR` (Español Costa Rica) |
| `Voice Selection` | Voz del asistente | Según preferencia |
| `Recording Enabled` | Grabar llamadas | `true` (para debug) |
| `User Speak First` | Quién habla primero | `false` (entrantes), `true` (salientes) |
| `Maximum Duration` | Duración máxima (seg) | `300` (5 minutos) |
| `Temperature` | Creatividad (0-1) | `0.7` |

### Mensajes Configurables

| Mensaje | Uso | Ejemplo |
|---------|-----|---------|
| `Greeting` | Saludo inicial | "Buenas, ¿a quién visita?" |
| `Inactivity` | Después de 5s silencio | "¿Sigue ahí?" |
| `Disconnection` | Antes de colgar por inactividad | "Hasta luego" |
| `Time Exceeded` | Al alcanzar duración máxima | "Se acabó el tiempo" |

### Audio Settings

| Parámetro | Descripción | Valor |
|-----------|-------------|-------|
| `Background Noise` | Ruido ambiente | `None` o `office` |
| `Background Noise Volume` | Volumen (0.01-1.0) | `0.05` |
| `Echo Cancellation (AEC)` | Cancelar eco | `true` si hay eco |
| `AEC Delay` | Delay en samples | `160` (default) |
| `AEC Step Size` | Velocidad adaptación | `0.05` |

## API Reference

### Base URL
```
http://localhost:7070
```

### Autenticación
Todas las requests requieren Bearer token:
```
Authorization: Bearer <your-api-key>
```

### Endpoints

#### 1. Originar Llamada

```http
POST /call
Content-Type: application/json
Authorization: Bearer <api-key>

{
  "username": "205",
  "destination": "203",
  "api_text_to_inject": "Contexto adicional para la IA..."
}
```

**Respuesta:**
```json
{
  "destination": "sip:203@192.168.10.24",
  "from_user": "205",
  "status": "Call initiation accepted"
}
```

#### 2. Almacenar Datos (Key/Value Store)

```http
POST /store/{key}
Content-Type: application/json
Authorization: Bearer <api-key>

{"documento": "74739322", "nombre": "Juan Pérez"}
```

**Respuesta:**
```json
{
  "status": "stored"
}
```

> **NOTA**: Los datos expiran después de 5 minutos.

#### 3. Recuperar Datos (con metadata)

```http
GET /store/{key}
Authorization: Bearer <api-key>
```

**Respuesta:**
```json
{
  "expires_at": "2025-04-13T10:37:33.13762707Z",
  "key": "577554",
  "value": "{\"documento\":\"74739322\"}"
}
```

#### 4. Recuperar Solo Valor

```http
GET /store/{key}/value
Authorization: Bearer <api-key>
```

**Respuesta:**
```json
{"documento": "74739322"}
```

## Tools Built-in de AsterSIPVox

Estas herramientas están integradas en AsterSIPVox y se pueden usar desde el System Prompt:

### 1. transfer_call
Transfiere la llamada a otra extensión o número.

```
Si el usuario pide hablar con un operador, usa la herramienta `transfer_call`
con destination "1002".
```

### 2. play_dtmf
Reproduce tonos DTMF durante la llamada.

```
Para navegar un menú IVR, usa `play_dtmf` con los dígitos necesarios.
```

### 3. hangUp
Termina la llamada.

```
Cuando la conversación concluya, usa la herramienta `hangUp` para colgar.
```

## Configuración de Tools Personalizadas

En AsterSIPVox se pueden crear tools que llaman a APIs HTTP externas. Para SITNOVA:

### Estructura de Tool

```json
{
  "name": "buscar_residente",
  "description": "Busca un residente por nombre o número de casa",
  "http": {
    "baseUrl": "https://api.sitnova.com/tools/buscar-residente",
    "method": "POST"
  },
  "authentication": {
    "type": "Header",
    "headerName": "X-API-Key",
    "value": "<api-key>"
  },
  "parameters": [
    {
      "name": "query",
      "location": "Body",
      "schema": {
        "type": "string",
        "description": "Nombre del residente o número de casa"
      }
    },
    {
      "name": "condominium_id",
      "location": "Body",
      "schema": {
        "type": "string",
        "description": "ID del condominio"
      }
    }
  ]
}
```

### Tools de SITNOVA para AsterSIPVox

| Tool | Endpoint | Descripción |
|------|----------|-------------|
| `buscar_residente` | `/tools/buscar-residente` | Busca residente por nombre o casa |
| `notificar_residente` | `/tools/notificar-residente` | Envía WhatsApp al residente |
| `estado_autorizacion` | `/tools/estado-autorizacion` | Verifica si el residente respondió |
| `abrir_porton` | `/tools/abrir-porton` | Abre el portón de acceso |
| `transferir_operador` | `/tools/transferir-operador` | Transfiere a operador humano |
| `colgar_llamada` | `/tools/colgar-llamada` | Termina la llamada |

## Dynamic Context API (Opcional)

AsterSIPVox puede obtener contexto dinámico antes de conectar la llamada:

```
URL: https://api.sitnova.com/context?callerid={callerid}&callid={callid}
Method: GET
Authentication: Header (X-API-Key)
Injection: Append to System Prompt
```

Esto permite inyectar información del visitante (placa detectada, etc.) antes de que inicie la conversación.

## System Prompt para SITNOVA

El System Prompt se configura directamente en AsterSIPVox. Ver archivo:
- `src/services/voice/prompts.py` - Prompt maestro

### Estructura del Prompt

```
1. ROL: Definir quién es el asistente
2. REGLAS CRÍTICAS: Anti-silencio, no repetir preguntas
3. FLUJO DE CONVERSACIÓN: Pasos ordenados
4. USO DE TOOLS: Cuándo usar cada herramienta
5. CONTROL DE LLAMADA: Cuándo colgar o transferir
6. LÍMITES DE SEGURIDAD: Qué no debe hacer
```

## Variables de Entorno Relacionadas

```bash
# AsterSIPVox
ASTERSIPVOX_URL=http://localhost:7070
ASTERSIPVOX_API_KEY=your-api-key
ASTERSIPVOX_EXTENSION=205

# Ultravox (usado por AsterSIPVox)
ULTRAVOX_API_KEY=your-ultravox-key
ULTRAVOX_VOICE=es-CR-SofiaNeural

# FreePBX
FREEPBX_HOST=192.168.1.50
FREEPBX_AMI_PORT=5038
FREEPBX_AMI_USER=portero
FREEPBX_AMI_SECRET=your-secret

# Operador (para transferencias)
OPERATOR_EXTENSION=1002
OPERATOR_PHONE=+50688015665
OPERATOR_TIMEOUT=120
```

## Flujo de una Llamada Entrante

```
1. Visitante llama → FreePBX recibe
2. FreePBX rutea a extensión 205 → AsterSIPVox
3. AsterSIPVox conecta con Ultravox
4. (Opcional) Context API obtiene datos previos
5. Ultravox inicia conversación con System Prompt
6. Durante conversación:
   - IA usa tools (buscar_residente, etc.)
   - Tools llaman a API de SITNOVA
   - API devuelve resultados
   - IA continúa conversación
7. Al finalizar:
   - Si autorizado: abrir_porton + hangUp
   - Si denegado: hangUp
   - Si timeout: transfer_call a operador
```

## Flujo de una Llamada Saliente (Originate)

```
1. Sistema detecta evento → Llama API /call
2. AsterSIPVox origina llamada desde ext 205
3. Residente contesta
4. Ultravox maneja conversación con prompt inyectado
5. Según respuesta del residente:
   - Autoriza: tool autorizar_acceso
   - Deniega: tool denegar_acceso
6. hangUp al terminar
```

## Mejores Prácticas

### Prompts
- Ser específico y claro en las instrucciones
- Incluir ejemplos de uso de cada tool
- Definir fallbacks para situaciones no esperadas
- Evitar instrucciones contradictorias

### Tools
- Respuestas rápidas (< 3 segundos)
- Siempre retornar un campo `result` con mensaje para la IA
- Incluir manejo de errores
- Logging detallado para debugging

### Audio
- Empezar con AEC desactivado, activar si hay eco
- Probar diferentes valores de delay según el ambiente
- Background noise bajo (0.05) o desactivado

### Testing
- Probar cada tool individualmente
- Simular diferentes escenarios de usuario
- Revisar recordings en portal Ultravox
- Monitorear logs: `journalctl -u astersipvox -f`

## Troubleshooting

| Problema | Causa Probable | Solución |
|----------|----------------|----------|
| No registra | Credenciales incorrectas | Verificar username/password en PBX |
| No contesta | Extension deshabilitada | Verificar `Enabled: true` |
| No usa tools | Prompt incompleto | Revisar instrucciones de tools |
| Eco en llamada | AEC mal configurado | Ajustar AEC Delay |
| Timeout en tools | API lenta | Optimizar respuesta de API |
| No transfiere | Tool mal configurado | Verificar parámetros de transfer_call |

## Archivos Relacionados en SITNOVA

```
src/services/voice/
├── astersipvox_client.py    # Cliente API de AsterSIPVox
├── ultravox_client.py       # Cliente directo de Ultravox
├── prompts.py               # System Prompt centralizado
└── webhook_handler.py       # Handler de eventos

src/api/routes/
├── tools.py                 # Endpoints para tools de AsterSIPVox
├── voice.py                 # Endpoints de voz
└── webhooks.py              # Webhooks de Ultravox/Evolution

src/agent/
├── tools.py                 # Tools de LangGraph (incluye hangup, transfer)
├── nodes.py                 # Nodos del grafo
└── graph.py                 # Grafo de estados
```

## Referencias

- **AsterSIPVox Portal**: https://app.astersipvox.asternic.net
- **Ultravox Portal**: https://ultravox.ai
- **Documentación Ultravox**: https://docs.ultravox.ai

---

> **RECORDATORIO**: Las tools, el System Prompt, y la configuración de audio se hacen
> directamente en el portal de AsterSIPVox. El código en SITNOVA proporciona los
> endpoints HTTP que AsterSIPVox llama como tools.

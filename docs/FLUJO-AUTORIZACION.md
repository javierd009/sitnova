# Flujo de Autorización - Guía de Pruebas

Este documento explica el flujo completo de autorización de visitantes y cómo probarlo.

## Últimas Actualizaciones (2025-12-03)

### Nuevas Funcionalidades
- **System Prompt Profesional**: Prompts centralizados en `src/services/voice/prompts.py`
- **Mensajes WhatsApp Enriquecidos**: Incluye nombre, cédula, motivo de visita, placa
- **Mensajes de Espera Contextuales**: Mensajes según tiempo transcurrido (< 15s, 15-30s, 30-60s, > 120s)
- **Búsqueda Mejorada**: Sistema solicita apellido si falta información
- **Direcciones**: Instrucciones de llegada incluidas al autorizar acceso
- **Human in the Loop**: Transferencia a operador cuando el sistema no puede resolver

## Diagrama del Flujo

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Visitante  │     │   SITNOVA   │     │  Evolution  │     │  Residente  │
│   (Agente)  │     │    API      │     │    API      │     │  (WhatsApp) │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │                   │
       │ 1. Llega visita   │                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
       │ 2. notificar-     │ 3. send_text()   │ 4. WhatsApp msg   │
       │    residente      │──────────────────>│──────────────────>│
       │                   │                   │                   │
       │                   │   [Guarda auth    │                   │
       │                   │    pendiente en   │                   │
       │                   │    Supabase]      │                   │
       │                   │                   │                   │
       │                   │                   │ 5. Responde "SI"  │
       │                   │                   │<──────────────────│
       │                   │ 6. Webhook        │                   │
       │                   │<──────────────────│                   │
       │                   │                   │                   │
       │                   │   [Actualiza      │                   │
       │                   │    status a       │                   │
       │                   │    "autorizado"]  │                   │
       │                   │                   │                   │
       │ 7. estado-        │                   │                   │
       │    autorizacion   │                   │                   │
       │<──────────────────│                   │                   │
       │                   │                   │                   │
       │ 8. Abre portón    │                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
```

## Componentes Clave

### 1. Tabla `pending_authorizations` (Supabase)
- Almacena autorizaciones pendientes
- Persiste entre reinicios del contenedor
- Expira después de 30 minutos

### 2. Endpoints principales
| Endpoint | Función | Nuevas Características |
|----------|---------|------------------------|
| `POST /tools/notificar-residente` | Envía WhatsApp y guarda auth pendiente | Incluye motivo de visita en mensaje |
| `POST /webhooks/evolution/whatsapp` | Recibe respuesta del residente | Sin cambios |
| `GET /tools/estado-autorizacion` | Consulta estado de la autorización | Mensajes contextuales según tiempo |
| `POST /tools/buscar-residente` | Busca residente por nombre/casa | Pide apellido si falta info |
| `POST /tools/transferir-operador` | Transfiere a operador humano | NUEVO endpoint |

## Pruebas con CURL

### URL Base
```bash
# Desarrollo local
BASE_URL="http://localhost:8000"

# Producción (cambiar por tu URL)
BASE_URL="https://tu-api.com"
```

### Paso 1: Verificar salud del sistema
```bash
curl -s "$BASE_URL/health" | jq
```

### Paso 2: Diagnóstico completo
```bash
curl -s "$BASE_URL/webhooks/evolution/diagnostico-completo" | jq
```

**Respuesta esperada:**
```json
{
  "timestamp": "2024-12-02T...",
  "componentes": {
    "supabase": {"status": "ok", "total_registros": 0}
  },
  "autorizaciones": {
    "total": 0,
    "pendientes": 0
  }
}
```

### Paso 3: Notificar a un residente (con datos completos)
```bash
curl -X POST "$BASE_URL/tools/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "Casa 10",
    "nombre_visitante": "Juan Pérez",
    "cedula": "123456789",
    "placa": "ABC123",
    "motivo_visita": "Entrega de paquete"
  }' | jq
```

**Respuesta esperada:**
```json
{
  "enviado": true,
  "mensaje": "Notificación enviada a [Nombre] (Casa 10). Por favor espere la autorización.",
  "metodo": "whatsapp",
  "result": "He enviado una notificación por WhatsApp..."
}
```

**Mensaje WhatsApp enviado al residente:**
```
🚪 *Visita en portería*

Hay una persona esperando en la entrada:
👤 *Nombre:* Juan Pérez
🪪 *Cédula:* 123456789
📝 *Motivo:* Entrega de paquete
🏠 *Destino:* Casa 10
🚗 *Placa:* ABC123

Responda *SI* para autorizar o *NO* para denegar.
También puede enviar un mensaje para el visitante.
```

### Paso 4: Verificar autorización creada
```bash
curl -s "$BASE_URL/webhooks/evolution/autorizaciones" | jq
```

**Respuesta esperada:**
```json
{
  "total": 1,
  "autorizaciones": {
    "50684817227": {
      "apartment": "Casa 10",
      "visitor_name": "Juan Pérez",
      "status": "pendiente"
    }
  }
}
```

### Paso 5a: Simular respuesta del residente (SIN WhatsApp real)
```bash
# Autorizar
curl -X POST "$BASE_URL/webhooks/evolution/simular-respuesta?phone=50684817227&respuesta=si" | jq

# Denegar
curl -X POST "$BASE_URL/webhooks/evolution/simular-respuesta?phone=50684817227&respuesta=no" | jq

# Mensaje personalizado
curl -X POST "$BASE_URL/webhooks/evolution/simular-respuesta?phone=50684817227&respuesta=Que%20espere%205%20minutos" | jq
```

### Paso 5b: Simular webhook de Evolution API (como si llegara de WhatsApp)
```bash
curl -X POST "$BASE_URL/webhooks/evolution/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "messages.upsert",
    "instance": "sitnova",
    "data": {
      "key": {
        "remoteJid": "50684817227@s.whatsapp.net",
        "fromMe": false
      },
      "message": {
        "conversation": "si"
      }
    }
  }' | jq
```

### Paso 6: Consultar estado de autorización (con mensajes contextuales)
```bash
curl -X POST "$BASE_URL/tools/estado-autorizacion" \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq
```

**Respuesta si fue autorizado (CON DIRECCIONES):**
```json
{
  "apartamento": "Casa 10",
  "estado": "autorizado",
  "mensaje": "El residente ha AUTORIZADO el acceso...",
  "direccion": "Segunda casa después de la piscina, lado derecho",
  "result": "Excelente noticias. El residente de Casa 10 ha autorizado el ingreso. Para llegar: Segunda casa después de la piscina, lado derecho"
}
```

**Respuesta si está pendiente (< 15 segundos):**
```json
{
  "apartamento": "Casa 10",
  "estado": "pendiente",
  "mensaje": "Estoy contactando al residente, un momento por favor.",
  "result": "Estoy contactando al residente, un momento por favor."
}
```

**Respuesta si está pendiente (15-30 segundos):**
```json
{
  "apartamento": "Casa 10",
  "estado": "pendiente",
  "mensaje": "El residente está revisando la solicitud.",
  "result": "El residente está revisando la solicitud."
}
```

**Respuesta si está pendiente (> 120 segundos):**
```json
{
  "apartamento": "Casa 10",
  "estado": "timeout",
  "mensaje": "No hemos podido contactar al residente después de 2 minutos...",
  "result": "No hemos podido contactar al residente. ¿Desea dejar un mensaje o intentar más tarde?"
}
```

### Paso 7: Ver webhooks recibidos (debugging)
```bash
curl -s "$BASE_URL/webhooks/evolution/webhook-log" | jq
```

## Problemas Comunes

### 1. "No hay autorización pendiente"
**Causa:** El teléfono del residente no coincide con el que envía el webhook.

**Verificar:**
```bash
# Ver qué teléfonos están guardados
curl -s "$BASE_URL/webhooks/evolution/diagnostico-completo" | jq '.phones_registrados'
```

**Solución:** Asegurar que el teléfono en la tabla `residents` tenga el formato correcto (ej: `50684817227` sin `+`).

### 2. "Status sigue en pendiente"
**Causa:** El webhook no está llegando o no se procesa.

**Verificar:**
```bash
# Ver si llegaron webhooks
curl -s "$BASE_URL/webhooks/evolution/webhook-log" | jq '.webhooks[-1]'
```

**Solución:**
1. Verificar configuración del webhook en Evolution API
2. URL debe ser: `https://tu-api.com/webhooks/evolution/whatsapp`
3. Evento debe ser: `MESSAGES_UPSERT` o `messages.upsert`

### 3. "Supabase no disponible"
**Causa:** Credenciales de Supabase incorrectas o tabla no existe.

**Verificar:**
```bash
curl -s "$BASE_URL/webhooks/evolution/diagnostico-completo" | jq '.componentes.supabase'
```

**Solución:**
1. Verificar `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` en `.env`
2. Ejecutar migración: `database/migrations/002_pending_authorizations.sql`

## Configuración de Evolution API

### Webhook URL
```
https://tu-api.com/webhooks/evolution/whatsapp
```

### Eventos a suscribir
- `MESSAGES_UPSERT` (recomendado)
- O `messages.upsert`

### Headers requeridos
Ninguno especial, pero Evolution API envía:
- `Content-Type: application/json`

## Formato del teléfono

| Formato guardado | Formato webhook | ¿Match? |
|-----------------|-----------------|---------|
| `50684817227` | `50684817227` | ✅ |
| `+50684817227` | `50684817227` | ✅ (normalizado) |
| `84817227` | `50684817227` | ❌ (falta código país) |

**Recomendación:** Guardar teléfonos en formato `50684817227` (sin `+`, con código de país).

## Formatos de Webhook de Evolution API

El sistema maneja automáticamente diferentes formatos de webhook según el dispositivo:

### 1. Normal (WhatsApp Web/iOS)
```json
{
  "remoteJid": "50683208070@s.whatsapp.net",
  "addressingMode": "pn"
}
```

### 2. LID - Linked ID (Android)
```json
{
  "remoteJid": "34935331135698@lid",
  "remoteJidAlt": "50683208070@s.whatsapp.net",
  "addressingMode": "lid"
}
```
**Nota:** El número real está en `remoteJidAlt`, no en `remoteJid`.

### 3. Legacy
```json
{
  "remoteJid": "50683208070@c.us"
}
```

### 4. Grupos (ignorados automáticamente)
```json
{
  "remoteJid": "50688015665-1571969073@g.us",
  "participant": "50683208070@s.whatsapp.net"
}
```

### Extracción de teléfono

La función `extraer_telefono_de_webhook()` maneja todos estos casos:
1. Detecta el tipo de formato (@s.whatsapp.net, @lid, @c.us, @g.us)
2. Extrae el número del campo correcto (remoteJid o remoteJidAlt)
3. Valida que sea numérico y tenga al menos 8 dígitos
4. Incluye fallback para formatos desconocidos

## Logs útiles

En los logs del contenedor verás:

```
📨 RAW WEBHOOK BODY: {...}
💬 WhatsApp webhook received!
   Event: messages.upsert
   📱 RemoteJID: 50684817227@s.whatsapp.net
   📤 FromMe: False
   💬 Text: si
📞 Número extraído: 50684817227
🔍 Búsqueda de autorización: key=50684817227, auth={...}
✅ ACCESO AUTORIZADO por 50684817227 para Casa 10
```

## Reiniciar el flujo

Si necesitas limpiar y probar de nuevo:

```bash
# Limpiar log de webhooks
curl -X DELETE "$BASE_URL/webhooks/evolution/webhook-log"

# Limpiar autorizaciones viejas (automático cada 30 min)
# O manualmente en Supabase:
# DELETE FROM pending_authorizations WHERE created_at < NOW() - INTERVAL '1 hour';
```

---

## Nuevas Funcionalidades Detalladas

### 1. System Prompt Profesional

**Archivo**: `/Users/mac/Documents/mis-proyectos/sitnova/src/services/voice/prompts.py`

El system prompt define:
- Personalidad del agente (profesional, amable, español costarricense)
- Información a recopilar: nombre completo, cédula, casa, motivo
- Flujo de conversación paso a paso
- Manejo de tiempos de espera (NO pregunta "¿sigues ahí?")
- Reglas estrictas de seguridad (NUNCA leer código, dar info personal)

**Ventajas**:
- Centralizado: Un solo lugar para modificar todos los prompts
- Consistente: Mismo comportamiento en Ultravox y AsterSIPVox
- Mantenible: Fácil de actualizar sin tocar múltiples archivos

### 2. Mensajes WhatsApp Enriquecidos

**Antes**:
```
Visita en portería
Nombre: Juan Pérez
```

**Ahora**:
```
🚪 *Visita en portería*

👤 *Nombre:* Juan Pérez
🪪 *Cédula:* 123456789
📝 *Motivo:* Entrega de paquete
🏠 *Destino:* Casa 10
🚗 *Placa:* ABC123
```

**Beneficio**: El residente tiene toda la información para tomar una decisión informada.

### 3. Mensajes de Espera Contextuales

El endpoint `/tools/estado-autorizacion` ahora adapta su respuesta según el tiempo transcurrido:

| Tiempo | Mensaje |
|--------|---------|
| < 15s | "Estoy contactando al residente, un momento por favor." |
| 15-30s | "El residente está revisando la solicitud." |
| 30-60s | "Seguimos esperando la respuesta del residente." |
| 60-120s | "Aún esperando respuesta, gracias por su paciencia." |
| > 120s | "No hemos podido contactar al residente. ¿Desea dejar un mensaje?" |

**Beneficio**: El visitante sabe qué está pasando sin preguntas repetitivas molestas.

### 4. Búsqueda por Nombre Mejorada

**Endpoint**: `POST /tools/buscar-residente`

**Escenario 1: Solo nombre**
```json
Request: {"nombre": "Juan"}
Response: {
  "encontrado": false,
  "necesita_mas_info": true,
  "tipo_info_faltante": "apellido",
  "result": "Necesito el apellido para poder buscar a esa persona. ¿Cuál es el apellido?"
}
```

**Escenario 2: Nombre completo sin match**
```json
Request: {"nombre": "Juan", "apellido": "Pérez"}
Response: {
  "encontrado": false,
  "necesita_mas_info": true,
  "tipo_info_faltante": "casa",
  "result": "No encontré a nadie con ese nombre. ¿Sabe el número de casa o apartamento?"
}
```

**Beneficio**: Guía al visitante para proporcionar la información correcta.

### 5. Direcciones e Instrucciones de Llegada

**Migración**: `database/migrations/003_add_address_to_residents.sql`

**Nuevos campos en tabla `residents`**:
- `address`: Dirección física
- `address_instructions`: Instrucciones de llegada

**Ejemplo**:
```sql
UPDATE residents
SET address_instructions = 'Segunda casa después de la piscina, lado derecho'
WHERE apartment = 'Casa 10';
```

**Respuesta cuando es autorizado**:
```json
{
  "estado": "autorizado",
  "direccion": "Segunda casa después de la piscina, lado derecho",
  "result": "El residente ha autorizado su ingreso. Para llegar: Segunda casa después de la piscina, lado derecho"
}
```

**Beneficio**: El visitante no se pierde dentro del condominio.

### 6. Human in the Loop (Transferencia a Operador)

**Endpoint**: `POST /tools/transferir-operador`

**Casos de uso**:
- Visitante no proporciona información necesaria
- Residente no responde después de timeout (120s)
- Situación especial que requiere intervención humana

**Variables de entorno necesarias**:
```bash
OPERATOR_PHONE=50688015665  # Teléfono del operador
OPERATOR_TIMEOUT=120        # Tiempo antes de ofrecer transferir
```

**Request**:
```bash
curl -X POST "$BASE_URL/tools/transferir-operador" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "Visitante no proporciona cédula",
    "nombre_visitante": "Juan Pérez",
    "apartamento": "Casa 10"
  }'
```

**Mensaje enviado al operador**:
```
🚨 *Transferencia de llamada*

Un visitante necesita asistencia:
👤 Visitante: Juan Pérez
🏠 Destino: Casa 10
📝 Motivo: Visitante no proporciona cédula

Por favor atienda la portería.
```

**Beneficio**: Respaldo humano cuando el sistema no puede resolver automáticamente.

---

## Resumen de Archivos Nuevos/Modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `src/services/voice/prompts.py` | NUEVO | Centraliza todos los prompts |
| `src/services/voice/ultravox_client.py` | MODIFICADO | Usa nuevo prompt centralizado |
| `src/services/voice/astersipvox_client.py` | MODIFICADO | Usa nuevo prompt centralizado |
| `src/api/routes/tools.py` | MODIFICADO | Múltiples mejoras en endpoints |
| `database/migrations/003_add_address_to_residents.sql` | NUEVO | Agrega campos de dirección |
| `.env.example` | MODIFICADO | Agrega OPERATOR_PHONE y OPERATOR_TIMEOUT |

---

## Testing de Nuevas Funcionalidades

### Test 1: Mensajes de Espera
```bash
# 1. Notificar residente
curl -X POST "$BASE_URL/tools/notificar-residente" -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10", "nombre_visitante": "Test", "cedula": "123", "motivo_visita": "Test"}'

# 2. Consultar inmediatamente (< 15s)
curl -X POST "$BASE_URL/tools/estado-autorizacion" -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq '.mensaje'
# Esperado: "Estoy contactando al residente..."

# 3. Esperar 20 segundos y consultar de nuevo
sleep 20
curl -X POST "$BASE_URL/tools/estado-autorizacion" -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq '.mensaje'
# Esperado: "El residente está revisando la solicitud."
```

### Test 2: Búsqueda con Apellido Faltante
```bash
curl -X POST "$BASE_URL/tools/buscar-residente" -H "Content-Type: application/json" \
  -d '{"nombre": "Juan"}' | jq
# Esperado: necesita_mas_info = true, tipo_info_faltante = "apellido"
```

### Test 3: Transferencia a Operador
```bash
curl -X POST "$BASE_URL/tools/transferir-operador" -H "Content-Type: application/json" \
  -d '{
    "motivo": "Timeout esperando respuesta",
    "nombre_visitante": "Juan Pérez",
    "apartamento": "Casa 10"
  }' | jq
# Esperado: transferido = true
# Verificar: WhatsApp al OPERATOR_PHONE
```

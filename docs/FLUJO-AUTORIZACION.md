# Flujo de Autorización - Guía de Pruebas

Este documento explica el flujo completo de autorización de visitantes y cómo probarlo.

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
| Endpoint | Función |
|----------|---------|
| `POST /tools/notificar-residente` | Envía WhatsApp y guarda auth pendiente |
| `POST /webhooks/evolution/whatsapp` | Recibe respuesta del residente |
| `GET /tools/estado-autorizacion` | Consulta estado de la autorización |

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

### Paso 3: Notificar a un residente
```bash
curl -X POST "$BASE_URL/tools/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "Casa 10",
    "nombre_visitante": "Juan Pérez",
    "cedula": "123456789",
    "placa": "ABC123"
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

### Paso 6: Consultar estado de autorización
```bash
curl -X POST "$BASE_URL/tools/estado-autorizacion" \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq
```

**Respuesta si fue autorizado:**
```json
{
  "apartamento": "Casa 10",
  "estado": "autorizado",
  "mensaje": "El residente ha AUTORIZADO el acceso...",
  "result": "Excelente noticias. El residente de Casa 10 ha autorizado el ingreso..."
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

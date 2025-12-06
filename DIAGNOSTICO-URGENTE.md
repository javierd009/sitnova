# 🚨 Diagnóstico Urgente - Agente No Espera Respuesta

**Fecha**: 2025-12-06
**Problema Reportado**:
- Agente envía notificación WhatsApp ✅
- Inmediatamente dice "no es posible contactar" ❌
- Intenta transferir a operador pero también falla ❌
- Cuelga la llamada sin esperar respuesta ❌

---

## 🔍 Análisis del Problema

### Flujo Esperado:
```
1. notificar_residente → Envía WhatsApp ✅
2. estado_autorizacion (cada 5s) → Espera respuesta ⏳
3. Residente responde → Webhook actualiza estado ✅
4. estado_autorizacion detecta cambio → Abre portón ✅
```

### Flujo Actual (ROTO):
```
1. notificar_residente → Envía WhatsApp ✅
2. estado_autorizacion → NO ENCUENTRA autorización ❌
3. Dice "no pude contactar" ❌
4. transferir_operador → Falla (sin OPERATOR_PHONE?) ❌
5. Cuelga llamada ❌
```

---

## 🐛 Posibles Causas

### Causa #1: Supabase NO Conectado (MÁS PROBABLE)

**Síntoma**:
- `notificar_residente` envía WhatsApp pero NO guarda autorización en Supabase
- Autorización se guarda solo en MEMORIA
- `estado_autorizacion` busca en Supabase pero no la encuentra

**Verificación**:
```bash
# Ver logs de Docker - buscar estas líneas:
docker logs sitnova-backend --tail 200 | grep -i "supabase\|memoria"

# ❌ MAL: Si ves esto
"Autorizacion guardada en MEMORIA (fallback)"
"Supabase client not available"
"Could not get Supabase client"

# ✅ BIEN: Deberías ver esto
"Autorizacion guardada en Supabase"
"Supabase upsert success"
```

**Solución**:
1. Verificar variables de entorno:
```bash
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

2. Si están vacías, agregar en `.env`:
```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_SERVICE_ROLE_KEY=tu-service-role-key-aqui
```

3. Reiniciar contenedor:
```bash
docker restart sitnova-backend
```

---

### Causa #2: Tabla `pending_authorizations` No Existe

**Síntoma**:
- Logs muestran error de Supabase: "relation 'pending_authorizations' does not exist"

**Verificación**:
```bash
# Ver logs completos
docker logs sitnova-backend --tail 500 | grep -A 3 "pending_authorizations"
```

**Solución**:
Crear tabla en Supabase:

```sql
-- Ejecutar en Supabase SQL Editor
CREATE TABLE IF NOT EXISTS pending_authorizations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone VARCHAR(50) UNIQUE NOT NULL,
    apartment VARCHAR(100),
    visitor_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pendiente',
    mensaje_personalizado TEXT,
    cedula VARCHAR(50),
    placa VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '30 minutes')
);

-- Índices para búsqueda rápida
CREATE INDEX idx_pending_auth_phone ON pending_authorizations(phone);
CREATE INDEX idx_pending_auth_apartment ON pending_authorizations(apartment);
CREATE INDEX idx_pending_auth_status ON pending_authorizations(status);
CREATE INDEX idx_pending_auth_expires ON pending_authorizations(expires_at);

-- Auto-limpieza de expirados (opcional)
CREATE OR REPLACE FUNCTION cleanup_expired_authorizations()
RETURNS void AS $$
BEGIN
    DELETE FROM pending_authorizations
    WHERE expires_at < NOW() AND status = 'pendiente';
END;
$$ LANGUAGE plpgsql;
```

---

### Causa #3: OPERATOR_PHONE No Configurado

**Síntoma**:
- Agente dice "no es posible contactar un operador"

**Verificación**:
```bash
# Ver variable de entorno
docker exec sitnova-backend env | grep OPERATOR_PHONE
```

**Solución**:
Agregar en `.env`:
```env
# Teléfono del operador (formato: 50612345678)
OPERATOR_PHONE=50612345678
OPERATOR_TIMEOUT=120  # Segundos antes de ofrecer transferencia
```

---

### Causa #4: Evolution API No Responde

**Síntoma**:
- WhatsApp se "envía" pero no llega realmente
- Webhook no recibe mensajes de respuesta

**Verificación**:
```bash
# Test directo de Evolution API
curl -X POST https://tu-evolution-url/message/sendText/INSTANCE_NAME \
  -H "apikey: TU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "50612345678",
    "text": "Test desde curl"
  }'
```

**Solución**:
1. Verificar credenciales Evolution API:
```env
EVOLUTION_API_URL=https://tu-evolution.com
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE_NAME=tu-instancia
```

2. Verificar webhook configurado en Evolution:
   - URL: `https://api.sitnova.integratec-ia.com/webhooks/evolution`
   - Events: `message.upsert`

---

### Causa #5: AsterSIPVox No Llama a `estado_autorizacion`

**Síntoma**:
- El agente no consulta el estado después de notificar

**Verificación**:
Ver logs de AsterSIPVox (si tienes acceso) o logs del backend:
```bash
# Buscar llamadas a estado-autorizacion
docker logs sitnova-backend --tail 500 | grep "estado-autorizacion"

# Debería ver llamadas cada 5-10 segundos después de notificar
```

**Solución**:
El system prompt ya tiene las instrucciones correctas. Verificar que se actualizó en AsterSIPVox:
- Ir a AsterSIPVox → Extensions → SITNOVA
- Verificar Step 5: "WAIT WITH UPDATES"
- Debe decir: "First check (5s): Use estado_autorizacion"

---

## 🚀 Plan de Diagnóstico (EJECUTAR AHORA)

### Paso 1: Ver Logs Completos del Backend

```bash
# Comando más importante - ejecutar primero
docker logs sitnova-backend --tail 500 > logs-diagnostico.txt

# Buscar patrones clave
grep -i "supabase\|memoria\|pending_authorization\|evolution\|operator" logs-diagnostico.txt
```

**Qué buscar**:
- ✅ "Autorizacion guardada en Supabase" → Supabase funciona
- ❌ "Autorizacion guardada en MEMORIA" → Supabase NO funciona
- ❌ "Supabase client not available" → Credenciales mal
- ❌ "relation 'pending_authorizations' does not exist" → Tabla falta
- ❌ "No hay operador configurado" → OPERATOR_PHONE falta
- ❌ "Error con Evolution API" → Evolution falla

---

### Paso 2: Test Manual de Endpoints

```bash
# 1. Test notificar_residente
curl -X POST https://api.sitnova.integratec-ia.com/tools/notificar-residente \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "Casa 10",
    "nombre_visitante": "Test Usuario",
    "cedula": "123456789",
    "motivo_visita": "Test diagnostico"
  }'

# Esperar 2 segundos

# 2. Test estado_autorizacion (CRÍTICO)
curl -X POST https://api.sitnova.integratec-ia.com/tools/estado-autorizacion \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}'

# Resultado esperado:
# {"estado": "pendiente", "mensaje": "Esperando respuesta..."}
#
# Resultado MAL (problema):
# {"estado": "no_encontrado", "mensaje": "No hay autorización pendiente"}
```

---

### Paso 3: Verificar Supabase Directamente

```bash
# Si tienes acceso a Supabase dashboard:
# 1. Ir a Table Editor
# 2. Buscar tabla "pending_authorizations"
# 3. Ver si existe
# 4. Ver si hay registros

# Alternativa: Query via API REST de Supabase
curl "https://tu-proyecto.supabase.co/rest/v1/pending_authorizations" \
  -H "apikey: TU_ANON_KEY" \
  -H "Authorization: Bearer TU_SERVICE_KEY"
```

---

### Paso 4: Test Webhook Evolution

```bash
# Simular webhook de WhatsApp
curl -X POST https://api.sitnova.integratec-ia.com/webhooks/evolution \
  -H "Content-Type: application/json" \
  -d '{
    "event": "message.upsert",
    "data": {
      "key": {
        "remoteJid": "50612345678@s.whatsapp.net"
      },
      "message": {
        "conversation": "SI"
      }
    }
  }'
```

---

## 📊 Checklist de Verificación

Ejecuta cada ítem y marca:

### Variables de Entorno
- [ ] `SUPABASE_URL` configurada
- [ ] `SUPABASE_SERVICE_ROLE_KEY` configurada
- [ ] `EVOLUTION_API_URL` configurada
- [ ] `EVOLUTION_API_KEY` configurada
- [ ] `EVOLUTION_INSTANCE_NAME` configurada
- [ ] `OPERATOR_PHONE` configurada

### Supabase
- [ ] Tabla `pending_authorizations` existe
- [ ] Tiene columnas correctas (phone, apartment, status, etc.)
- [ ] Índices creados
- [ ] Conexión funciona (test con curl)

### Evolution API
- [ ] Instancia activa
- [ ] Webhook configurado: `https://api.sitnova.integratec-ia.com/webhooks/evolution`
- [ ] API Key válida
- [ ] Test de envío funciona

### Backend
- [ ] Contenedor corriendo: `docker ps | grep sitnova-backend`
- [ ] Logs no muestran errores críticos
- [ ] Endpoint `/health` responde 200
- [ ] Test manual de endpoints funciona

### AsterSIPVox
- [ ] System prompt actualizado (ver Step 5)
- [ ] Extensión reiniciada después de cambios
- [ ] Logs muestran llamadas a tools

---

## 🎯 Solución Más Probable (80%)

**PROBLEMA**: Supabase NO conectado

**SÍNTOMA**:
```
Logs muestran:
"Autorizacion guardada en MEMORIA (fallback)"
"No hay autorización pendiente para Casa 10"
```

**CAUSA**: Variables `SUPABASE_URL` o `SUPABASE_SERVICE_ROLE_KEY` no configuradas o incorrectas

**SOLUCIÓN RÁPIDA**:

1. **Editar `.env`**:
```bash
nano .env

# Agregar/verificar:
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey...
```

2. **Reiniciar contenedor**:
```bash
docker restart sitnova-backend
```

3. **Verificar logs**:
```bash
docker logs sitnova-backend --tail 50 -f

# Buscar:
# ✅ "Connected to Supabase"
# ✅ "Autorizacion guardada en Supabase"
```

4. **Test nuevamente**:
```bash
# Hacer llamada real al intercomunicador
# Decir: "Vengo a visitar a Deisy Colorado"
# Verificar que ESPERA la respuesta del residente
```

---

## 🔧 Script de Diagnóstico Automático

Crear archivo `diagnostico.sh`:

```bash
#!/bin/bash
echo "========================================="
echo "DIAGNÓSTICO SITNOVA - $(date)"
echo "========================================="

echo ""
echo "1. Variables de entorno:"
echo "   SUPABASE_URL: ${SUPABASE_URL:-❌ NO CONFIGURADA}"
echo "   SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY:0:20}... (${#SUPABASE_SERVICE_ROLE_KEY} chars)"
echo "   EVOLUTION_API_URL: ${EVOLUTION_API_URL:-❌ NO CONFIGURADA}"
echo "   OPERATOR_PHONE: ${OPERATOR_PHONE:-❌ NO CONFIGURADA}"

echo ""
echo "2. Contenedores Docker:"
docker ps | grep sitnova

echo ""
echo "3. Health check:"
curl -s https://api.sitnova.integratec-ia.com/health | jq .

echo ""
echo "4. Últimos 20 logs:"
docker logs sitnova-backend --tail 20

echo ""
echo "5. Test endpoint notificar:"
curl -s -X POST https://api.sitnova.integratec-ia.com/tools/notificar-residente \
  -H "Content-Type: application/json" \
  -d '{"apartamento":"TEST","nombre_visitante":"Diagnostico","cedula":"999","motivo_visita":"Test"}' | jq .

echo ""
echo "6. Test endpoint estado:"
curl -s -X POST https://api.sitnova.integratec-ia.com/tools/estado-autorizacion \
  -H "Content-Type: application/json" \
  -d '{"apartamento":"TEST"}' | jq .

echo ""
echo "========================================="
echo "Diagnóstico completo."
echo "========================================="
```

Ejecutar:
```bash
chmod +x diagnostico.sh
./diagnostico.sh > diagnostico-resultado.txt 2>&1
cat diagnostico-resultado.txt
```

---

## 📞 Próximos Pasos

1. **EJECUTAR** el script de diagnóstico arriba
2. **REVISAR** los logs completos (`docker logs sitnova-backend --tail 500`)
3. **COMPARTIR** el output del diagnóstico
4. **IDENTIFICAR** cuál de las 5 causas es la correcta
5. **APLICAR** la solución correspondiente

---

**URGENTE**: El problema más común es que **Supabase no está conectado**.

**Prueba esto PRIMERO**:
```bash
# Dentro del contenedor
docker exec sitnova-backend env | grep SUPABASE

# Si no ves las variables, agregarlas al .env y reiniciar
```

---

**Creado por**: Claude Code
**Prioridad**: 🚨 CRÍTICA
**Tiempo estimado de fix**: 5-10 minutos (una vez identificada la causa)

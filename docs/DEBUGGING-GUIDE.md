# Guía de Debugging - SITNOVA Voice Agent

## Arquitectura del Flujo de Llamadas

```
Visitante → Fanvil i10 → FreePBX → AsterSIPVox → Ultravox
                                        ↓
                                   HTTP Tools
                                        ↓
                              FastAPI Backend (SITNOVA)
                                        ↓
                              Supabase / Evolution API
```

## Endpoints de Diagnóstico

### 1. Health Check Completo
```bash
curl https://api.sitnova.integratec-ia.com/tools/health | jq
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T...",
  "version": "1.3.0",
  "checks": {
    "supabase": {"status": "ok"},
    "evolution_api": {"status": "ok"},
    "condominium": {"status": "ok", "name": "..."},
    "tools_activity": {"calls_last_5min": 5, "errors": 0},
    "memory": {"status": "ok"}
  }
}
```

### 2. Ver Llamadas Recientes
```bash
# Todas las llamadas (últimas 10)
curl https://api.sitnova.integratec-ia.com/tools/diagnostico | jq

# Filtrar por endpoint
curl "https://api.sitnova.integratec-ia.com/tools/diagnostico?endpoint=/buscar-residente" | jq

# Filtrar por status
curl "https://api.sitnova.integratec-ia.com/tools/diagnostico?status=error" | jq

# Ver más llamadas
curl "https://api.sitnova.integratec-ia.com/tools/diagnostico?limit=50" | jq
```

### 3. Ver Autorizaciones Pendientes
```bash
curl https://api.sitnova.integratec-ia.com/tools/autorizaciones-pendientes | jq
```

### 4. Debug de Parámetros
```bash
# Ver qué parámetros recibe un endpoint
curl -X POST https://api.sitnova.integratec-ia.com/tools/debug-params \
  -H "Content-Type: application/json" \
  -d '{"query": "deisy colorado"}' | jq
```

## Pruebas de Búsqueda de Residentes

### Test: Búsqueda por nombre
```bash
curl -X POST https://api.sitnova.integratec-ia.com/tools/buscar-residente \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "Deisy Colorado"
  }' | jq
```

### Test: Búsqueda con error fonético (STT)
```bash
# "dese colorado" → debería encontrar "Deisy Colorado"
curl -X POST https://api.sitnova.integratec-ia.com/tools/buscar-residente \
  -H "Content-Type: application/json" \
  -d '{"query": "dese colorado"}' | jq
```

### Test: Búsqueda por número de casa
```bash
curl -X POST https://api.sitnova.integratec-ia.com/tools/buscar-residente \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "15"}' | jq
```

## Logs del Backend

### En Docker/Portainer
```bash
# Ver logs en tiempo real
docker logs -f sitnova-backend

# Filtrar por buscar-residente
docker logs sitnova-backend 2>&1 | grep "buscar-residente"

# Ver últimas 100 líneas con timestamps
docker logs --tail 100 -t sitnova-backend
```

### Indicadores en Logs

| Emoji | Significado |
|-------|-------------|
| 📥 | Request entrante |
| 📤 | Response saliente |
| ✅ | Operación exitosa |
| ❌ | Error |
| ⚠️ | Warning |
| 🔍 | Búsqueda en progreso |
| 🔄 | Corrección fonética aplicada |
| 💡 | Sugerencia |

### Ejemplo de Log Exitoso
```
📥 CALL #42 → /buscar-residente
⏰ Timestamp: 2025-12-07T10:30:45
📦 Body: {"query": "dese colorado"}
🔄 Corrección fonética aplicada: 'dese colorado' -> 'dc colorado'
🔍 Buscando residente: nombre=dc colorado
✅ Fuzzy match alto (85%): Deisy Colorado
📤 RESPONSE #42 (45ms) → found_by_name
```

## Correcciones Fonéticas Implementadas

El sistema corrige automáticamente errores comunes de STT:

| Input STT | Corrección | Residente Encontrado |
|-----------|------------|---------------------|
| dese colorado | dc colorado | Deisy Colorado |
| daisy colorado | deisy colorado | Deisy Colorado |
| radriga | rodriguez | Rodríguez |
| gonsales | gonzalez | González |
| ernandez | hernandez | Hernández |

## Flujo de una Búsqueda Típica

```
1. AsterSIPVox envía POST /buscar-residente
   └─ Body: {"query": "dese colorado"}

2. Backend recibe y logea
   └─ log_request() → call_id = 42

3. Aplica correcciones fonéticas
   └─ "dese colorado" → "dc colorado"

4. Busca en Supabase (residents)
   a. Intenta match exacto con variaciones fonéticas
   b. Si no hay match → fuzzy matching (threshold 0.45)
   c. Si no hay fuzzy → sugerencias de apellido

5. Encuentra match (85%)
   └─ "Deisy Colorado" en casa 15

6. Retorna respuesta
   └─ log_response() → status = found_by_name

7. AsterSIPVox/Ultravox usa el resultado
   └─ "Encontré a Deisy Colorado en casa 15..."
```

## Problemas Comunes

### 1. "No encontré ningún residente..."

**Causas:**
- Nombre mal escrito en base de datos
- Corrección fonética no implementada
- Residente inactivo (`is_active = false`)

**Diagnóstico:**
```bash
# Ver residentes en la DB
curl https://api.sitnova.integratec-ia.com/tools/debug-residente/15 | jq

# Ver log de la búsqueda
curl "https://api.sitnova.integratec-ia.com/tools/diagnostico?endpoint=/buscar-residente&limit=5" | jq
```

### 2. "El agente se queda en silencio"

**Causas:**
- Tool timeout (> 5 segundos)
- Error en Supabase
- Respuesta mal formateada

**Diagnóstico:**
```bash
# Ver health status
curl https://api.sitnova.integratec-ia.com/tools/health | jq '.checks.supabase'

# Ver errores recientes
curl "https://api.sitnova.integratec-ia.com/tools/diagnostico?status=error" | jq
```

### 3. "WhatsApp no llega al residente"

**Causas:**
- Evolution API no configurado
- Número de teléfono incorrecto
- Instancia de WhatsApp desconectada

**Diagnóstico:**
```bash
# Ver config de Evolution
curl https://api.sitnova.integratec-ia.com/tools/health | jq '.checks.evolution_api'

# Ver autorización pendiente
curl https://api.sitnova.integratec-ia.com/tools/autorizaciones-pendientes | jq
```

### 4. "El agente repite las mismas preguntas"

**Causas:**
- Prompt no tiene reglas de memoria
- Variables de sesión no se mantienen

**Solución:**
El prompt V13 incluye `<memory_rules>` para evitar esto.

### 5. "La cédula se confirma de forma confusa"

**Causas:**
- Prompt no tiene `<cedula_confirmation>`
- TTS pronuncia números como palabras

**Solución:**
El prompt V13 incluye instrucciones de pronunciación dígito por dígito con pausas.

## Script de Validación

```bash
# Validar configuración de AsterSIPVox
source venv/bin/activate
python scripts/update_astersipvox_config.py --validate
python scripts/update_astersipvox_config.py --show
```

## Actualizar Configuración de AsterSIPVox

1. Editar `docs/astersipvox-config-v13.json`
2. Validar: `python scripts/update_astersipvox_config.py --validate`
3. Copiar JSON: `python scripts/update_astersipvox_config.py --json`
4. Pegar en dashboard de AsterSIPVox → Extensiones → [Extensión] → Edit
5. Guardar y probar llamada de prueba

## Monitoreo Continuo

### Dashboard Recomendado
- **Grafana** para métricas
- **Uptime Kuma** para health checks
- **Portainer** para logs de contenedores

### Alertas Sugeridas
- `status != "healthy"` → Alerta crítica
- `error_count > 5 en 5min` → Alerta de errores
- `avg_duration_ms > 3000` → Alerta de latencia

## Contacto para Soporte

- **Issues**: https://github.com/integratec-ia/sitnova/issues
- **Logs**: Ver en Portainer
- **Config**: Dashboard AsterSIPVox

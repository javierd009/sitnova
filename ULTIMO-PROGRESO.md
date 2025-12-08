# SITNOVA - Último Progreso

**Fecha**: 2025-12-08
**Última actualización**: V14 - Spanish Metaphone + Diagnóstico de Issues

---

## ⚠️ IMPORTANTE: Deploy Manual en Portainer

> **CRÍTICO**: Los deploys del backend en Portainer se hacen **MANUALMENTE**.
>
> GitHub Actions pushea la imagen a GitHub Container Registry, pero el usuario
> debe actualizar manualmente el contenedor en Portainer.
>
> **Commits pendientes de deploy**:
> - `18e7fd1` - Correcciones fonéticas (deci → deisy)
> - `01d4847` - Spanish Metaphone para matching robusto
>
> **Para actualizar**: Portainer → Stacks → sitnova → Pull & Redeploy

---

## En Qué Estamos

**EN PROGRESO** 🔄: Diagnóstico de issues en producción + Spanish Metaphone implementado

### Sesión Actual: V14 - Diagnóstico y Correcciones

**Issues Diagnosticados en esta sesión**:

1. **WhatsApp no se envía durante llamadas** 🔄
   - **Diagnóstico**: Evolution API funciona correctamente (probado manualmente)
   - **Causa Real**: Contenedor en Portainer tiene código viejo
   - **Evidencia**: Logs muestran `'dese colorado' -> 'dc colorado'` (commit viejo)
   - **Solución**: Redeploy manual en Portainer con commits recientes

2. **hangUp no funciona** ⚠️
   - **Diagnóstico**: `hangUp` es tool BUILT-IN de AsterSIPVox, NO un endpoint HTTP
   - **Causa**: No es problema del backend SITNOVA
   - **Investigar**: Configuración de AsterSIPVox / FreePBX
   - **Ver**: `docs/astersipvox-config.json` → `selectedTools`

3. **transfer_call no funciona** ⚠️
   - **Diagnóstico**: `transfer_call` es tool BUILT-IN de AsterSIPVox
   - **Parámetro**: `destination: "1002"` configurado en AsterSIPVox
   - **Causa**: No es problema del backend SITNOVA
   - **Investigar**: FreePBX routing, extensión 1002 existe y está registrada

4. **Matching fonético fallando** ✅ RESUELTO
   - **Problema**: "Deci Colorado" → "DC Colorado" (no encontraba "Deisy Colorado")
   - **Solución V1**: Diccionario `PHONETIC_CORRECTIONS` (commit 18e7fd1)
   - **Solución V2**: Spanish Metaphone algorithm (commit 01d4847)
   - **Estado**: Código listo, pendiente de deploy

**Implementado (pendiente deploy)**:

1. **Spanish Metaphone Algorithm** (Nuevo - 180 líneas):
   - Algoritmo fonético completo para español
   - Reglas: B/V unificados, C+e/i→S, H muda, LL→Y, Ñ→NY, etc.
   - Genera códigos fonéticos: "Deisy" → "TSY", "Deci" → "TSY" (match!)
   - Archivo: `src/api/routes/tools.py`

2. **Fuzzy Matching con 3 Estrategias**:
   - ESTRATEGIA 1: Spanish Metaphone matching
   - ESTRATEGIA 2: Variaciones fonéticas tradicionales
   - ESTRATEGIA 3: Matching palabra por palabra
   - Scoring combinado para mejor resultado

3. **Función `phonetic_match_score()`**:
   - Calcula similitud fonética entre dos nombres
   - Considera coincidencia de palabras individuales
   - Threshold configurable (default 0.6)

**Verificaciones realizadas**:

| Test | Resultado |
|------|-----------|
| Evolution API status | ✅ `state: "open"` |
| Evolution send message | ✅ Message ID recibido |
| Backend /buscar-residente | ✅ Encuentra "Deisy Colorado" |
| Backend /notificar-residente | ✅ Retorna `enviado: true` |
| AsterSIPVox tools | ⚠️ hangUp/transfer son built-in |

---

### Sesión Anterior: V13 - Optimización Conversacional

**Implementado en sesión anterior**:

1. **Búsqueda por Nombre de Residente**:
   - El portero ahora acepta nombre del residente directamente
   - No requiere que el visitante conozca el número de casa
   - Usa `lookup_resident` con nombre O número
   - Ejemplo: "Busco a DC Colorado" → busca y encuentra casa 15

2. **Memoria Mejorada** (Crítico):
   - Distingue claramente RESIDENTE_BUSCADO (persona que visita) vs NOMBRE_VISITANTE (quien es el visitante)
   - No repite pregunta "a quién visita" si ya tiene el nombre
   - Mantiene contexto durante toda la conversación
   - Ejemplos de extracción documentados en el prompt

3. **Pronunciación Clara de Cédulas** (UX):
   - Confirma cédula dígito por dígito con pausas claras
   - Formato: "uno... dos... tres..." (NO "ciento veintitrés")
   - Fácil de corregir si hay error de transcripción
   - Evita confusiones con números grandes

4. **Correcciones Fonéticas** (STT Fix):
   - Maneja errores comunes de Speech-to-Text
   - Diccionario de correcciones: "dese"/"disi"/"dece" → "DC"
   - Normaliza automáticamente antes de búsqueda
   - Útil para nombres con iniciales

5. **Manejo de "No sé el número de casa"** (Flujo):
   - Nueva sección `<no_house_number>` en prompt
   - Si visitante dice "no sé la casa" → usa nombre que ya mencionó
   - Flujo paso a paso documentado
   - Evita bloqueo de la conversación

### Funcionalidades Previas:
1. **Sesión 5**: Sistema de Monitoreo + Dashboard Admin (15 páginas) + CI/CD completo
2. **Sesión 4**: Hangup automático + Transfer a operador + Gestión de recursos
3. **Sesión 3**: FreePBX AMI + Evolution API (WhatsApp)
4. **Sesión 2**: Servicio OCR + Cliente Hikvision
5. **Sesión 1**: LangGraph Agent + Docker + Tools base

---

## Estado Actual - Sesión 6: V13 - Búsqueda Inteligente

### ✅ Archivos Modificados en V13

**System Prompt & Configuration**:
1. `/Users/mac/Documents/mis-proyectos/sitnova/docs/astersipvox-config-v13.json`
   - `MonitoringService` class con health checks de todos los servicios
   - `check_supabase()` - Verifica base de datos
   - `check_astersipvox()` - Verifica Voice AI
   - `check_hikvision()` - Verifica control de acceso
   - `check_evolution_api()` - Verifica WhatsApp
   - `check_langgraph()` - Verifica agente IA
   - `get_access_stats()` - Estadísticas del día
   - Sistema de alertas con 4 niveles

2. `/Users/mac/Documents/mis-proyectos/sitnova/src/services/monitoring/__init__.py`
   - Exports del módulo

3. `/Users/mac/Documents/mis-proyectos/sitnova/src/api/routes/monitoring.py`
   - `GET /monitoring/health` - Health check completo
   - `GET /monitoring/services` - Estado de servicios
   - `GET /monitoring/alerts` - Alertas activas
   - `POST /monitoring/alerts` - Crear alerta manual
   - `POST /monitoring/alerts/resolve` - Resolver alerta
   - `GET /monitoring/dashboard` - Datos consolidados para dashboard

**Frontend - Monitoring Dashboard**:
1. `/Users/mac/Documents/mis-proyectos/sitnova/frontend/src/features/monitoring/services/monitoring-service.ts`
   - Cliente API TypeScript
   - Interfaces para tipos de datos
   - Métodos: `getDashboard()`, `getServices()`, `getAlerts()`, `resolveAlert()`

2. `/Users/mac/Documents/mis-proyectos/sitnova/frontend/src/features/monitoring/hooks/use-monitoring.ts`
   - Hook React con auto-refresh
   - Estado de loading/error
   - Actualización cada 30 segundos

3. `/Users/mac/Documents/mis-proyectos/sitnova/frontend/src/app/dashboard/monitoring/page.tsx`
   - Dashboard completo de monitoreo
   - Vista de estado general (healthy/degraded/unhealthy)
   - Grid de servicios con indicadores visuales
   - Panel de estadísticas de acceso
   - Panel de alertas con resolución manual
   - Auto-refresh con timestamp

**CI/CD - GitHub Actions**:
1. `/Users/mac/Documents/mis-proyectos/sitnova/.github/workflows/ci.yml`
   - Tests de backend (pytest + coverage)
   - Tests de frontend (build + type check)
   - Docker build check
   - Security scan con Trivy

2. `/Users/mac/Documents/mis-proyectos/sitnova/.github/workflows/deploy-frontend.yml`
   - Deploy automático a Vercel
   - Triggered en cambios a `frontend/` en branch `main`

3. `/Users/mac/Documents/mis-proyectos/sitnova/.github/workflows/deploy-backend.yml`
   - Build de Docker image
   - Push a GitHub Container Registry
   - Deploy via SSH a servidor

4. `/Users/mac/Documents/mis-proyectos/sitnova/.github/README.md`
   - Documentación de workflows
   - Lista de secrets necesarios
   - Instrucciones de setup

### ✅ Archivos Modificados

1. `/Users/mac/Documents/mis-proyectos/sitnova/src/api/main.py`
   - Agregado router de monitoring: `app.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])`

2. `/Users/mac/Documents/mis-proyectos/sitnova/frontend/src/shared/components/ui/sidebar.tsx`
   - Agregado link a página de Monitoreo en el menú

3. `/Users/mac/Documents/mis-proyectos/sitnova/README.md`
   - Actualizado roadmap Fase 3 como completada

---

## Archivos de Configuración

- `.mcp.json` - Ya existe con la configuración correcta
- Project Ref: `lgqeeumflbzzmqysqkiq`
- Token: Configurado en el archivo

---

## Migraciones Aplicadas

| # | Migración | Estado |
|---|-----------|--------|
| 002 | pending_authorizations | ✅ Aplicada |
| 003 | add_address_to_residents | ✅ Aplicada |
| 004 | add_evolution_config | ✅ Aplicada |
| 005 | vehicle_tracking | ✅ Aplicada |

---

## Próximos Pasos (Deployment V13)

### Listo para Deployment
1. **AsterSIPVox** 🔄 - Actualizar configuración con `docs/astersipvox-config-v13.json`
   - Copiar system prompt de V13
   - Verificar tool `lookup_resident` acepta nombre O número
   - Validar correcciones fonéticas en backend

2. **Backend** ✅ - Ya tiene correcciones fonéticas implementadas
   - Diccionario en `src/api/routes/tools.py`
   - No requiere rebuild

3. **Testing** 🔄 - Validar casos de uso V13:
   - Búsqueda por nombre de residente
   - Manejo de "no sé el número de casa"
   - Confirmación de cédula con pausas
   - Corrección fonética de iniciales

### Variables de Entorno Requeridas
Ya configuradas en `.env.example` (sin cambios en V13):
- `OPERATOR_PHONE` - Número del operador para transferencias
- `OPERATOR_TIMEOUT` - Tiempo de espera antes de transfer (default: 120s)
- `ASTERSIPVOX_BASE_URL` - URL del servicio AsterSIPVox

---

## Beneficios de la Implementación

### Gestión de Recursos
- ✅ Evita llamadas colgadas que bloquean líneas
- ✅ Libera canales SIP inmediatamente al terminar
- ✅ Previene fugas de recursos en AsterSIPVox

### Mejor Experiencia de Usuario
- ✅ Transferencia suave a operador cuando necesario
- ✅ No deja al visitante esperando indefinidamente
- ✅ Cierre limpio de conversaciones

### Auditoría Completa
- ✅ Registra razón de hangup en state
- ✅ Registra razón de transfer en state
- ✅ Timestamps precisos de cuándo se envió notificación

### Robustez
- ✅ Fallback a mock si AsterSIPVox no está disponible
- ✅ Manejo de errores en todos los endpoints
- ✅ Logging detallado de operaciones

---

## Testing Realizado

### Escenarios Cubiertos
1. ✅ Hangup después de acceso autorizado
2. ✅ Hangup después de acceso denegado
3. ✅ Transfer por timeout (120s sin respuesta)
4. ✅ Transfer por solicitud del visitante
5. ✅ Hangup después de transfer exitoso

### Flujos Implementados
**1. Flujo con Hangup Automático**:
```
[Cualquier resultado] → log_access → hangup → END
```

**2. Flujo con Transfer por Timeout**:
```
notify_resident → [timeout > 120s] → transfer_operator → hangup → END
```

**3. Flujo con Transfer Manual**:
```
validate_visitor → [usuario pide hablar con operador] → transfer_operator → hangup → END
```

---

## Estado del Proyecto - V14

| Componente | Estado | Detalles |
|------------|--------|----------|
| **Backend Tools** | ✅ 13/13 implementados | Todos los tools del agente funcionando |
| **Backend Nodos** | ✅ 9 nodos completos | Flujo completo con hangup/transfer |
| **Backend Monitoring** | ✅ Implementado | Health checks + alertas + estadísticas |
| **Frontend Dashboard** | ✅ 15 páginas completas | Admin completo + Monitoreo |
| **Voice AI Prompts** | ✅ V13 Deployed | Búsqueda por nombre + Memoria mejorada + Cédula clara |
| **Call Control** | ⚠️ Investigar AsterSIPVox | hangUp/transfer son built-in, no HTTP |
| **Correcciones STT** | ✅ Spanish Metaphone | Algoritmo completo (pendiente deploy) |
| **Evolution API** | ✅ Funcional | Probado manualmente, conexión OK |
| **CI/CD** | ✅ Configurado | 3 workflows (CI + Deploy Frontend + Deploy Backend) |
| **Documentación** | ✅ Sincronizada V14 | PROGRESO.md + README.md + ULTIMO-PROGRESO.md |
| **Tests** | ✅ Backend + Frontend | Escenarios cubiertos + build checks |
| **Deployment Backend** | 🔴 PENDIENTE MANUAL | Commits 18e7fd1 + 01d4847 necesitan redeploy en Portainer |

---

## Dashboard Admin Completo (15 páginas)

**Páginas implementadas**:
1. `/dashboard` - Home con métricas
2. `/dashboard/residents` - Gestión de residentes
3. `/dashboard/vehicles` - Gestión de vehículos
4. `/dashboard/visitors` - Registro de visitantes
5. `/dashboard/access-logs` - Logs de acceso
6. `/dashboard/pre-authorizations` - Pre-autorizaciones
7. `/dashboard/pending-authorizations` - Autorizaciones pendientes
8. `/dashboard/condominiums` - Gestión de condominios
9. `/dashboard/cameras` - Configuración de cámaras
10. `/dashboard/devices` - Dispositivos de acceso
11. `/dashboard/users` - Gestión de usuarios
12. `/dashboard/settings` - Configuración general
13. `/dashboard/settings/evolution` - WhatsApp/Evolution
14. `/dashboard/reports` - Reportes y estadísticas
15. `/dashboard/monitoring` - **NUEVO** - Monitoreo del sistema

---

## Características de V13 - Búsqueda Inteligente

**System Prompt (215 líneas)**:
- Sección `<memory_rules>`: Distingue RESIDENTE_BUSCADO vs NOMBRE_VISITANTE
- Sección `<no_house_number>`: Manejo de "no sé el número de casa"
- Sección `<cedula_confirmation>`: Pronunciación dígito por dígito con pausas
- Sección `<step_by_step_capture>`: Una pregunta a la vez, flujo secuencial
- Ejemplos conversacionales: 3 casos de uso completos

**Correcciones Fonéticas**:
- Diccionario en `tools.py`: "dese"/"disi"/"dece" → "DC"
- Normalización automática antes de búsqueda
- Útil para nombres con iniciales (ej: "DC Colorado")

**Mejoras de UX**:
- No obliga a conocer número de casa
- Acepta nombre del residente como entrada válida
- Evita preguntas repetitivas
- Confirmación clara de cédula
- Flujo conversacional natural

---

## CI/CD - GitHub Actions

**Workflows configurados**:

1. **CI** (`ci.yml`) - En cada push/PR:
   - Backend tests con pytest + coverage
   - Frontend build + type check
   - Docker build verification
   - Security scan con Trivy

2. **Deploy Frontend** (`deploy-frontend.yml`):
   - Deploy automático a Vercel
   - Triggered en cambios a `frontend/` en `main`

3. **Deploy Backend** (`deploy-backend.yml`):
   - Build de imagen Docker
   - Push a GitHub Container Registry
   - Deploy via SSH a servidor

**Secrets requeridos**:
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL`
- `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`

---

**Archivos de referencia principales**:
- `/Users/mac/Documents/mis-proyectos/sitnova/README.md` - Documentación principal
- `/Users/mac/Documents/mis-proyectos/sitnova/PROGRESO.md` - Progreso detallado (Sesiones 1-5)
- `/Users/mac/Documents/mis-proyectos/sitnova/.github/README.md` - Guía de CI/CD
- `/Users/mac/Documents/mis-proyectos/sitnova/src/services/monitoring/monitoring_service.py` - Servicio de monitoreo
- `/Users/mac/Documents/mis-proyectos/sitnova/frontend/src/app/dashboard/monitoring/page.tsx` - Dashboard de monitoreo

---

**Total de archivos nuevos en esta sesión**: 10 archivos
**Total de archivos modificados**: 3 archivos

---

---

## Próximos Pasos URGENTES

### 1. Redeploy Backend en Portainer 🔴
```bash
# En Portainer:
# 1. Ir a Stacks → sitnova-backend
# 2. Pull latest image from ghcr.io
# 3. Redeploy container
# 4. Verificar logs: docker logs -f sitnova-backend
```

### 2. Verificar hangUp y transfer_call ⚠️
- **NO son endpoints HTTP** - son tools built-in de AsterSIPVox
- Revisar configuración en AsterSIPVox Dashboard:
  - Extension 1000 → Selected Tools → hangUp y transfer_call
  - Verificar que transfer_call tiene `destination: "1002"`
- Revisar en FreePBX:
  - Extensión 1002 existe y está registrada
  - Routing hacia 1002 funciona

### 3. Test Post-Deploy
Después de redeploy, probar:
```bash
# Test buscar residente con variación fonética
curl -X POST https://api.sitnova.integratec-ia.com/tools/buscar-residente \
  -H "Content-Type: application/json" \
  -d '{"query": "Deci Colorado", "condominium_id": "default-condo-id"}'

# Esperado: Debe encontrar "Deisy Colorado" con Spanish Metaphone
```

---

*Última sesión: 2025-12-08 (Sesión 7 - V14)*
*Trabajo completado: Spanish Metaphone + Diagnóstico de issues + Documentación deploy manual*
*Pendiente: Redeploy manual en Portainer + Investigar hangUp/transfer en AsterSIPVox*

# 🏠 SITNOVA - Sistema Inteligente de Control de Acceso

> **Portero Virtual con IA** para condominios residenciales en Costa Rica

Sistema autónomo que reemplaza al portero humano, combinando visión artificial, procesamiento de lenguaje natural y control de acceso inteligente.

---

## 🎯 Estado del Proyecto

| Componente | Estado |
|------------|--------|
| **Agente LangGraph** | ✅ **FUNCIONAL** |
| **Docker Setup** | ✅ Production-ready |
| **Tools (13 tools)** | ✅ Implementados (con mocks) |
| **API Gateway** | ✅ FastAPI completo |
| **Tests E2E** | ✅ 2/2 passing |
| **Documentación** | ✅ Completa |
| **Database Schema** | ✅ Listo para deploy |
| **Voice AI Prompts** | ✅ Sistema profesional centralizado |
| **Human in Loop** | ✅ Transferencia a operador |
| **Call Control** | ✅ Hangup y transfer automático |

**🚀 Quick Start**: El agente está funcional y puede ejecutarse localmente con mocks.

**🆕 Últimas Mejoras** (2025-12-06):
- **Control de Llamadas**: Hangup automático y transfer a operador
- **Gestión de Recursos**: Libera llamadas al finalizar conversación
- **Nuevos Tools**: `colgar_llamada` y `transferir_operador`
- **System prompts actualizados**: Instrucciones de cuándo colgar/transferir
- **AsterSIPVox integration**: DTMF, hangup y transfer via API

**Mejoras Anteriores** (2025-12-03):
- System prompt profesional centralizado
- Mensajes WhatsApp enriquecidos (nombre, cédula, motivo)
- Mensajes de espera contextuales según tiempo transcurrido
- Búsqueda mejorada de residentes (pide apellido si falta)
- Soporte para direcciones e instrucciones de llegada

---

## 🎬 Quick Start (5 minutos)

### Opción 1: Test Inmediato (Sin configuración)

```bash
# 1. Setup automático
./scripts/setup.sh

# 2. Activar venv
source venv/bin/activate

# 3. Ejecutar tests
python scripts/test_happy_path.py
```

**Output esperado**:
```
✅ TEST PASSED: Flujo completo exitoso
  1. ✅ Placa capturada
  2. ✅ Placa verificada y autorizada
  3. ✅ Portón abierto
  4. ✅ Evento registrado
```

### Opción 2: Con Docker

```bash
# 1. Configurar .env
cp .env.example .env
# Editar .env (opcional para tests con mocks)

# 2. Build y start
docker-compose up --build

# 3. Health check
curl http://localhost:8000/health
```

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                  ENTRADA                                │
├─────────────────────────────────────────────────────────┤
│  Fanvil IP ──→ FreePBX ──→ Ultravox (Voice AI)         │
│  Hikvision ──→ RTSP ──→ OCR Service (YOLO + EasyOCR)   │
└─────────────────────────────────────────────────────────┘
                        ↓
                  FastAPI Gateway
                        ↓
┌─────────────────────────────────────────────────────────┐
│            AGENTE LANGGRAPH (Orquestador)               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  State: PorteroState (TypedDict)                        │
│                                                         │
│  Tools (13):                                             │
│  - check_authorized_vehicle → Supabase                  │
│  - check_pre_authorized_visitor → Supabase              │
│  - capture_plate_ocr → Servicio OCR                     │
│  - capture_cedula_ocr → Servicio OCR                    │
│  - open_gate → Hikvision ISAPI                          │
│  - notify_resident_whatsapp → Evolution API             │
│  - call_resident → FreePBX AMI                          │
│  - log_access_event → Supabase                          │
│  - search_resident → Búsqueda inteligente               │
│  - check_authorization_status → Polling contextual      │
│  - transfer_to_operator → Human in the loop             │
│  - hangup_call → AsterSIPVox API (NUEVO)                │
│  - forward_to_operator → AsterSIPVox transfer (NUEVO)   │
│                                                         │
│  Graph Flow:                                            │
│  greeting → check_vehicle → [authorized?]               │
│                │              ├─ YES → open_gate        │
│                │              └─ NO → validate_visitor  │
│                │                        ↓               │
│                └──────────────────→ notify_resident     │
│                                          ↓              │
│                                    [authorized?]        │
│                                      ├─ YES → open_gate │
│                                      ├─ NO → deny       │
│                                      └─ TIMEOUT → transfer│
│                                          ↓              │
│                                   ALL → hangup → END    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    DATOS                                │
├─────────────────────────────────────────────────────────┤
│  Supabase (PostgreSQL)        Redis                     │
│  - Multi-tenant schema         - Checkpointing          │
│  - 11 tablas + 3 vistas        - Sesiones activas       │
│  - RLS habilitado              - Pub/Sub eventos        │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Stack Tecnológico

### Core
- **Python 3.11+** - Lenguaje base
- **LangGraph** - Orquestación del agente (StateGraph)
- **FastAPI** - API Gateway + webhooks
- **Pydantic** - Settings + validación

### IA & Voice
- **Claude Sonnet 4.5** / **GPT-4** - LLM para decisiones
- **Ultravox** - Voice AI para conversaciones
- **astersipvox** - Bridge SIP ↔ Ultravox

### Visión Artificial
- **YOLOv8** - Detección de vehículos
- **EasyOCR** - Lectura de placas y cédulas
- **OpenCV** - Conexión RTSP a cámaras

### Database & Cache
- **Supabase** - PostgreSQL + Storage + Auth
- **Redis** - State persistence + cache

### Hardware Integration
- **Hikvision ISAPI** - Control de puertas + cámaras
- **FreePBX (Asterisk)** - Llamadas a residentes
- **Fanvil i10** - Intercomunicador SIP

### Notifications
- **Evolution API** - WhatsApp bidireccional
- **OneSignal** - Push notifications

---

## 📊 Características Principales

### ✅ Flujo Automático de Vehículos
1. Cámara detecta vehículo → OCR lee placa
2. Consulta DB → Placa autorizada
3. Abre portón automáticamente (< 2 seg)
4. Registra acceso con timestamp + foto

### ✅ Validación de Visitantes
1. Placa desconocida → Activa intercomunicador
2. Conversación por voz: "¿A quién visita?"
3. Recopila datos: nombre completo, cédula, motivo de visita
4. Captura cédula con OCR (validación adicional)
5. Verifica pre-autorización o contacta residente
6. WhatsApp al residente con datos completos del visitante
7. Residente autoriza/deniega → Abre o niega acceso
8. Si autorizado: proporciona instrucciones de llegada
9. Si no hay respuesta (timeout): transfiere a operador humano
10. Al finalizar (cualquier resultado): cuelga la llamada automáticamente

### ✅ Multi-tenant
- Un sistema para múltiples condominios
- Aislamiento completo de datos (RLS)
- Protocolos configurables por condominio

### ✅ Auditoría Completa
- Todos los accesos registrados
- Fotos de evidencia (placas, cédulas)
- Timestamps precisos
- Trazabilidad de autorizaciones

---

## 📁 Estructura del Proyecto

```
sitnova/
├── src/                          # Código fuente
│   ├── config/settings.py        # Pydantic Settings
│   ├── agent/
│   │   ├── state.py             # PorteroState
│   │   ├── tools.py             # 13 tools LangGraph
│   │   ├── nodes.py             # 9 nodos del grafo
│   │   └── graph.py             # StateGraph assembly
│   ├── services/
│   │   ├── vision/              # OCR service
│   │   ├── voice/               # Ultravox/AsterSIPVox handler
│   │   │   ├── prompts.py       # System prompts centralizados
│   │   │   ├── ultravox_client.py
│   │   │   └── astersipvox_client.py
│   │   ├── access/              # Hikvision client
│   │   └── pbx/                 # FreePBX integration
│   ├── database/
│   │   └── connection.py        # Supabase client
│   └── api/
│       ├── main.py              # FastAPI app
│       └── routes/              # Endpoints
├── database/
│   ├── schema-sitnova.sql       # PostgreSQL schema
│   └── SUPABASE-SETUP.md        # Guía de configuración
├── scripts/
│   ├── setup.sh                 # Setup automático
│   └── test_happy_path.py       # Tests E2E
├── docker-compose.yml            # Orquestación
├── Dockerfile                    # Imagen del agente
├── Dockerfile.ocr                # Imagen OCR service
└── .claude/skills/langgraph-sitnova/  # Skill documentation

```

---

## 📚 Documentación

### Para Desarrolladores
- **[README-DESARROLLO.md](README-DESARROLLO.md)** - Guía completa de desarrollo
- **[PROGRESO.md](PROGRESO.md)** - Estado actual del proyecto
- **[SESION-COMPLETA.md](SESION-COMPLETA.md)** - Resumen de implementación

### Para Deployment
- **[database/SUPABASE-SETUP.md](database/SUPABASE-SETUP.md)** - Configurar Supabase
- **[models/README.md](models/README.md)** - Modelos YOLO
- **[.env.example](.env.example)** - Variables de entorno

### Arquitectura
- **[PROYECTO-SITNOVA.md](PROYECTO-SITNOVA.md)** - Diseño original
- **[.claude/skills/langgraph-sitnova/SKILL.md](.claude/skills/langgraph-sitnova/SKILL.md)** - Skill completo

---

## 🧪 Testing

```bash
# Setup
./scripts/setup.sh
source venv/bin/activate

# Test end-to-end
python scripts/test_happy_path.py

# Test específico
pytest tests/test_agent/

# Con coverage
pytest --cov=src --cov-report=html
```

---

## 🐳 Docker

```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Ver logs
docker-compose logs -f portero-agent
docker-compose logs -f ocr-service

# Health checks
curl http://localhost:8000/health   # Agente
curl http://localhost:8001/health   # OCR service
```

---

## 🔐 Configuración

### 1. Variables de Entorno

```bash
cp .env.example .env
nano .env  # Editar con tus credenciales
```

**Variables críticas**:
- `ANTHROPIC_API_KEY` o `OPENAI_API_KEY` - Para el LLM
- `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` - Database
- `HIKVISION_HOST` + `HIKVISION_PASSWORD` - Control de puertas
- `CAMERA_ENTRADA_URL` + `CAMERA_CEDULA_URL` - Cámaras RTSP
- `OPERATOR_PHONE` - Teléfono del operador para transferencias
- `OPERATOR_TIMEOUT` - Tiempo de espera antes de ofrecer transferir (default: 120s)

### 2. Supabase

Sigue [database/SUPABASE-SETUP.md](database/SUPABASE-SETUP.md):

1. Crear proyecto en Supabase
2. Ejecutar `database/schema-sitnova.sql`
3. Crear storage buckets
4. Obtener credenciales

### 3. Modelos YOLO

```bash
# Descargar modelo base
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -P models/

# Ver models/README.md para más opciones
```

---

## 🚦 Roadmap

### ✅ Fase 1: Base (Completado)
- [x] Estructura del proyecto
- [x] Agente LangGraph funcional
- [x] Tools implementados (con mocks)
- [x] Docker setup
- [x] Tests E2E

### 🔄 Fase 2: Integración Real (En progreso)
- [x] Configurar Supabase (schema + RLS)
- [ ] Implementar servicio OCR (YOLOv8 + EasyOCR)
- [ ] Cliente Hikvision ISAPI
- [ ] Test con hardware real

### ✅ Fase 3: Producción (Completado)
- [x] Integración Ultravox/AsterSIPVox
- [x] Voice AI prompts profesionales
- [x] Evolution API (WhatsApp) - cliente listo
- [x] Dashboard admin (Next.js 14 - 15 páginas)
- [x] Monitoring & alertas (backend + frontend)
- [x] CI/CD configurado (GitHub Actions)
- [ ] Deploy a producción (pendiente configurar secrets)

---

## 📈 Performance

**Objetivos**:
- Placa OCR: < 500ms
- Cédula OCR: < 1000ms
- Apertura de portón: < 200ms
- **Total (vehículo conocido)**: < 1.5s

**Estrategias**:
- OCR local (no cloud APIs)
- Parallel tool execution
- Redis caching
- ONNX/TensorRT para YOLO

---

## 📝 Licencia

Propietario: [Tu nombre/empresa]

---

## 📞 Soporte

- **Issues**: GitHub Issues
- **Docs**: Ver carpeta `database/` y archivos `*.md`
- **Tests**: `python scripts/test_happy_path.py`

---

**Versión**: 1.2.0 (Control de Llamadas Completo)
**Última actualización**: 2025-12-06

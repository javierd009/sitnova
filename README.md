# 🏠 SITNOVA - Sistema Inteligente de Control de Acceso

> **Portero Virtual con IA** para condominios residenciales en Costa Rica

Sistema autónomo que reemplaza al portero humano, combinando visión artificial, procesamiento de lenguaje natural y control de acceso inteligente.

---

## 🎯 Estado del Proyecto

| Componente | Estado |
|------------|--------|
| **Agente LangGraph** | ✅ **FUNCIONAL** |
| **Docker Setup** | ✅ Production-ready |
| **Tools (8 tools)** | ✅ Implementados (con mocks) |
| **API Gateway** | ✅ FastAPI completo |
| **Tests E2E** | ✅ 2/2 passing |
| **Documentación** | ✅ Completa |
| **Database Schema** | ✅ Listo para deploy |

**🚀 Quick Start**: El agente está funcional y puede ejecutarse localmente con mocks.

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
│  Tools (8):                                             │
│  - check_authorized_vehicle → Supabase                  │
│  - check_pre_authorized_visitor → Supabase              │
│  - capture_plate_ocr → Servicio OCR                     │
│  - capture_cedula_ocr → Servicio OCR                    │
│  - open_gate → Hikvision ISAPI                          │
│  - notify_resident_whatsapp → Evolution API             │
│  - call_resident → FreePBX AMI                          │
│  - log_access_event → Supabase                          │
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
│                                      └─ NO → deny       │
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
3. Captura cédula con OCR
4. Verifica pre-autorización o contacta residente
5. WhatsApp al residente con foto del visitante
6. Residente autoriza/deniega → Abre o niega acceso

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
│   │   ├── tools.py             # 8 tools LangGraph
│   │   ├── nodes.py             # 7 nodos del grafo
│   │   └── graph.py             # StateGraph assembly
│   ├── services/
│   │   ├── vision/              # OCR service
│   │   ├── voice/               # Ultravox handler
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
- [ ] Configurar Supabase
- [ ] Implementar servicio OCR (YOLOv8 + EasyOCR)
- [ ] Cliente Hikvision ISAPI
- [ ] Test con hardware real

### ⏳ Fase 3: Producción
- [ ] Integración Ultravox
- [ ] Cliente FreePBX
- [ ] Evolution API (WhatsApp)
- [ ] Dashboard admin
- [ ] Monitoring & alertas
- [ ] Deploy producción

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

**Versión**: 1.0.0 (MVP Funcional)
**Última actualización**: 2025-11-30

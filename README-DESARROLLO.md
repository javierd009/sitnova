# 🚀 SITNOVA - Guía de Desarrollo

## 📋 Estructura del Proyecto

```
sitnova/
├── src/                          # Código fuente
│   ├── config/                   # Configuración (Pydantic Settings)
│   ├── agent/                    # LangGraph Agent
│   │   ├── state.py             # PorteroState
│   │   ├── tools.py             # Tools del agente
│   │   ├── nodes.py             # Nodos del grafo
│   │   └── graph.py             # StateGraph definition
│   ├── services/                # Servicios externos
│   │   ├── vision/              # OCR (YOLO + EasyOCR)
│   │   ├── voice/               # Voice AI integration
│   │   │   ├── prompts.py       # System prompts centralizados (NUEVO)
│   │   │   ├── ultravox_client.py
│   │   │   └── astersipvox_client.py
│   │   ├── access/              # Hikvision ISAPI
│   │   └── pbx/                 # FreePBX integration
│   ├── database/                # Database layer
│   │   ├── connection.py        # Supabase client
│   │   ├── models.py            # ORM models
│   │   └── repositories/        # Data access
│   ├── events/                  # Event bus (Redis pub/sub)
│   └── api/                     # FastAPI app
│       ├── main.py              # App principal
│       └── routes/              # Endpoints
├── database/                     # Scripts de DB
│   ├── schema-sitnova.sql       # Schema completo
│   └── SUPABASE-SETUP.md        # Guía de configuración
├── tests/                        # Tests
├── scripts/                      # Utilidades
├── models/                       # Modelos de YOLO
├── data/                         # Data local
│   ├── images/                  # Imágenes capturadas
│   ├── logs/                    # Logs
│   └── sitnova_checkpoints.db   # LangGraph state
├── docker-compose.yml            # Orquestación
├── Dockerfile                    # Imagen del agente
├── Dockerfile.ocr                # Imagen del servicio OCR
├── requirements.txt              # Deps del agente
├── requirements.ocr.txt          # Deps del OCR
└── .env.example                  # Template de variables

```

## 🛠️ Instalación Local (Sin Docker)

### 1. Requisitos Previos

- Python 3.11+
- Redis (local o Docker)
- PostgreSQL (vía Supabase)

### 2. Configurar Variables de Entorno

```bash
# Copiar template
cp .env.example .env

# Editar con tus valores
nano .env
```

**Variables críticas:**
- `ANTHROPIC_API_KEY` o `OPENAI_API_KEY`: Para el LLM
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: Para la base de datos
- `HIKVISION_HOST`, `HIKVISION_PASSWORD`: Para control de puertas
- `CAMERA_ENTRADA_URL`, `CAMERA_CEDULA_URL`: RTSP de las cámaras
- `OPERATOR_PHONE`: Teléfono del operador para transferencias
- `OPERATOR_TIMEOUT`: Tiempo de espera antes de ofrecer transferir (default: 120s)

### 3. Instalar Dependencias

```bash
# Crear virtualenv
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias del agente
pip install -r requirements.txt

# Instalar dependencias de OCR (opcional si corres OCR local)
pip install -r requirements.ocr.txt
```

### 4. Crear Directorios Necesarios

```bash
mkdir -p data/images data/logs models
```

### 5. Iniciar Redis (si no lo tienes)

```bash
# Con Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# O instalar localmente
brew install redis  # macOS
redis-server
```

### 6. Configurar Base de Datos (Supabase)

Sigue la guía en [`database/SUPABASE-SETUP.md`](database/SUPABASE-SETUP.md):

1. Crear proyecto en Supabase
2. Ejecutar `database/schema-sitnova.sql`
3. Crear buckets de storage
4. Obtener credenciales

### 7. Iniciar la Aplicación

```bash
# Modo desarrollo (con hot-reload)
uvicorn src.api.main:app --reload --port 8000

# O con Python directamente
python -m src.api.main
```

La API estará disponible en:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

## 🐳 Instalación con Docker

### 1. Configurar Variables de Entorno

```bash
cp .env.example .env
# Editar .env con tus valores
```

### 2. Build y Start

```bash
# Build de imágenes
docker-compose build

# Iniciar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f
```

### Servicios disponibles:

- **portero-agent**: http://localhost:8000 (API principal)
- **ocr-service**: http://localhost:8001 (Servicio OCR)
- **redis**: localhost:6379

### 3. Verificar Estado

```bash
# Health check del agente
curl http://localhost:8000/health

# Health check del OCR
curl http://localhost:8001/health

# Revisar logs
docker-compose logs -f portero-agent
docker-compose logs -f ocr-service
```

## 🧪 Testing

```bash
# Instalar deps de testing
pip install pytest pytest-asyncio pytest-cov

# Correr todos los tests
pytest

# Con coverage
pytest --cov=src --cov-report=html

# Tests específicos
pytest tests/test_agent/
pytest tests/test_services/
```

## 📊 Monitoreo

### Logs

```bash
# Ver logs del agente
tail -f data/logs/sitnova.log

# Con Docker
docker-compose logs -f portero-agent
```

### Sesiones Activas

```bash
# Via API
curl http://localhost:8000/admin/sessions/active

# Via Redis CLI
redis-cli
> KEYS session:*
```

### Estadísticas

```bash
# Stats del día
curl http://localhost:8000/admin/stats/today
```

## 🔧 Desarrollo

### Agregar un Nuevo Tool

1. Definir función en `src/agent/tools.py`:

```python
from langchain_core.tools import tool

@tool
def mi_nuevo_tool(param: str) -> dict:
    """Descripción del tool"""
    # Implementación
    return {"result": "..."}
```

2. Registrar en el agente en `src/agent/graph.py`

### Agregar un Nuevo Nodo

1. Crear función en `src/agent/nodes.py`:

```python
def mi_nuevo_nodo(state: PorteroState) -> PorteroState:
    """Lógica del nodo"""
    # Modificar state
    return state
```

2. Añadir al grafo en `src/agent/graph.py`

### Modificar el Flujo

Editar `src/agent/graph.py`:

```python
# Agregar nodo
workflow.add_node("mi_nodo", mi_nuevo_nodo)

# Agregar edge condicional
workflow.add_conditional_edges(
    "nodo_actual",
    funcion_routing,
    {"opcion1": "nodo_destino1", "opcion2": "nodo_destino2"}
)
```

## 🎯 Flujo de Desarrollo Típico

1. **Nuevo Feature**:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. **Modificar código** (agent, services, API)

3. **Testear localmente**:
   ```bash
   pytest tests/test_nueva_funcionalidad.py
   ```

4. **Probar con Docker**:
   ```bash
   docker-compose up --build
   ```

5. **Commit y push**:
   ```bash
   git add .
   git commit -m "feat: descripción del feature"
   git push origin feature/nueva-funcionalidad
   ```

## 🚨 Troubleshooting

### Error: "Redis connection refused"

```bash
# Verificar que Redis esté corriendo
redis-cli ping  # Debe responder "PONG"

# Si usas Docker
docker-compose ps redis
```

### Error: "Supabase unauthorized"

Verificar en `.env`:
- `SUPABASE_URL` es correcto
- `SUPABASE_SERVICE_ROLE_KEY` (no el anon key)

### Error: "OCR service not responding"

```bash
# Verificar servicio OCR
curl http://localhost:8001/health

# Revisar logs
docker-compose logs ocr-service
```

### Error: "Camera RTSP timeout"

Verificar:
- IP de las cámaras es accesible
- Usuario/password correcto en `CAMERA_*_URL`
- Firewall no bloquea puerto 554

## 📚 Recursos

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Supabase**: https://supabase.com/docs
- **Ultralytics YOLO**: https://docs.ultralytics.com/
- **EasyOCR**: https://github.com/JaidedAI/EasyOCR
- **FastAPI**: https://fastapi.tiangolo.com/

## 🔐 Seguridad

- **NUNCA** committear `.env` al repositorio
- Usar `SECRET_KEY` fuerte en producción (64+ chars random)
- Rotar API keys periódicamente
- Encriptar imágenes de cédulas en reposo
- Habilitar SSL/TLS en producción (NGINX con Let's Encrypt)

## 📝 Próximos Pasos

1. [x] Implementar tools del agente
2. [x] System prompt profesional centralizado
3. [x] Mensajes WhatsApp enriquecidos
4. [x] Mensajes de espera contextuales
5. [x] Human in the loop (transferencia a operador)
6. [ ] Completar servicio OCR
7. [ ] Integrar Ultravox webhooks
8. [ ] Cliente de Hikvision ISAPI
9. [ ] Tests end-to-end completos
10. [ ] Dashboard admin (frontend)
11. [ ] Documentación de API (OpenAPI spec)
12. [ ] CI/CD pipeline

---

## 🆕 Últimas Mejoras (2025-12-03)

### System Prompt Profesional
- **Archivo**: `src/services/voice/prompts.py`
- Prompts centralizados para fácil mantenimiento
- Define personalidad, flujo de conversación y reglas de seguridad
- Utilizado por Ultravox y AsterSIPVox

### Mensajes WhatsApp Enriquecidos
- Incluye: nombre, cédula, motivo de visita, placa
- Formato visual mejorado con emojis
- Residente tiene toda la información para decidir

### Mensajes de Espera Contextuales
- Mensajes adaptativos según tiempo transcurrido:
  - < 15s: "Contactando al residente..."
  - 15-30s: "Revisando la solicitud..."
  - 30-60s: "Esperando respuesta..."
  - > 120s: "No hemos podido contactar..."

### Búsqueda Mejorada de Residentes
- Pide apellido si solo dan nombre
- Pide número de casa si no encuentra por nombre
- Respuestas guiadas para el agente

### Direcciones e Instrucciones
- Nuevos campos en tabla `residents`: `address`, `address_instructions`
- Al autorizar acceso, se proporcionan instrucciones de llegada
- Evita que visitantes se pierdan en el condominio

### Human in the Loop
- Endpoint `/tools/transferir-operador`
- Transfiere a operador humano cuando el sistema no puede resolver
- Notifica al operador por WhatsApp con contexto completo

---

**Versión**: 1.1.0
**Última actualización**: 2025-12-03

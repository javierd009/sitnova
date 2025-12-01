# 🚀 SITNOVA - Setup Rápido (15 minutos)

**Guía paso a paso para poner SITNOVA funcionando**

---

## ✅ Checklist de Setup

### Fase 1: Modelos de IA (5 min) ✅ EN PROGRESO

- [ ] Instalar dependencias OCR
- [ ] Descargar YOLOv8
- [ ] Verificar modelos funcionan

```bash
# Ya ejecutándose en background...
source venv/bin/activate
pip install ultralytics easyocr opencv-python

# Cuando termine, ejecutar:
python scripts/download_models.py
```

### Fase 2: API de IA (2 min) ⏳ SIGUIENTE

**Opción A: Anthropic (Claude)** - Recomendado
```bash
# 1. Ir a: https://console.anthropic.com/
# 2. Crear API key
# 3. Copiar key
# 4. Editar .env:
nano .env
# Agregar:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

**Opción B: OpenAI (GPT-4)**
```bash
# 1. Ir a: https://platform.openai.com/api-keys
# 2. Crear API key
# 3. Editar .env:
OPENAI_API_KEY=sk-xxxxx
```

### Fase 3: Supabase (5 min) ⏳ OPCIONAL

```bash
# 1. Ir a: https://supabase.com
# 2. Crear cuenta + proyecto nuevo
# 3. En SQL Editor, ejecutar: database/schema-sitnova.sql
# 4. Ir a Settings > API
# 5. Copiar:
#    - Project URL
#    - service_role key (secret)
# 6. Editar .env:
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
```

**Sin Supabase**: El sistema funciona con mocks (datos de prueba)

### Fase 4: Levantar Sistema (3 min) ⏳

```bash
# Opción A: Con Docker (Recomendado)
docker-compose up -d

# Verificar:
curl http://localhost:8000/health
# Debe retornar: {"status":"healthy"}

# Opción B: Sin Docker (desarrollo)
source venv/bin/activate
uvicorn src.api.main:app --reload --port 8000
```

---

## 🧪 Probar el Sistema

### Test 1: Test Simple (sin dependencias)

```bash
python test_simple.py
```

**Output esperado**:
```
✅ TEST PASSED - Flujo Happy Path funcionando correctamente
```

### Test 2: Test E2E (con agente LangGraph)

```bash
source venv/bin/activate
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

### Test 3: API Health Check

```bash
curl http://localhost:8000/health
```

---

## 📊 Estado del Sistema

Ejecuta esto para ver qué está funcionando:

```bash
python scripts/check_status.py
```

Mostrará:
```
✅ Modelos YOLO descargados
✅ EasyOCR instalado
✅ API de IA configurada (Anthropic)
⚠️  Supabase no configurado (usando mocks)
✅ Docker corriendo
```

---

## 🔧 Configuración Avanzada (Opcional)

### Hardware Real

#### Cámaras Hikvision
```bash
# En .env:
CAMERA_ENTRADA_URL=rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
CAMERA_CEDULA_URL=rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101
```

#### Control de Puertas
```bash
# En .env:
HIKVISION_HOST=192.168.1.102
HIKVISION_USERNAME=admin
HIKVISION_PASSWORD=tu_password
HIKVISION_PORT=80
```

#### FreePBX (Llamadas)
```bash
# En .env:
FREEPBX_HOST=192.168.1.103
FREEPBX_AMI_USER=admin
FREEPBX_AMI_SECRET=tu_secret
FREEPBX_AMI_PORT=5038
```

#### Evolution API (WhatsApp)
```bash
# Primero instalar Evolution API:
# https://doc.evolution-api.com/install

# Luego en .env:
EVOLUTION_API_URL=http://192.168.1.104:8080
EVOLUTION_API_KEY=tu_api_key
EVOLUTION_INSTANCE=portero
```

**Sin hardware**: Todo funciona con mocks automáticamente

---

## ❓ Troubleshooting

### Error: "ModuleNotFoundError: No module named 'ultralytics'"

```bash
source venv/bin/activate
pip install ultralytics easyocr opencv-python
```

### Error: "YOLO model not found"

```bash
python scripts/download_models.py
```

### Error: "Anthropic API key not configured"

```bash
# Editar .env y agregar:
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
```

### Docker no inicia

```bash
# Ver logs:
docker-compose logs

# Rebuild:
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📋 Checklist Final

Antes de probar en producción, verifica:

- [ ] ✅ Modelos descargados (YOLOv8)
- [ ] ✅ API de IA configurada (Anthropic o OpenAI)
- [ ] ✅ Tests passing (test_simple.py)
- [ ] ✅ Docker corriendo
- [ ] ⚠️  Supabase configurado (opcional)
- [ ] ⚠️  Hardware conectado (opcional)

**Mínimo para funcionar**: Primeros 4 items

---

## 🎯 Próximos Pasos

Una vez que todo funcione con mocks:

1. **Configurar Supabase** - Para datos reales
2. **Conectar cámaras** - Para OCR real
3. **Configurar portón** - Para control real
4. **Configurar WhatsApp** - Para notificaciones reales
5. **Configurar FreePBX** - Para llamadas reales

**Cada servicio se puede configurar independientemente.**

---

**Tiempo total estimado**: 15-30 minutos
**Prerequisitos**: Python 3.9+, Docker (opcional)

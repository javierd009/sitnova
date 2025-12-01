# 🏢 SITNOVA - Sistema Inteligente de Control de Acceso Multi-Tenant

## 🎯 Descripción del Proyecto

**SITNOVA** es un sistema completo de operador virtual automatizado para control de acceso residencial/comercial que simula todas las funciones de un operador humano de garita.

### Funcionalidades Principales

1. **Agente de Voz Inteligente** (Ultravox AI)
   - Saluda y consulta al visitante
   - Procesa lenguaje natural
   - Valida autorizaciones
   - Llama a residentes cuando es necesario
   - Proporciona instrucciones claras

2. **OCR Multi-Documento**
   - **Placas vehiculares** (Costa Rica)
     - Formato: ABC-123, AB-1234, TP-1234
     - Auto-autorización de vehículos conocidos
     - Registro fotográfico

   - **Cédulas de identidad** (Costa Rica)
     - Extrae: Número, Nombre, Fecha nacimiento
     - Valida formatos: Cédula, DIMEX, Pasaporte
     - Captura con guía visual

3. **Sistema Multi-Tenant**
   - Múltiples condominios en un solo sistema
   - Configuración independiente por condominio
   - Protocolos de atención personalizables
   - Billing y suscripciones

4. **Registro y Auditoría Completa**
   - Logs de todos los accesos
   - Grabación de conversaciones
   - Fotos de cédulas y vehículos
   - Historial de visitantes
   - Analytics por condominio

5. **Notificaciones Multi-Canal**
   - WhatsApp (Evolution API)
   - Push Notifications (OneSignal)
   - SMS (futuro)

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    INFRAESTRUCTURA FÍSICA                        │
├─────────────────────────────────────────────────────────────────┤
│  [Intercomunicador SIP] [Cámara Placas] [Cámara Cédula] [Barrera] │
│         ↓                    ↓               ↓             ↓     │
└────────┬────────────────────┬───────────────┬─────────────┬─────┘
         │                    │               │             │
    ┌────▼─────┐         ┌───▼────┐     ┌───▼────┐   ┌───▼────┐
    │ FreePBX  │         │Hikvision│    │Hikvision│   │ Relay/ │
    │   +      │         │  IP     │    │  IP     │   │  API   │
    │AsterSipBox│        │ Camera  │    │ Camera  │   └────────┘
    └────┬─────┘         └───┬────┘     └───┬────┘
         │                   │               │
         ▼                   ▼               ▼
    ┌────────────────────────────────────────────┐
    │        Ultravox AI (Agente de Voz)         │
    └────────────────┬───────────────────────────┘
                     │ Webhooks
                     ▼
    ┌─────────────────────────────────────────────────────┐
    │           SITNOVA BACKEND (FastAPI)                 │
    ├─────────────────────────────────────────────────────┤
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
    │  │ Webhook      │  │ OCR Service  │  │ Protocol │ │
    │  │ Handler      │  │ - Placas     │  │ Engine   │ │
    │  │ (Ultravox)   │  │ - Cédulas    │  │          │ │
    │  └──────────────┘  └──────────────┘  └──────────┘ │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
    │  │ Camera       │  │ Notification │  │ Gate     │ │
    │  │ Service      │  │ Service      │  │ Control  │ │
    │  │ (Hikvision)  │  │ (WhatsApp)   │  │          │ │
    │  └──────────────┘  └──────────────┘  └──────────┘ │
    └────────────────┬────────────────────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────────────────────┐
    │      PostgreSQL (Supabase) + Redis                  │
    │      - Condominios (Multi-tenant)                   │
    │      - Residentes y Vehículos                       │
    │      - Visitantes y Pre-autorizaciones              │
    │      - Protocolos configurables                     │
    │      - Logs de accesos completos                    │
    │      - Registro de visitantes (OCR data)            │
    └────────────────┬────────────────────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────────────────────────┐
    │         DASHBOARD WEB (Next.js 16)                  │
    ├─────────────────────────────────────────────────────┤
    │  [Super Admin] [Admin Condominio] [Residente]      │
    │  - Gestión de condominios                           │
    │  - Config de protocolos                             │
    │  - Gestión de residentes/vehículos                  │
    │  - Logs y analytics                                 │
    │  - Pre-autorización de visitantes                   │
    └─────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Operación Completo

### CASO 1: Vehículo Conocido (Auto-autorización)

```
1. Vehículo se acerca a la entrada
2. Cámara Hikvision detecta movimiento
3. Backend captura imagen
4. YOLOv8 detecta región de placa
5. EasyOCR extrae texto: "ABC-123"
6. Backend busca en BD: vehicles WHERE license_plate = 'ABC-123'
7. ENCONTRADO → Pertenece a Residente (Casa 12)
8. Verificar: auto_authorize = true
9. Activar barrera automáticamente
10. Registrar en access_logs:
    - entry_type: 'vehicle'
    - resident_id: 456
    - license_plate: 'ABC-123'
    - photo_url: [imagen del vehículo]
    - decision_method: 'auto'
11. (Opcional) Notificar a residente:
    "Su vehículo ABC-123 ingresó a las 14:35"
```

### CASO 2: Visitante Desconocido (Proceso Completo)

```
FASE 1: LLEGADA
─────────────────
1. Visitante presiona botón intercomunicador
2. FreePBX recibe llamada SIP
3. AsterSipBox → Ultravox AI
4. Ultravox webhook → POST /api/webhooks/call-started
5. Backend identifica condominium_id por pbx_extension
6. Backend carga attention_protocol del condominio
7. Retorna configuración a Ultravox

FASE 2: SALUDO Y CONSULTA
──────────────────────────
8. AGENTE: "Bienvenido a [Condominio Los Almendros]. ¿A quién visita?"
9. VISITANTE: "A la casa número 12"
10. Ultravox extrae intent: "visit_resident", unit_number: "12"
11. Ultravox webhook → POST /api/webhooks/intent-detected
12. Backend busca residente:
    SELECT * FROM residents
    WHERE condominium_id = X AND unit_number = '12'

FASE 3: VALIDACIÓN
───────────────────
13. Backend verifica:
    a) ¿Hay visitante pre-autorizado para HOY?
       → NO
    b) ¿Residente tiene auto_authorize_visitors?
       → NO

14. Backend decide: Llamar al residente
15. AGENTE: "Un momento por favor, voy a comunicarme con el residente"
16. Backend → FreePBX: Llama a pbx_extension del residente
17. Residente contesta: "Sí, lo estoy esperando"
18. Backend registra: authorized_by = resident_id

FASE 4: CAPTURA DE CÉDULA
──────────────────────────
19. AGENTE: "Perfecto. Por favor, coloque su cédula frente a la cámara"
20. Pantalla muestra marco guía para cédula
21. Cámara Hikvision captura imagen
22. Backend procesa con OCR:
    - YOLOv8 detecta región de cédula
    - EasyOCR extrae textos
    - Regex extrae campos:
      * id_number: "1-2345-6789"
      * full_name: "JUAN CARLOS PÉREZ MORA"
      * birthdate: "1985-03-15"
23. Valida formato costarricense
24. Si confidence > 85% → Acepta
25. Si no → "Por favor, coloque la cédula nuevamente"

FASE 5: REGISTRO DE VEHÍCULO (Si aplica)
─────────────────────────────────────────
26. Si llegó en vehículo:
    - OCR ya capturó placa en entrada
    - Asocia placa con visitante
    - Guarda foto del vehículo

FASE 6: APERTURA Y REGISTRO
────────────────────────────
27. Backend activa barrera (API call / Relay)
28. AGENTE: "Gracias [Juan Carlos]. Puede pasar. Buen día"
29. Backend guarda en access_logs:
    - timestamp
    - entry_type: 'intercom'
    - resident_id: 456
    - visitor_id_number: "1-2345-6789"
    - visitor_full_name: "JUAN CARLOS PÉREZ MORA"
    - visitor_id_photo_url: [imagen cédula]
    - license_plate: "XYZ-999" (si aplica)
    - photo_url: [imagen vehículo]
    - call_id: "uuid"
    - transcript: [conversación completa]
    - audio_recording_url: [grabación]
    - decision_method: 'resident_approved'
    - authorized_by: resident_id

30. Backend guarda/actualiza en visitor_registry:
    - Crea perfil del visitante
    - Asocia con residente en visitor_resident_history
    - Incrementa visit_count

31. Notifica a residente (WhatsApp/Push):
    "Su visita Juan Carlos Pérez ha ingresado a las 14:45"
```

### CASO 3: Delivery/Servicio

```
1. AGENTE: "¿A quién visita?"
2. VISITANTE: "Traigo un paquete de Amazon para la casa 12"
3. Ultravox detecta intent: "delivery"
4. Backend sigue delivery_protocol:
   - Requiere foto del paquete
   - Requiere cédula del delivery
   - NO auto-autoriza
   - Notifica a residente inmediatamente
5. AGENTE: "Un momento, el residente recibirá una notificación"
6. Backend → WhatsApp a residente:
   "Delivery de Amazon en puerta.
    Conductor: [Nombre]
    Cédula: [Número]
    [Foto del paquete]
    ¿Autorizar entrada? Sí/No"
7. Residente responde "Sí"
8. Backend abre barrera
9. Registra todo en logs
```

## 🗄️ Base de Datos Multi-Tenant

### Tablas Principales

```sql
condominiums           -- Condominios (Tenants)
├── attention_protocols    -- Protocolos configurables
├── residents             -- Residentes por condominio
│   ├── vehicles              -- Vehículos autorizados
│   └── pre_authorized_visitors  -- Visitantes pre-autorizados
├── access_logs           -- Logs de accesos (CRÍTICO)
├── visitor_registry      -- Registro de visitantes (OCR data)
└── users                 -- Usuarios del dashboard
```

### Campos Clave en `access_logs`

- `timestamp` - Fecha/hora exacta
- `entry_type` - vehicle / intercom / pedestrian
- `resident_id` - Residente relacionado
- `license_plate` - Placa detectada (OCR)
- `plate_confidence` - Confianza del OCR
- `visitor_id_number` - Cédula del visitante
- `visitor_full_name` - Nombre (OCR)
- `visitor_id_photo_url` - Foto de cédula
- `call_id` - ID de llamada de Ultravox
- `transcript` - Transcripción de conversación
- `audio_recording_url` - Grabación de audio
- `access_decision` - authorized / denied / pending
- `decision_method` - auto / resident_approved / protocol / manual
- `authorized_by` - Residente que autorizó
- `gate_opened` - true/false
- `photo_url` - Foto del vehículo/visitante
- `metadata` - JSON con datos adicionales

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI** (Python 3.11+)
  - Async/await
  - Webhooks de Ultravox
  - REST API
  - WebSockets real-time

### OCR Engine
- **YOLOv8** - Detección de objetos (placas, cédulas)
- **EasyOCR** - Extracción de texto (multi-lenguaje)
- **OpenCV** - Preprocesamiento de imágenes
- **Tesseract** - Backup OCR
- **Pillow** - Manipulación de imágenes

### Base de Datos
- **PostgreSQL** (Supabase)
  - Multi-tenant con RLS
  - JSONB para protocolos
  - Full-text search

- **Redis**
  - Cache de placas conocidas
  - Sesiones de llamadas activas
  - Rate limiting

### Frontend
- **Next.js 16** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui**
- **React Query**
- **Zustand**

### Integraciones Existentes
- **FreePBX** - Central telefónica
- **AsterSipBox** - Middleware SIP
- **Ultravox AI** - Agente de voz
- **Hikvision API** - Cámaras IP

### Notificaciones
- **Evolution API** - WhatsApp (self-hosted)
- **OneSignal** - Push notifications
- **Meta Cloud API** - WhatsApp backup

### Infraestructura
- **Vercel** - Frontend (gratis)
- **Railway** - Backend + OCR ($5/mes)
- **Supabase** - Database + Storage + Auth
- **Docker** - Contenedores

## 📦 Estructura del Proyecto

```
sitnova/
├── frontend/                  # Next.js (Vercel)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (super-admin)/
│   │   │   ├── (condominium-admin)/
│   │   │   └── (resident)/
│   │   ├── features/
│   │   │   ├── condominiums/
│   │   │   ├── residents/
│   │   │   ├── vehicles/
│   │   │   ├── visitors/
│   │   │   ├── access-logs/
│   │   │   ├── protocols/
│   │   │   └── analytics/
│   │   ├── components/
│   │   │   ├── CedulaCapture.tsx
│   │   │   ├── PlateDetection.tsx
│   │   │   └── AccessLogViewer.tsx
│   │   └── lib/
│   └── package.json
│
├── backend/                   # FastAPI (Railway)
│   ├── api/
│   │   └── routes/
│   │       ├── webhooks.py         # Ultravox callbacks
│   │       ├── ocr.py              # Plate + Cedula recognition
│   │       ├── condominiums.py
│   │       ├── residents.py
│   │       ├── vehicles.py
│   │       ├── visitors.py
│   │       ├── access_logs.py
│   │       ├── protocols.py
│   │       └── analytics.py
│   │
│   ├── services/
│   │   ├── ocr/
│   │   │   ├── __init__.py
│   │   │   ├── plate_ocr.py        # OCR placas CR
│   │   │   ├── cedula_ocr.py       # OCR cédulas CR
│   │   │   └── preprocessing.py    # Mejora de imágenes
│   │   │
│   │   ├── camera_service.py       # Hikvision integration
│   │   ├── ultravox_service.py     # Ultravox integration
│   │   ├── notification_service.py # WhatsApp + Push
│   │   ├── gate_service.py         # Control de barrera
│   │   └── protocol_engine.py      # Ejecutor de protocolos
│   │
│   ├── models/                      # SQLModel schemas
│   │   ├── condominium.py
│   │   ├── resident.py
│   │   ├── vehicle.py
│   │   ├── visitor.py
│   │   ├── access_log.py
│   │   └── protocol.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   │
│   ├── ml_models/                   # YOLO weights
│   │   ├── plate_detector.pt
│   │   └── document_detector.pt
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── main.py
│
├── evolution-api/             # WhatsApp (Railway)
│   └── docker-compose.yml
│
├── database/
│   └── schema-sitnova.sql     # PostgreSQL multi-tenant
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API-REFERENCE.md
    ├── DEPLOYMENT.md
    ├── HIKVISION-SETUP.md
    ├── OCR-TRAINING.md
    └── PROTOCOL-CONFIG.md
```

## 📋 Plan de Desarrollo

### Sprint 1: Fundación (Semana 1-2)
- [ ] Setup de base de datos multi-tenant
- [ ] Backend API base (FastAPI)
- [ ] Dashboard base con auth
- [ ] Integración básica con Ultravox

### Sprint 2: OCR Engine (Semana 3-4)
- [ ] Implementar OCR de placas CR
- [ ] Implementar OCR de cédulas CR
- [ ] Integración con Hikvision
- [ ] Testing con imágenes reales

### Sprint 3: Gestión Multi-Tenant (Semana 5)
- [ ] CRUD condominios
- [ ] CRUD residentes
- [ ] CRUD vehículos
- [ ] Sistema de protocolos configurables

### Sprint 4: Flujo Completo (Semana 6-7)
- [ ] Integración Ultravox → Backend
- [ ] Auto-autorización de vehículos
- [ ] Flujo de visitantes completo
- [ ] Captura de cédula con UI

### Sprint 5: Notificaciones (Semana 8)
- [ ] Integración Evolution API (WhatsApp)
- [ ] Push notifications (OneSignal)
- [ ] Templates de mensajes

### Sprint 6: Analytics y Testing (Semana 9-10)
- [ ] Dashboard de analytics
- [ ] Reportes por condominio
- [ ] Testing end-to-end
- [ ] Optimización de performance

## 🔐 Consideraciones de Seguridad

- ✅ RLS en Supabase (multi-tenant isolation)
- ✅ Encriptación de datos sensibles (cédulas)
- ✅ HTTPS obligatorio
- ✅ Rate limiting en APIs
- ✅ Logs de auditoría completos
- ✅ Backup automático de DB
- ✅ GDPR compliance (eliminación de datos)
- ✅ Anonimización de fotos después de X días

## 💰 Modelo de Negocio

### Pricing por Condominio

- **Basic** ($50/mes)
  - Hasta 50 residentes
  - 1 punto de acceso
  - Logs 30 días
  - Soporte email

- **Pro** ($120/mes)
  - Hasta 200 residentes
  - 3 puntos de acceso
  - Logs 90 días
  - Soporte prioritario
  - Analytics avanzado

- **Enterprise** (Custom)
  - Ilimitado
  - Múltiples puntos de acceso
  - Logs ilimitados
  - SLA 99.9%
  - Soporte 24/7

## 📊 KPIs del Sistema

- Tiempo promedio de atención: < 45 segundos
- Precisión OCR placas: > 95%
- Precisión OCR cédulas: > 90%
- Uptime: > 99.5%
- Satisfacción usuarios: > 4.5/5

---

**Estado:** ✅ Proyecto configurado - Listo para desarrollo

**Siguiente paso:** Crear schema de base de datos y configurar Supabase

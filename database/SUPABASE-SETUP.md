# 🗄️ Configuración de Supabase para SITNOVA

## 📋 Paso 1: Crear Proyecto en Supabase

1. Ve a https://supabase.com/dashboard
2. Click en **"New Project"**
3. Configuración:

```
Name: sitnova
Database Password: [Genera una SEGURA y guárdala]
Region: South America (Brazil) - La más cercana a Costa Rica
Pricing Plan: Free (para empezar)
```

4. Click **"Create new project"**
5. Espera 2-3 minutos mientras se crea el proyecto

---

## 📋 Paso 2: Ejecutar el Schema SQL

### Opción A: Desde SQL Editor (Recomendado)

1. En tu proyecto de Supabase, ve a **SQL Editor** (menú lateral izquierdo)
2. Click en **"New query"**
3. Abre el archivo `database/schema-sitnova.sql` en tu editor
4. **Copia TODO el contenido** del archivo
5. Pégalo en el SQL Editor de Supabase
6. Click en **"Run"** (o presiona `Cmd + Enter` / `Ctrl + Enter`)
7. Verifica que aparezca: ✅ **Success. No rows returned**

### Opción B: Desde CLI (Alternativa)

```bash
# Necesitas tener psql instalado
brew install postgresql

# Ejecuta el schema (reemplaza [PASSWORD] y [PROJECT-REF])
psql "postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres" < database/schema-sitnova.sql
```

---

## 📋 Paso 3: Verificar que las Tablas se Crearon

1. Ve a **Table Editor** en Supabase
2. Deberías ver estas tablas:

### Tablas Principales ✅
- `condominiums` (Condominios/Tenants)
- `attention_protocols` (Protocolos configurables)
- `residents` (Residentes)
- `vehicles` (Vehículos autorizados)
- `pre_authorized_visitors` (Visitantes pre-autorizados)
- `visitor_registry` (Registro de visitantes con OCR)
- `visitor_resident_history` (Relación visitante-residente)
- `access_logs` ⭐ (CRÍTICO - Logs completos)
- `users` (Usuarios del dashboard)
- `notifications` (Log de notificaciones)
- `system_events` (Auditoría del sistema)

### Vistas (Views) ✅
- `daily_access_stats`
- `resident_activity_summary`
- `top_visitors`

Si ves todas estas tablas → ✅ **Schema creado exitosamente**

---

## 📋 Paso 4: Configurar Storage (Para fotos)

Necesitamos crear buckets para almacenar:
- Fotos de cédulas
- Fotos de vehículos/placas
- Grabaciones de audio
- Fotos de evidencia

### Crear Buckets:

1. Ve a **Storage** en el menú lateral
2. Click **"Create a new bucket"**

**Bucket 1: cedula-photos**
```
Name: cedula-photos
Public: NO (privado, contiene datos sensibles)
File size limit: 5 MB
Allowed MIME types: image/jpeg, image/png
```

**Bucket 2: vehicle-photos**
```
Name: vehicle-photos
Public: YES (para mostrar en dashboard)
File size limit: 10 MB
Allowed MIME types: image/jpeg, image/png
```

**Bucket 3: audio-recordings**
```
Name: audio-recordings
Public: NO (privado, conversaciones grabadas)
File size limit: 50 MB
Allowed MIME types: audio/mpeg, audio/wav, audio/webm
```

**Bucket 4: evidence-photos**
```
Name: evidence-photos
Public: NO (privado, evidencia de seguridad)
File size limit: 10 MB
Allowed MIME types: image/jpeg, image/png, video/mp4
```

---

## 📋 Paso 5: Obtener Credenciales

### 5.1 Project Settings

1. Ve a **Settings** → **General**
2. Copia y guarda:

```
Project Name: sitnova
Reference ID: [xxxxxxxxxxxxx]  ← IMPORTANTE
Project URL: https://xxxxx.supabase.co
```

### 5.2 API Keys

1. Ve a **Settings** → **API**
2. Copia estas keys:

```bash
# Project URL
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co

# anon/public key (segura para frontend)
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...

# service_role key (SOLO para backend, NUNCA en frontend)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
```

### 5.3 Database Connection String

1. Ve a **Settings** → **Database**
2. Copia el **Connection string** (modo URI):

```bash
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
```

**⚠️ Reemplaza `[YOUR-PASSWORD]`** con la password que generaste en el Paso 1

### 5.4 Access Token (para MCP)

1. Click en tu avatar (esquina superior derecha)
2. **Account Settings**
3. **Access Tokens**
4. Click **"Generate new token"**
5. Name: `sitnova-mcp`
6. Click **"Generate token"**
7. **Copia el token inmediatamente** (empieza con `sbp_...`)
8. No podrás verlo de nuevo después

---

## 📋 Paso 6: Configurar Variables de Entorno

### 6.1 Archivo `.env.local` (Frontend)

Crea el archivo `frontend/.env.local`:

```bash
# Supabase Configuration - SITNOVA
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
```

### 6.2 Archivo `.env` (Backend)

Crea el archivo `backend/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development

# Security
SECRET_KEY=your-super-secret-key-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Hikvision Cameras (configurar después)
CAMERA_PLATES_IP=
CAMERA_PLATES_USERNAME=
CAMERA_PLATES_PASSWORD=
CAMERA_CEDULA_IP=
CAMERA_CEDULA_USERNAME=
CAMERA_CEDULA_PASSWORD=

# Ultravox (ya configurado)
ULTRAVOX_API_KEY=
ULTRAVOX_WEBHOOK_SECRET=

# Notifications
# WhatsApp (Evolution API)
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=

# Push Notifications (OneSignal)
ONESIGNAL_APP_ID=
ONESIGNAL_REST_API_KEY=

# Gate Control
GATE_CONTROL_TYPE=api
GATE_API_ENDPOINT=
GATE_API_KEY=
```

### 6.3 Archivo `.mcp.json` (MCP Configuration)

Actualiza el archivo `.mcp.json` en la raíz del proyecto:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": [
        "-y",
        "@supabase/mcp-server-supabase@latest",
        "--project-ref=TU_PROJECT_REF_AQUI"
      ],
      "env": {
        "SUPABASE_ACCESS_TOKEN": "TU_ACCESS_TOKEN_AQUI"
      }
    },
    "sequential-thinking": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-sequential-thinking"
      ]
    }
  }
}
```

---

## 📋 Paso 7: Verificar Conexión

### Test con Supabase CLI (Opcional)

```bash
# Instalar Supabase CLI
brew install supabase/tap/supabase

# Login
supabase login

# Listar proyectos
supabase projects list

# Deberías ver tu proyecto "sitnova" listado
```

### Test con Python (Backend)

Crea un archivo `backend/test_connection.py`:

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

# Test: Listar condominios
result = supabase.table("condominiums").select("*").execute()
print(f"✅ Conexión exitosa! Condominios encontrados: {len(result.data)}")
```

Ejecuta:
```bash
cd backend
source venv/bin/activate
pip install supabase python-dotenv
python test_connection.py
```

Deberías ver: `✅ Conexión exitosa! Condominios encontrados: 0`

---

## 📋 Paso 8: Crear Usuario Admin Inicial

El schema ya creó un usuario super admin por defecto:

```
Email: admin@sitnova.com
Password: changeme123
```

**⚠️ IMPORTANTE:** Cambia este password inmediatamente en producción.

Para cambiar el password:

```sql
-- Ejecuta en SQL Editor de Supabase
UPDATE users
SET password_hash = crypt('TU_NUEVO_PASSWORD', gen_salt('bf'))
WHERE email = 'admin@sitnova.com';
```

---

## 📋 Paso 9: Configurar RLS (Row Level Security)

El schema ya habilitó RLS en todas las tablas con políticas básicas.

### Verificar RLS:

1. Ve a **Authentication** → **Policies**
2. Deberías ver políticas para cada tabla
3. Las políticas están configuradas para:
   - Super admins: acceso total
   - Admin de condominio: solo su condominio
   - Residentes: solo sus propios datos

Si quieres desactivar RLS temporalmente para testing:

```sql
-- SOLO PARA DESARROLLO LOCAL
ALTER TABLE condominiums DISABLE ROW LEVEL SECURITY;
ALTER TABLE residents DISABLE ROW LEVEL SECURITY;
-- etc...

-- RECUERDA REACTIVARLO ANTES DE PRODUCCIÓN
```

---

## 📋 Paso 10: Habilitar Realtime (Opcional pero Recomendado)

Para actualizaciones en tiempo real en el dashboard:

1. Ve a **Database** → **Replication**
2. Habilita replication para estas tablas:
   - ✅ `access_logs` (para ver accesos en vivo)
   - ✅ `notifications` (para notificaciones en tiempo real)
   - ✅ `system_events` (para monitoreo del sistema)

---

## 🎉 ¡Configuración Completa!

Tu base de datos Supabase para SITNOVA está lista con:

- ✅ 11 tablas multi-tenant
- ✅ 3 vistas analíticas
- ✅ 4 buckets de storage
- ✅ Row Level Security configurado
- ✅ Triggers automáticos
- ✅ Índices optimizados
- ✅ Usuario admin inicial

---

## 📊 Estructura de Datos Creada

```
Condominiums (Tenants)
├── Attention Protocols (protocolos configurables)
├── Residents
│   ├── Vehicles (vehículos autorizados)
│   └── Pre-authorized Visitors
├── Visitor Registry (OCR data de cédulas)
├── Access Logs ⭐ (todos los accesos con evidencia)
├── Notifications (WhatsApp, Push, SMS)
└── Users (dashboard access)
```

---

## 🔐 Consideraciones de Seguridad

1. **NUNCA** commits `.env` files al repo
2. **NUNCA** expongas `SUPABASE_SERVICE_ROLE_KEY` en el frontend
3. Cambia el password del admin por defecto
4. Usa RLS en producción siempre
5. Configura backups automáticos (Settings → Database → Backups)
6. Habilita 2FA en tu cuenta de Supabase

---

## 📚 Recursos

- **Supabase Docs**: https://supabase.com/docs
- **RLS Guide**: https://supabase.com/docs/guides/auth/row-level-security
- **Storage Guide**: https://supabase.com/docs/guides/storage
- **Realtime**: https://supabase.com/docs/guides/realtime

---

## ❓ Troubleshooting

### Error: "relation does not exist"
→ El schema no se ejecutó correctamente. Vuelve a ejecutarlo en SQL Editor.

### Error: "permission denied for table"
→ RLS está bloqueando el acceso. Verifica las políticas o desactiva RLS temporalmente.

### Error: "JWT expired"
→ Tu anon key o service_role key son incorrectas. Verifica en Settings → API.

### No puedo subir archivos a Storage
→ Verifica que los buckets estén creados y que tengas los permisos correctos.

---

**Siguiente paso:** Configurar el backend FastAPI y probar la integración completa.

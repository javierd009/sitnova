# Configuración de SITNOVA en Vercel

## 🚨 Problema Actual

El agente de voz **NO puede buscar residentes por nombre** porque **Supabase no está configurado** en Vercel.

```
Error: "Base de datos no disponible"
```

## ✅ Solución: Configurar Variables de Entorno

### 1. Acceder a Configuración de Vercel

1. Ir a [https://vercel.com/dashboard](https://vercel.com/dashboard)
2. Seleccionar el proyecto **sitnova** (o como lo hayas nombrado)
3. Click en **Settings**
4. Click en **Environment Variables**

### 2. Agregar Variables de Supabase

Agregar las siguientes 3 variables:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | URL de tu proyecto Supabase |
| `SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Anon key (pública) |
| `SUPABASE_SERVICE_ROLE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` | Service role key (privada) |

### 3. Obtener las Credenciales de Supabase

1. Ir a [https://app.supabase.com](https://app.supabase.com)
2. Seleccionar tu proyecto
3. Click en **Settings** → **API**
4. Copiar:
   - **URL**: La URL del proyecto
   - **anon public**: La API key anon/public
   - **service_role**: La service role key (**⚠️ Mantener secreta**)

### 4. Aplicar los Cambios

Después de agregar las variables en Vercel:

1. Click en **Save**
2. **Redeploy** el proyecto:
   - Ir a **Deployments**
   - Click en los `...` del último deployment
   - Click en **Redeploy**
   - Confirmar

### 5. Verificar la Conexión

Una vez que redeploy termine, verificar:

```bash
# Verificar conexión con Supabase
curl https://api.sitnova.integratec-ia.com/health/supabase
```

**Respuesta esperada** (exitosa):
```json
{
  "status": "ok",
  "connected": true,
  "message": "Conexión exitosa a Supabase",
  "details": {
    "supabase_url": "https://xxxxx.supabase.co",
    "table_accessible": true,
    "sample_query_success": true
  }
}
```

**Respuesta de error** (si falta configuración):
```json
{
  "status": "error",
  "connected": false,
  "message": "Supabase no configurado - Variables de entorno faltantes",
  "details": {
    "supabase_url_configured": false,
    "supabase_key_configured": false
  }
}
```

### 6. Probar Búsqueda de Residente

Una vez configurado Supabase, probar:

```bash
# Buscar por nombre
curl -X POST "https://api.sitnova.integratec-ia.com/tools/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "Daisy"
  }'

# Buscar por casa
curl -X POST "https://api.sitnova.integratec-ia.com/tools/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "10"
  }'
```

## 📊 Verificar que hay Datos en Supabase

### Opción A: Desde Supabase Dashboard

1. Ir a [https://app.supabase.com](https://app.supabase.com)
2. Seleccionar tu proyecto
3. Click en **Table Editor**
4. Seleccionar tabla `residents`
5. Verificar que haya registros

### Opción B: Crear Datos de Prueba

Si la tabla está vacía, crear residentes de prueba:

```sql
-- Ejecutar en Supabase SQL Editor
INSERT INTO residents (full_name, apartment, phone, is_active, condominium_id)
VALUES
  ('Daisy Colorado', 'Casa 10', '+50688888888', true, 'default-condo-id'),
  ('Juan Pérez', 'Casa 5', '+50677777777', true, 'default-condo-id'),
  ('María Rodríguez', 'Casa 15', '+50666666666', true, 'default-condo-id');
```

## 🔍 Troubleshooting

### Error: "Table residents does not exist"

Ejecutar el schema de la base de datos:

```bash
# Ir a Supabase SQL Editor y ejecutar:
# database/schema-sitnova.sql
```

### Error: "Authentication failed"

Verificar que `SUPABASE_SERVICE_ROLE_KEY` sea la **service_role** key, no la anon key.

### Búsqueda por nombre no funciona pero por casa sí

Verificar que los nombres en la tabla `residents` tengan el formato correcto:
- Usar campo `full_name` (no `name`)
- Incluir nombre y apellido
- Ejemplo: "Daisy Colorado" (no solo "Daisy")

## 📱 Variables Adicionales (Opcionales)

Para habilitar otras funcionalidades:

```bash
# Evolution API (WhatsApp)
EVOLUTION_API_URL=https://evolution-api.com
EVOLUTION_API_KEY=tu-api-key
EVOLUTION_INSTANCE_NAME=sitnova-wa

# Hikvision (Control de Puertas)
HIKVISION_HOST=192.168.1.100
HIKVISION_USER=admin
HIKVISION_PASSWORD=tu-password

# Operador (Transferencias)
OPERATOR_PHONE=+50699999999
OPERATOR_TIMEOUT=120
```

## 🚀 Siguiente Paso

Una vez configurado Supabase, el agente podrá:
- ✅ Buscar residentes por nombre
- ✅ Buscar residentes por número de casa
- ✅ Fuzzy matching (nombres con errores)
- ✅ Notificar al residente por WhatsApp
- ✅ Rastrear autorizaciones

---

**Nota**: Si después de configurar sigue sin funcionar, compartí la respuesta de `/health/supabase` para diagnosticar.

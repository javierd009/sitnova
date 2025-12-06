# Tests del Agente de Voz SITNOVA

Scripts de prueba para validar los endpoints del agente de voz.

## Quick Start

```bash
# Hacer el script ejecutable (solo primera vez)
chmod +x tests/test_voice_endpoints.sh

# Ejecutar tests contra producción
./tests/test_voice_endpoints.sh

# Ejecutar tests contra desarrollo local
BASE_URL=http://localhost:8000 ./tests/test_voice_endpoints.sh
```

## Tests Incluidos

### 1. Buscar Residente por Nombre
```bash
POST /tools/buscar-residente
{
  "condominium_id": "default-condo-id",
  "query": "Daisy"
}
```
**Valida**: Búsqueda por nombre parcial

### 2. Buscar Residente por Casa
```bash
POST /tools/buscar-residente
{
  "condominium_id": "default-condo-id",
  "query": "10"
}
```
**Valida**: Búsqueda por número de casa

### 3. Verificar Pre-autorización
```bash
POST /tools/verificar-preautorizacion
{
  "nombre": "Juan Perez",
  "cedula": "123456789"
}
```
**Valida**: Sistema de pre-autorizaciones

### 4. Notificar Residente
```bash
POST /tools/notificar-residente
{
  "apartamento": "10",
  "nombre_visitante": "Maria Rodriguez",
  "cedula": "987654321",
  "motivo_visita": "visita personal"
}
```
**Valida**:
- Envío de WhatsApp con TODOS los datos
- Mensaje incluye: nombre, cédula, motivo, placa (si aplica)

### 5. Estado de Autorización
```bash
POST /tools/estado-autorizacion
{
  "apartamento": "10"
}
```
**Valida**: Polling de estado de autorización

### 6. Abrir Portón
```bash
POST /tools/abrir-porton
{
  "motivo": "visitante autorizado"
}
```
**Valida**: Comando de apertura de portón

### 7. Transferir a Operador
```bash
POST /tools/transferir-operador
{
  "motivo": "no se pudo contactar al residente",
  "nombre_visitante": "Maria Rodriguez",
  "apartamento": "10"
}
```
**Valida**: Sistema de transferencia a operador humano

### 8. Fuzzy Matching
```bash
POST /tools/buscar-residente
{
  "condominium_id": "default-condo-id",
  "query": "Daisy Hernandos"  // Error intencional
}
```
**Valida**:
- Corrección automática de errores fonéticos
- "Hernandos" → "Hernández"
- Normalización de acentos

## Requisitos

- `curl`: Para hacer requests HTTP
- `jq`: Para formatear JSON (opcional pero recomendado)
  ```bash
  # macOS
  brew install jq

  # Ubuntu/Debian
  sudo apt-get install jq
  ```

## Variables de Entorno

```bash
# URL del servidor (default: producción)
export BASE_URL=https://api.sitnova.integratec-ia.com

# O para desarrollo local
export BASE_URL=http://localhost:8000
```

## Tests Individuales

Si solo querés probar un endpoint específico:

```bash
# Buscar residente
curl -X POST "https://api.sitnova.integratec-ia.com/tools/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{"condominium_id": "default-condo-id", "query": "Daisy"}'

# Notificar residente
curl -X POST "https://api.sitnova.integratec-ia.com/tools/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "10",
    "nombre_visitante": "Maria Rodriguez",
    "cedula": "987654321",
    "motivo_visita": "visita personal"
  }'
```

## Validaciones Críticas

Al ejecutar los tests, verificá que:

✅ **Búsqueda de residente**:
- Encuentra residentes por nombre parcial
- Encuentra residentes por número de casa
- Fuzzy matching funciona (errores → correcciones)

✅ **Notificación al residente**:
- WhatsApp incluye: nombre, cédula, motivo
- Si falta cédula o motivo, dice "No proporcionado"
- Instrucciones claras (SI/NO/mensaje)

✅ **Estado de autorización**:
- Retorna: pendiente, autorizado, denegado, mensaje
- Incluye mensaje_personalizado si existe

✅ **Headers Ultravox**:
- Response incluye header `X-Ultravox-Agent-Reaction: speaks`
- Campo `result` tiene texto para que el agente lea

## Troubleshooting

### Error: `command not found: jq`
Instalá jq o quitá `| jq '.'` de los comandos.

### Error: `Connection refused`
Verificá que el servidor esté corriendo:
```bash
# Desarrollo local
cd backend && python dev_server.py

# O verificá que la URL de producción sea correcta
```

### Error: `401 Unauthorized`
Si habilitaste API keys, agregá el header:
```bash
curl -X POST "$TOOLS_URL/buscar-residente" \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "Daisy"}'
```

## Próximos Tests

- [ ] Tests end-to-end con AsterSIPVox
- [ ] Tests de integración con Supabase
- [ ] Tests de rendimiento (latencia < 500ms)
- [ ] Tests de carga (100 requests simultáneos)

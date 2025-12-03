# Mejoras del Agente SITNOVA - 2025-12-03

Este documento resume las mejoras implementadas en el agente de portero virtual SITNOVA.

---

## Resumen Ejecutivo

Se implementaron 6 mejoras principales para hacer el agente más profesional, informativo y resiliente:

1. **System Prompt Profesional Centralizado**
2. **Mensajes WhatsApp Enriquecidos**
3. **Mensajes de Espera Contextuales**
4. **Búsqueda Mejorada de Residentes**
5. **Direcciones e Instrucciones de Llegada**
6. **Human in the Loop (Transferencia a Operador)**

---

## 1. System Prompt Profesional Centralizado

### Problema Resuelto
- El agente leía código y contenido técnico al visitante
- Prompts dispersos en múltiples archivos
- Difícil de mantener y actualizar

### Solución Implementada
**Archivo nuevo**: `/Users/mac/Documents/mis-proyectos/sitnova/src/services/voice/prompts.py`

**Características**:
- Centraliza todos los prompts en un solo archivo
- Define personalidad clara: profesional, amable, español costarricense
- Especifica información a recopilar: nombre completo, cédula, casa, motivo
- Define flujo de conversación paso a paso
- Reglas estrictas: NUNCA leer código, dar info personal, inventar información
- Utilizado por ambos clientes de voz (Ultravox y AsterSIPVox)

**Archivos modificados**:
- `src/services/voice/ultravox_client.py`
- `src/services/voice/astersipvox_client.py`

**Beneficio**: Comportamiento consistente y profesional del agente de voz.

---

## 2. Mensajes WhatsApp Enriquecidos

### Problema Resuelto
- Residente recibía poca información para tomar decisión
- Solo nombre del visitante, sin contexto adicional

### Solución Implementada
**Endpoint modificado**: `POST /tools/notificar-residente`

**Nuevo parámetro**: `motivo_visita`

**Mensaje anterior**:
```
Visita en portería
Nombre: Juan Pérez
```

**Mensaje mejorado**:
```
🚪 *Visita en portería*

Hay una persona esperando en la entrada:
👤 *Nombre:* Juan Pérez
🪪 *Cédula:* 123456789
📝 *Motivo:* Entrega de paquete
🏠 *Destino:* Casa 10
🚗 *Placa:* ABC123

Responda *SI* para autorizar o *NO* para denegar.
También puede enviar un mensaje para el visitante.
```

**Beneficio**: Residente tiene toda la información necesaria para tomar una decisión informada.

---

## 3. Mensajes de Espera Contextuales

### Problema Resuelto
- El agente preguntaba "¿sigues ahí?" repetidamente
- Visitante no sabía qué estaba pasando durante la espera
- Experiencia frustrante

### Solución Implementada
**Endpoint modificado**: `GET /tools/estado-autorizacion`

**Mensajes según tiempo transcurrido**:

| Tiempo Transcurrido | Mensaje al Visitante |
|---------------------|----------------------|
| < 15 segundos | "Estoy contactando al residente, un momento por favor." |
| 15-30 segundos | "El residente está revisando la solicitud." |
| 30-60 segundos | "Seguimos esperando la respuesta del residente." |
| 60-120 segundos | "Aún esperando respuesta, gracias por su paciencia." |
| > 120 segundos | "No hemos podido contactar al residente. ¿Desea dejar un mensaje o intentar más tarde?" |

**Implementación**:
```python
wait_seconds = (datetime.now() - auth_time).total_seconds()

if wait_seconds < 15:
    mensaje = "Estoy contactando al residente, un momento por favor."
elif wait_seconds < 30:
    mensaje = "El residente está revisando la solicitud."
elif wait_seconds < 60:
    mensaje = "Seguimos esperando la respuesta del residente."
elif wait_seconds < 120:
    mensaje = "Aún esperando respuesta, gracias por su paciencia."
else:
    estado = "timeout"
    mensaje = "No hemos podido contactar al residente..."
```

**Beneficio**: Visitante está informado sin preguntas molestas repetitivas.

---

## 4. Búsqueda Mejorada de Residentes

### Problema Resuelto
- Si visitante solo daba nombre sin apellido, sistema no sabía cómo proceder
- Falta de guía para obtener información completa

### Solución Implementada
**Endpoint modificado**: `POST /tools/buscar-residente`

**Nuevo campo en respuesta**: `necesita_mas_info` y `tipo_info_faltante`

**Escenario 1: Solo nombre**
```json
Request: {"nombre": "Juan"}

Response: {
  "encontrado": false,
  "necesita_mas_info": true,
  "tipo_info_faltante": "apellido",
  "result": "Necesito el apellido para poder buscar a esa persona. ¿Cuál es el apellido?"
}
```

**Escenario 2: Nombre completo sin match**
```json
Request: {"nombre": "Juan", "apellido": "Pérez"}

Response: {
  "encontrado": false,
  "necesita_mas_info": true,
  "tipo_info_faltante": "casa",
  "result": "No encontré a nadie con ese nombre. ¿Sabe el número de casa o apartamento?"
}
```

**Beneficio**: Sistema guía al visitante para proporcionar información correcta.

---

## 5. Direcciones e Instrucciones de Llegada

### Problema Resuelto
- Visitante autorizado no sabía cómo llegar a la casa dentro del condominio
- Se perdían buscando la dirección correcta

### Solución Implementada
**Migración nueva**: `database/migrations/003_add_address_to_residents.sql`

**Nuevos campos en tabla `residents`**:
```sql
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address_instructions TEXT;
```

**Ejemplo de uso**:
```sql
UPDATE residents
SET address_instructions = 'Segunda casa después de la piscina, lado derecho'
WHERE apartment = 'Casa 10';
```

**Respuesta al autorizar acceso**:
```json
{
  "estado": "autorizado",
  "direccion": "Segunda casa después de la piscina, lado derecho",
  "result": "El residente ha autorizado su ingreso. Para llegar: Segunda casa después de la piscina, lado derecho"
}
```

**El agente dice**:
> "Excelente, el residente autorizó su ingreso. Para llegar, es la segunda casa después de la piscina, lado derecho. Bienvenido."

**Beneficio**: Visitantes llegan directamente sin perderse.

---

## 6. Human in the Loop (Transferencia a Operador)

### Problema Resuelto
- Sistema no tenía respaldo cuando no podía resolver automáticamente
- Visitantes quedaban bloqueados en situaciones especiales
- Falta de escalamiento a humano

### Solución Implementada
**Endpoint nuevo**: `POST /tools/transferir-operador`

**Casos de uso**:
1. Visitante no proporciona información necesaria después de múltiples intentos
2. Residente no responde después de timeout (120 segundos)
3. Situación especial que requiere intervención humana
4. Visitante pide hablar con una persona

**Variables de entorno nuevas** (`.env.example`):
```bash
# Operador humano (Human in the Loop)
OPERATOR_PHONE=50688015665  # Teléfono del operador para transferencias
OPERATOR_TIMEOUT=120        # Tiempo de espera antes de ofrecer transferir
```

**Request**:
```bash
curl -X POST "$BASE_URL/tools/transferir-operador" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "Visitante no proporciona cédula",
    "nombre_visitante": "Juan Pérez",
    "apartamento": "Casa 10"
  }'
```

**Mensaje enviado al operador**:
```
🚨 *Transferencia de llamada*

Un visitante necesita asistencia:
👤 Visitante: Juan Pérez
🏠 Destino: Casa 10
📝 Motivo: Visitante no proporciona cédula

Por favor atienda la portería.
```

**Beneficio**: Siempre hay un respaldo humano cuando el sistema no puede resolver.

---

## Archivos Nuevos/Modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `src/services/voice/prompts.py` | NUEVO | Centraliza todos los prompts del sistema |
| `src/services/voice/ultravox_client.py` | MODIFICADO | Usa nuevo prompt centralizado |
| `src/services/voice/astersipvox_client.py` | MODIFICADO | Usa nuevo prompt centralizado |
| `src/api/routes/tools.py` | MODIFICADO | Múltiples mejoras en endpoints |
| `database/migrations/003_add_address_to_residents.sql` | NUEVO | Agrega campos de dirección a residents |
| `.env.example` | MODIFICADO | Agrega OPERATOR_PHONE y OPERATOR_TIMEOUT |
| `docs/FLUJO-AUTORIZACION.md` | MODIFICADO | Documentación actualizada con nuevas funcionalidades |
| `README.md` | MODIFICADO | Actualizado con nuevas features |
| `README-DESARROLLO.md` | MODIFICADO | Guía de desarrollo actualizada |

---

## Testing

### Test 1: System Prompt
```bash
# El agente NO debe leer código ni información técnica
# Debe comportarse profesionalmente
# Debe seguir el flujo definido en prompts.py
```

### Test 2: Mensaje WhatsApp Enriquecido
```bash
curl -X POST "http://localhost:8000/tools/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "Casa 10",
    "nombre_visitante": "Juan Pérez",
    "cedula": "123456789",
    "placa": "ABC123",
    "motivo_visita": "Entrega de paquete"
  }'

# Verificar mensaje en WhatsApp incluye todos los campos
```

### Test 3: Mensajes de Espera Contextuales
```bash
# 1. Notificar residente
curl -X POST "http://localhost:8000/tools/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10", "nombre_visitante": "Test", "cedula": "123"}'

# 2. Consultar inmediatamente (< 15s)
curl -X POST "http://localhost:8000/tools/estado-autorizacion" \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq '.mensaje'
# Esperado: "Estoy contactando al residente..."

# 3. Esperar 20 segundos y consultar
sleep 20
curl -X POST "http://localhost:8000/tools/estado-autorizacion" \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa 10"}' | jq '.mensaje'
# Esperado: "El residente está revisando la solicitud."
```

### Test 4: Búsqueda con Apellido Faltante
```bash
curl -X POST "http://localhost:8000/tools/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Juan"}' | jq

# Esperado:
# {
#   "encontrado": false,
#   "necesita_mas_info": true,
#   "tipo_info_faltante": "apellido",
#   "result": "Necesito el apellido para poder buscar..."
# }
```

### Test 5: Direcciones
```bash
# 1. Agregar dirección a un residente en Supabase
UPDATE residents
SET address_instructions = 'Segunda casa después de la piscina'
WHERE apartment = 'Casa 10';

# 2. Autorizar acceso y verificar que incluye dirección
# Respuesta debe incluir campo "direccion"
```

### Test 6: Transferencia a Operador
```bash
curl -X POST "http://localhost:8000/tools/transferir-operador" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "Timeout esperando respuesta",
    "nombre_visitante": "Juan Pérez",
    "apartamento": "Casa 10"
  }'

# Esperado: transferido = true
# Verificar: WhatsApp al OPERATOR_PHONE con notificación
```

---

## Impacto en la Experiencia del Usuario

### Para el Visitante
- Conversación más natural y profesional
- Sabe qué está pasando durante la espera
- Recibe instrucciones claras para llegar
- Puede hablar con un humano si es necesario

### Para el Residente
- Recibe toda la información del visitante
- Puede tomar decisión informada
- No necesita hacer preguntas adicionales

### Para el Operador
- Notificaciones claras cuando se necesita intervención
- Contexto completo de la situación
- Respaldo cuando el sistema no puede resolver

---

## Métricas de Éxito

- Reducción de preguntas repetitivas al visitante
- Aumento en tasa de autorización (residente más informado)
- Reducción de visitantes perdidos en el condominio
- Transferencias a operador solo en casos necesarios (< 5%)
- Satisfacción del usuario medida en encuestas

---

## Próximos Pasos

1. Monitorear logs para detectar casos edge no contemplados
2. Recopilar feedback de residentes y visitantes
3. Ajustar timeouts según datos reales de respuesta
4. Implementar analytics dashboard para métricas
5. Considerar notificaciones por múltiples canales (SMS, llamada)

---

**Versión del documento**: 1.0
**Fecha**: 2025-12-03
**Autor**: Equipo de desarrollo SITNOVA

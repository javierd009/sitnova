# Plan de Mejoras - Agente Portero Virtual SITNOVA

## Estado: COMPLETADO ✅ (2025-12-03)

Todas las fases del plan han sido implementadas exitosamente. Ver documento detallado: `docs/MEJORAS-AGENTE-2025-12-03.md`

---

## Problemas Identificados (RESUELTOS)

### 1. Agente Leyendo Código (CRÍTICO) ✅ RESUELTO
**Síntoma**: El agente de voz dice frases como "System, print no sé qué entre comillas"
**Causa probable**: El system prompt de Ultravox/AsterSIPVox está recibiendo contenido incorrecto o hay algún debug activo que está siendo leído.
**Solución**: System prompt profesional centralizado en `src/services/voice/prompts.py` con reglas estrictas.

### 2. Búsqueda por Nombre Incompleta ✅ RESUELTO
**Síntoma**: Si el visitante solo da nombre sin apellido, el sistema no sabe cómo proceder
**Requerimiento**: Debe pedir apellido si solo tienen nombre, y casa si tampoco tienen apellido
**Solución**: Endpoint `/tools/buscar-residente` ahora pide apellido y guía al agente.

### 3. Información del Visitante Incompleta ✅ RESUELTO
**Actual**: Solo se pide nombre y casa
**Requerimiento**: Debe pedir siempre:
- Nombre completo
- Número de cédula
- Motivo de la visita
- Esta info debe llegar al residente por WhatsApp
**Solución**: Mensaje WhatsApp enriquecido incluye todos los campos. Endpoint `/tools/notificar-residente` acepta `motivo_visita`.

### 4. Direcciones de Casas ✅ RESUELTO
**Síntoma**: Una vez autorizado, el visitante no sabe cómo llegar
**Requerimiento**: Agregar campo de dirección para indicar cómo llegar a la casa
**Solución**: Migración `003_add_address_to_residents.sql` agrega campos `address` y `address_instructions`. Se incluyen al autorizar.

### 5. Mensajes de Espera Molestos ✅ RESUELTO
**Síntoma**: El agente pregunta "¿sigues ahí?" constantemente
**Requerimiento**:
- Indicar que se está contactando al residente
- Si no contesta después de X tiempo, indicar que intente comunicarse directamente
**Solución**: Endpoint `/tools/estado-autorizacion` ahora da mensajes contextuales según tiempo transcurrido (< 15s, 15-30s, 30-60s, > 120s).

### 6. Human in the Loop ✅ RESUELTO
**Requerimiento**: Si el sistema no logra resolver, debe poder transferir a un operador humano
**Solución**: Endpoint `/tools/transferir-operador` notifica al operador por WhatsApp. Variables `OPERATOR_PHONE` y `OPERATOR_TIMEOUT` agregadas.

---

## Plan de Implementación

### FASE 1: Corregir System Prompt (Crítico)

#### 1.1 Revisar y limpiar system prompt
**Archivo**: `src/services/voice/ultravox_client.py`

Crear un system prompt profesional y claro:

```python
SYSTEM_PROMPT_PORTERO = """Eres el asistente de seguridad virtual de un condominio residencial en Costa Rica.

TU PERSONALIDAD:
- Profesional y amable
- Hablas en español costarricense
- Eres conciso y claro
- No das explicaciones largas innecesarias

INFORMACIÓN QUE DEBES RECOPILAR DEL VISITANTE:
1. Nombre completo del visitante
2. Número de cédula
3. A quién visita (nombre Y/O número de casa)
4. Motivo de la visita

FLUJO DE CONVERSACIÓN:
1. Saludar: "Buenas, bienvenido al condominio. ¿A quién viene a visitar?"
2. Si da solo nombre sin apellido: "¿Me puede dar el apellido también?"
3. Si no sabe el número de casa: "¿Sabe el número de casa o apartamento?"
4. Pedir nombre: "¿Me puede dar su nombre completo, por favor?"
5. Pedir cédula: "¿Me puede dar su número de cédula?"
6. Pedir motivo: "¿Cuál es el motivo de su visita?"
7. Confirmar: "Perfecto, déjeme notificar al residente. Un momento por favor."

MIENTRAS ESPERA RESPUESTA:
- NO preguntar "¿sigue ahí?" repetidamente
- Decir: "Estoy contactando al residente, por favor aguarde un momento"
- Si pasan más de 30 segundos: "El residente aún no responde, seguimos intentando"
- Si pasan más de 60 segundos: "No hemos podido contactar al residente. ¿Desea dejar un mensaje o intentar más tarde?"

SI EL VISITANTE NO COLABORA:
- Mantener la calma y profesionalismo
- Si no proporciona información necesaria: "Sin esta información no puedo procesar su ingreso"
- Ofrecer alternativa: "¿Desea que le comunique con un operador humano?"

NUNCA:
- Leer código o información técnica
- Dar información personal de residentes
- Permitir acceso sin verificación
- Inventar información

RESPUESTAS DEL RESIDENTE:
- "SI" o similar = Autorizado - Abrir portón
- "NO" o similar = Denegado - Indicar que no puede ingresar
- Mensaje personalizado = Transmitir el mensaje al visitante
"""
```

#### 1.2 Archivo nuevo: `src/services/voice/prompts.py`
Centralizar todos los prompts del sistema para fácil mantenimiento.

### FASE 2: Mejorar Flujo de Búsqueda

#### 2.1 Modificar endpoint `/tools/buscar-residente`
**Archivo**: `src/api/routes/tools.py`

Mejorar respuestas para guiar al agente:

```python
# Si solo dan nombre (sin apellido)
if nombre_clean and not apellido_clean:
    return {
        "encontrado": False,
        "necesita_mas_info": True,
        "tipo_info_faltante": "apellido",
        "result": "Necesito el apellido para poder buscar a esa persona. ¿Cuál es el apellido?"
    }

# Si no hay match y no saben la casa
if not matches:
    return {
        "encontrado": False,
        "necesita_mas_info": True,
        "tipo_info_faltante": "casa",
        "result": "No encontré a nadie con ese nombre. ¿Sabe el número de casa o apartamento?"
    }
```

### FASE 3: Agregar Información del Visitante

#### 3.1 Modificar notificación WhatsApp
**Archivo**: `src/api/routes/tools.py`

Agregar parámetros:
- `motivo_visita: Optional[str]`

Modificar mensaje:
```python
mensaje_wa = (
    f"🚪 *Visita en portería*\n\n"
    f"Hay una persona esperando en la entrada:\n"
    f"👤 *Nombre:* {visitante}\n"
    f"🪪 *Cédula:* {cedula or 'No proporcionada'}\n"
    f"📝 *Motivo:* {motivo or 'No especificado'}\n"
    f"🏠 *Destino:* {apt}\n"
)
if visitor_placa:
    mensaje_wa += f"🚗 *Placa:* {visitor_placa}\n"

mensaje_wa += (
    f"\nResponda *SI* para autorizar o *NO* para denegar.\n"
    f"También puede enviar un mensaje para el visitante."
)
```

### FASE 4: Agregar Direcciones

#### 4.1 Migración de base de datos
**Archivo nuevo**: `database/migrations/003_add_address_to_residents.sql`

```sql
-- Agregar campo de dirección a residents
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE residents ADD COLUMN IF NOT EXISTS address_instructions TEXT;

-- Comentario
COMMENT ON COLUMN residents.address IS 'Dirección física de la casa/apartamento';
COMMENT ON COLUMN residents.address_instructions IS 'Instrucciones para llegar (ej: "Segunda casa después de la piscina")';
```

#### 4.2 Modificar respuesta de autorización
**Archivo**: `src/api/routes/tools.py`

Incluir instrucciones de dirección cuando el acceso es autorizado:

```python
if status == "autorizado":
    # Buscar dirección del residente
    resident_info = supabase.table("residents").select(
        "address, address_instructions"
    ).eq("apartment", apt).single().execute()

    direccion = resident_info.data.get("address_instructions") if resident_info.data else None

    mensaje = f"El residente ha autorizado su ingreso."
    if direccion:
        mensaje += f" Para llegar: {direccion}"

    return {
        "estado": "autorizado",
        "direccion": direccion,
        "result": mensaje
    }
```

### FASE 5: Mejorar Mensajes de Espera

#### 5.1 Nuevo endpoint de polling con contexto
**Archivo**: `src/api/routes/tools.py`

```python
@router.api_route("/estado-autorizacion", methods=["GET", "POST"])
async def estado_autorizacion(...):
    """
    Consulta el estado de autorización.

    Incluye mensajes contextuales según el tiempo de espera:
    - < 15 seg: "Contactando al residente..."
    - 15-30 seg: "El residente está revisando la solicitud..."
    - 30-60 seg: "Aún esperando respuesta del residente..."
    - > 60 seg: "No hemos podido contactar al residente"
    """
    # Calcular tiempo de espera
    auth_time = datetime.fromisoformat(auth.get("timestamp"))
    wait_seconds = (datetime.now() - auth_time).total_seconds()

    if wait_seconds < 15:
        wait_message = "Estoy contactando al residente, un momento por favor."
    elif wait_seconds < 30:
        wait_message = "El residente está revisando la solicitud."
    elif wait_seconds < 60:
        wait_message = "Seguimos esperando la respuesta del residente."
    else:
        wait_message = "No hemos podido contactar al residente. ¿Desea dejar un mensaje o intentar más tarde?"
```

### FASE 6: Human in the Loop

#### 6.1 Nuevo endpoint para transferir a operador
**Archivo**: `src/api/routes/tools.py`

```python
@router.post("/transferir-operador")
async def transferir_operador(
    request: Request,
    motivo: Optional[str] = Query(None),
    nombre_visitante: Optional[str] = Query(None),
    apartamento: Optional[str] = Query(None),
):
    """
    Transfiere la llamada a un operador humano.

    Casos de uso:
    - Visitante no proporciona información necesaria
    - Residente no contesta después de timeout
    - Situación especial que requiere intervención humana
    """
    # Notificar al operador por WhatsApp
    operador_phone = settings.operator_phone  # Nueva config

    mensaje = (
        f"🚨 *Transferencia de llamada*\n\n"
        f"Un visitante necesita asistencia:\n"
        f"👤 Visitante: {nombre_visitante or 'No identificado'}\n"
        f"🏠 Destino: {apartamento or 'No especificado'}\n"
        f"📝 Motivo: {motivo or 'No especificado'}\n\n"
        f"Por favor atienda la portería."
    )

    # Enviar notificación
    # ...

    return {
        "transferido": True,
        "result": "He notificado al operador. En unos momentos le atenderá una persona."
    }
```

#### 6.2 Agregar configuración de operador
**Archivo**: `src/config/settings.py`

```python
# Operador humano
operator_phone: str = ""  # Teléfono del operador de respaldo
operator_timeout: int = 120  # Segundos antes de ofrecer transferir
```

---

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `src/services/voice/prompts.py` | NUEVO - Centralizar prompts |
| `src/services/voice/ultravox_client.py` | Usar nuevo prompt |
| `src/services/voice/astersipvox_client.py` | Usar nuevo prompt |
| `src/api/routes/tools.py` | Múltiples mejoras |
| `src/config/settings.py` | Agregar config operador |
| `database/migrations/003_add_address.sql` | NUEVO - Migración |

---

## Orden de Implementación (COMPLETADO)

1. ✅ **FASE 1**: System prompt (resolver problema de leer código)
2. ✅ **FASE 3**: Información del visitante (mejorar WhatsApp)
3. ✅ **FASE 5**: Mensajes de espera (mejorar UX)
4. ✅ **FASE 2**: Búsqueda por nombre (mejorar flujo)
5. ✅ **FASE 4**: Direcciones (feature nuevo)
6. ✅ **FASE 6**: Human in the loop (respaldo)

**Todas las fases completadas el 2025-12-03**

---

## Notas de Seguridad

- NO incluir código o información técnica en prompts
- NO revelar información personal de residentes
- Validar todas las entradas antes de procesarlas
- Mantener logs de todas las interacciones para auditoría

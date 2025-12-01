# 🚀 Configurar Google Gemini para SITNOVA

## Paso 1: Obtener API Key de Gemini

1. **Ir a Google AI Studio**:
   ```
   https://aistudio.google.com/app/apikey
   ```

2. **Crear API Key**:
   - Click en "Get API key"
   - Click en "Create API key in new project" (o seleccionar proyecto existente)
   - Copiar la API key que aparece

3. **Guardar la API Key**:
   ```
   AIzaSy... (comienza con AIzaSy)
   ```

## Paso 2: Configurar en .env

Editar el archivo `.env`:

```bash
nano .env
```

Agregar o modificar estas líneas:

```bash
# API de IA - Google Gemini
GOOGLE_API_KEY=AIzaSy_tu_api_key_aqui

# Modelo a usar (opcional, por defecto gemini-pro)
LLM_MODEL=gemini-2.0-flash-exp  # El más nuevo y gratis
# O usar: gemini-pro, gemini-pro-vision
```

## Paso 3: Verificar configuración

```bash
python -c "
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash-exp')
response = llm.invoke('Hola, responde solo: OK')
print('✅ Gemini funciona:',response.content)
"
```

## Modelos Disponibles (Gratis)

| Modelo | Descripción | Límite Gratis |
|--------|-------------|---------------|
| `gemini-2.0-flash-exp` | Más nuevo, muy rápido | 10 RPM, 1500 RPD |
| `gemini-1.5-flash` | Rápido, eficiente | 15 RPM, 1500 RPD |
| `gemini-1.5-pro` | Más capaz, context largo | 2 RPM, 50 RPD |
| `gemini-pro` | Estable | 60 RPM |

**Recomendación**: `gemini-2.0-flash-exp` (el más nuevo)

RPM = Requests Per Minute
RPD = Requests Per Day

## Ventajas de Gemini

✅ **Tier gratuito muy generoso** (vs Anthropic/OpenAI)
✅ **Muy rápido** (especialmente Flash)
✅ **Multimodal** (texto + imágenes)
✅ **Context window grande** (hasta 2M tokens en Pro)
✅ **Integración perfecta con LangChain**

## Código de Integración

El código ya está preparado para usar Gemini. Solo necesitas:

1. API Key en `.env`
2. ¡Listo!

El sistema detecta automáticamente `GOOGLE_API_KEY` y usa Gemini.

## Troubleshooting

### Error: "API key not valid"
- Verifica que copiaste la key completa
- Debe empezar con `AIzaSy`
- No debe tener espacios

### Error: "Resource exhausted"
- Has excedido el límite gratuito
- Espera unos minutos
- O usa modelo con mayor límite

### Error: "Module not found: google.generativeai"
```bash
pip install langchain-google-genai
```

## Comparación de APIs

| Característica | Gemini | Anthropic | OpenAI |
|----------------|--------|-----------|---------|
| **Tier gratuito** | ✅ Generoso | ❌ No | ❌ No |
| **Precio** | Muy barato | Medio | Caro |
| **Velocidad** | Muy rápido | Rápido | Medio |
| **Calidad** | Excelente | Excelente | Excelente |
| **Context** | Hasta 2M | Hasta 200K | Hasta 128K |

**Conclusión**: Para SITNOVA (que necesita hacer muchas requests), **Gemini es la mejor opción** por costo/beneficio.

---

**Siguiente paso**: Probar el sistema con `python test_simple.py`

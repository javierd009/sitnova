#!/bin/bash
# Script de diagnóstico SITNOVA
# Identifica por qué el agente no espera respuestas

echo "========================================="
echo "DIAGNÓSTICO SITNOVA - $(date)"
echo "========================================="

echo ""
echo "📋 1. VARIABLES DE ENTORNO"
echo "   SUPABASE_URL: ${SUPABASE_URL:-❌ NO CONFIGURADA}"
if [ -n "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    echo "   SUPABASE_SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY:0:30}... (✅ configurada, ${#SUPABASE_SERVICE_ROLE_KEY} chars)"
else
    echo "   SUPABASE_SERVICE_ROLE_KEY: ❌ NO CONFIGURADA"
fi
echo "   EVOLUTION_API_URL: ${EVOLUTION_API_URL:-❌ NO CONFIGURADA}"
if [ -n "$EVOLUTION_API_KEY" ]; then
    echo "   EVOLUTION_API_KEY: ${EVOLUTION_API_KEY:0:20}... (✅ configurada)"
else
    echo "   EVOLUTION_API_KEY: ❌ NO CONFIGURADA"
fi
echo "   EVOLUTION_INSTANCE_NAME: ${EVOLUTION_INSTANCE_NAME:-❌ NO CONFIGURADA}"
echo "   OPERATOR_PHONE: ${OPERATOR_PHONE:-❌ NO CONFIGURADA}"

echo ""
echo "🐳 2. CONTENEDORES DOCKER"
docker ps --filter "name=sitnova" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🏥 3. HEALTH CHECK API"
echo "   Testing: https://api.sitnova.integratec-ia.com/health"
curl -s https://api.sitnova.integratec-ia.com/health | jq . || echo "   ❌ Health check falló"

echo ""
echo "📝 4. ÚLTIMOS 30 LOGS (buscando errores críticos)"
docker logs sitnova-backend --tail 30 2>&1 | grep -i "error\|supabase\|memoria\|pending_authorization" || echo "   No se encontraron errores evidentes"

echo ""
echo "🔍 5. TEST CREAR AUTORIZACIÓN (notificar-residente)"
echo "   Enviando notificación de prueba..."
response=$(curl -s -X POST https://api.sitnova.integratec-ia.com/tools/notificar-residente \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "Casa DIAG",
    "nombre_visitante": "Test Diagnostico",
    "cedula": "999999999",
    "motivo_visita": "Prueba sistema"
  }')
echo "$response" | jq .
enviado=$(echo "$response" | jq -r '.enviado')
if [ "$enviado" = "true" ]; then
    echo "   ✅ Notificación creada"
else
    echo "   ❌ Falló crear notificación"
fi

echo ""
echo "⏳ Esperando 2 segundos..."
sleep 2

echo ""
echo "🔎 6. TEST BUSCAR AUTORIZACIÓN (estado-autorizacion)"
echo "   Buscando autorización recién creada..."
response=$(curl -s -X POST https://api.sitnova.integratec-ia.com/tools/estado-autorizacion \
  -H "Content-Type: application/json" \
  -d '{"apartamento": "Casa DIAG"}')
echo "$response" | jq .
estado=$(echo "$response" | jq -r '.estado')

echo ""
echo "🎯 RESULTADO DEL DIAGNÓSTICO:"
echo "   Estado encontrado: $estado"

if [ "$estado" = "pendiente" ]; then
    echo "   ✅✅✅ SISTEMA FUNCIONANDO CORRECTAMENTE"
    echo "   La autorización se creó y se puede buscar."
    echo ""
    echo "   ➡️  PROBLEMA PROBABLE: AsterSIPVox no está llamando a estado_autorizacion"
    echo "       SOLUCIÓN: Actualizar system prompt en AsterSIPVox (ver SOLUCION-PROBLEMAS-AGENTE.md)"
elif [ "$estado" = "no_encontrado" ]; then
    echo "   ❌❌❌ PROBLEMA CRÍTICO: AUTORIZACIÓN NO SE GUARDÓ"
    echo "   La autorización se creó pero NO se puede buscar."
    echo ""
    echo "   ➡️  CAUSA MÁS PROBABLE: Supabase NO conectado"
    echo "       Las autorizaciones se guardan en MEMORIA pero se buscan en Supabase"
    echo ""
    echo "   SOLUCIÓN:"
    echo "   1. Verificar que SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY estén en .env"
    echo "   2. Verificar que la tabla pending_authorizations exista en Supabase"
    echo "   3. Reiniciar el contenedor: docker restart sitnova-backend"
else
    echo "   ⚠️  Estado inesperado: $estado"
fi

echo ""
echo "📊 7. VERIFICACIÓN SUPABASE EN LOGS"
echo "   Buscando evidencia de conexión Supabase..."
docker logs sitnova-backend --tail 200 2>&1 | grep -i "supabase" | head -10

echo ""
echo "   Buscando si usa MEMORIA (fallback):"
docker logs sitnova-backend --tail 200 2>&1 | grep -i "memoria" | head -5

echo ""
echo "========================================="
echo "DIAGNÓSTICO COMPLETO"
echo "========================================="
echo ""
echo "📄 Para más información, ver: DIAGNOSTICO-URGENTE.md"
echo ""

#!/bin/bash
# Test de endpoints del agente de voz SITNOVA
# Ejecutar: chmod +x tests/test_voice_endpoints.sh && ./tests/test_voice_endpoints.sh

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# URL base (ajustar según tu servidor)
BASE_URL="${BASE_URL:-https://api.sitnova.integratec-ia.com}"
TOOLS_URL="$BASE_URL/tools"

echo "========================================="
echo "🧪 TESTS DE ENDPOINTS - SITNOVA"
echo "========================================="
echo "URL: $TOOLS_URL"
echo ""

# Test 1: Buscar residente por nombre
echo -e "${YELLOW}Test 1: Buscar residente por nombre${NC}"
echo "POST $TOOLS_URL/buscar-residente"
curl -X POST "$TOOLS_URL/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "Daisy"
  }' | jq '.'
echo ""
echo ""

# Test 2: Buscar residente por casa
echo -e "${YELLOW}Test 2: Buscar residente por número de casa${NC}"
echo "POST $TOOLS_URL/buscar-residente"
curl -X POST "$TOOLS_URL/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "10"
  }' | jq '.'
echo ""
echo ""

# Test 3: Verificar pre-autorización
echo -e "${YELLOW}Test 3: Verificar pre-autorización${NC}"
echo "POST $TOOLS_URL/verificar-preautorizacion"
curl -X POST "$TOOLS_URL/verificar-preautorizacion" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan Perez",
    "cedula": "123456789"
  }' | jq '.'
echo ""
echo ""

# Test 4: Notificar residente (con TODOS los campos)
echo -e "${YELLOW}Test 4: Notificar residente con todos los datos${NC}"
echo "POST $TOOLS_URL/notificar-residente"
curl -X POST "$TOOLS_URL/notificar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "10",
    "nombre_visitante": "Maria Rodriguez",
    "cedula": "987654321",
    "motivo_visita": "visita personal"
  }' | jq '.'
echo ""
echo ""

# Test 5: Estado de autorización
echo -e "${YELLOW}Test 5: Verificar estado de autorización${NC}"
echo "POST $TOOLS_URL/estado-autorizacion"
curl -X POST "$TOOLS_URL/estado-autorizacion" \
  -H "Content-Type: application/json" \
  -d '{
    "apartamento": "10"
  }' | jq '.'
echo ""
echo ""

# Test 6: Abrir portón
echo -e "${YELLOW}Test 6: Abrir portón${NC}"
echo "POST $TOOLS_URL/abrir-porton"
curl -X POST "$TOOLS_URL/abrir-porton" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "visitante autorizado"
  }' | jq '.'
echo ""
echo ""

# Test 7: Transferir a operador
echo -e "${YELLOW}Test 7: Transferir a operador${NC}"
echo "POST $TOOLS_URL/transferir-operador"
curl -X POST "$TOOLS_URL/transferir-operador" \
  -H "Content-Type: application/json" \
  -d '{
    "motivo": "no se pudo contactar al residente",
    "nombre_visitante": "Maria Rodriguez",
    "apartamento": "10"
  }' | jq '.'
echo ""
echo ""

# Test 8: Fuzzy matching (nombre con error)
echo -e "${YELLOW}Test 8: Fuzzy matching - nombre con error${NC}"
echo "POST $TOOLS_URL/buscar-residente"
curl -X POST "$TOOLS_URL/buscar-residente" \
  -H "Content-Type: application/json" \
  -d '{
    "condominium_id": "default-condo-id",
    "query": "Daisy Hernandos"
  }' | jq '.'
echo ""
echo ""

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ Tests completados${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Notas:"
echo "- Si no tienes jq instalado: brew install jq (Mac) o apt-get install jq (Linux)"
echo "- Para cambiar la URL: BASE_URL=http://localhost:8000 ./tests/test_voice_endpoints.sh"
echo ""

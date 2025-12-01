#!/bin/bash
# ============================================
# SITNOVA - Script de Deployment
# ============================================

set -e

echo "🚀 SITNOVA Deployment Script"
echo "=============================="

# Verificar que existe .env.prod
if [ ! -f .env.prod ]; then
    echo "❌ Error: .env.prod no existe"
    echo "   Copia .env.prod.example a .env.prod y configura los valores"
    exit 1
fi

# Cargar variables
source .env.prod

# Crear directorios necesarios
echo "📁 Creando directorios..."
mkdir -p nginx/ssl data/images data/logs models

# Generar certificados SSL autofirmados si no existen (para desarrollo)
if [ ! -f nginx/ssl/fullchain.pem ]; then
    echo "🔐 Generando certificados SSL de desarrollo..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -subj "/C=CR/ST=SanJose/L=SanJose/O=SITNOVA/CN=${DOMAIN:-localhost}"
fi

# Build de imagenes
echo "🔨 Construyendo imagenes Docker..."
docker-compose -f docker-compose.prod.yml build

# Detener servicios existentes
echo "🛑 Deteniendo servicios existentes..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker-compose -f docker-compose.prod.yml up -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando que los servicios inicien..."
sleep 10

# Verificar salud
echo "🏥 Verificando servicios..."
docker-compose -f docker-compose.prod.yml ps

# Health checks
echo ""
echo "📊 Health Checks:"
echo "-----------------"

# Backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend: OK"
else
    echo "❌ Backend: FAILED"
fi

# Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: OK"
else
    echo "❌ Frontend: FAILED"
fi

# Redis
if docker exec sitnova-redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: OK"
else
    echo "❌ Redis: FAILED"
fi

# Evolution
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Evolution API: OK"
else
    echo "⚠️  Evolution API: Starting..."
fi

echo ""
echo "=============================="
echo "✅ Deployment completado!"
echo ""
echo "URLs:"
echo "  - Frontend: https://${DOMAIN:-localhost}"
echo "  - API: https://api.${DOMAIN:-localhost}"
echo "  - Evolution: https://evolution.${DOMAIN:-localhost}"
echo ""
echo "Para ver logs: docker-compose -f docker-compose.prod.yml logs -f"

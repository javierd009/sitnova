#!/bin/bash

# ============================================
# SITNOVA - Setup Script
# Script de configuración inicial del proyecto
# ============================================

set -e  # Exit on error

echo "🚀 SITNOVA - Setup Inicial"
echo "================================"
echo ""

# ============================================
# 1. Verificar Python
# ============================================
echo "📦 Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    echo "Instala Python 3.11+ desde https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python $PYTHON_VERSION encontrado"
echo ""

# ============================================
# 2. Crear virtualenv
# ============================================
echo "🐍 Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtualenv creado"
else
    echo "⚠️  Virtualenv ya existe"
fi
echo ""

# ============================================
# 3. Activar virtualenv e instalar deps
# ============================================
echo "📥 Instalando dependencias..."
source venv/bin/activate

pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt

echo "✅ Dependencias instaladas"
echo ""

# ============================================
# 4. Crear directorios necesarios
# ============================================
echo "📁 Creando directorios..."
mkdir -p data/images data/logs models

echo "✅ Directorios creados"
echo ""

# ============================================
# 5. Configurar .env
# ============================================
echo "⚙️  Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Archivo .env creado desde .env.example"
    echo "⚠️  IMPORTANTE: Edita .env con tus credenciales"
else
    echo "⚠️  .env ya existe, no se sobrescribe"
fi
echo ""

# ============================================
# 6. Verificar Docker (opcional)
# ============================================
echo "🐳 Verificando Docker..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    echo "✅ Docker $DOCKER_VERSION encontrado"

    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f4 | tr -d ',')
        echo "✅ Docker Compose $COMPOSE_VERSION encontrado"
    else
        echo "⚠️  Docker Compose no encontrado (opcional)"
    fi
else
    echo "⚠️  Docker no encontrado (opcional)"
fi
echo ""

# ============================================
# 7. Verificar Redis (opcional)
# ============================================
echo "🔴 Verificando Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis está corriendo"
    else
        echo "⚠️  Redis instalado pero no está corriendo"
        echo "   Inicia con: redis-server"
    fi
else
    echo "⚠️  Redis no encontrado"
    echo "   Instala con: brew install redis (macOS)"
    echo "   O usa Docker: docker run -d -p 6379:6379 redis:7-alpine"
fi
echo ""

# ============================================
# 8. Descargar modelo YOLO (opcional)
# ============================================
echo "🤖 Modelos de YOLO..."
if [ ! -f "models/yolov8n.pt" ]; then
    echo "⚠️  Modelo YOLOv8n no encontrado"
    echo "   Descarga manual:"
    echo "   wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -P models/"
else
    echo "✅ Modelo YOLOv8n encontrado"
fi
echo ""

# ============================================
# Resumen
# ============================================
echo "================================"
echo "✅ Setup completado!"
echo "================================"
echo ""
echo "📋 Próximos pasos:"
echo ""
echo "1. Edita .env con tus credenciales:"
echo "   - ANTHROPIC_API_KEY o OPENAI_API_KEY"
echo "   - SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY"
echo "   - HIKVISION_HOST y HIKVISION_PASSWORD"
echo "   - Etc."
echo ""
echo "2. Configura Supabase:"
echo "   - Sigue database/SUPABASE-SETUP.md"
echo ""
echo "3. Inicia la aplicación:"
echo "   source venv/bin/activate"
echo "   uvicorn src.api.main:app --reload"
echo ""
echo "   O con Docker:"
echo "   docker-compose up --build"
echo ""
echo "4. Accede a:"
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/health"
echo ""
echo "📚 Documentación completa: README-DESARROLLO.md"
echo ""

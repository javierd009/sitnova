#!/bin/bash
# ============================================
# SITNOVA - SSL Setup Script
# Obtiene certificados Let's Encrypt
# ============================================

set -e

echo "==================================="
echo "SITNOVA - SSL Certificate Setup"
echo "==================================="

# Verificar que existe .env.prod
if [ ! -f .env.prod ]; then
    echo "Error: .env.prod no existe"
    echo "Copia .env.prod.example y configura DOMAIN y EMAIL"
    exit 1
fi

# Cargar variables
source .env.prod

# Verificar variables requeridas
if [ -z "$DOMAIN" ]; then
    echo "Error: DOMAIN no esta configurado en .env.prod"
    exit 1
fi

if [ -z "$SSL_EMAIL" ]; then
    echo "Error: SSL_EMAIL no esta configurado en .env.prod"
    echo "Agrega: SSL_EMAIL=tu@email.com"
    exit 1
fi

echo ""
echo "Dominio: $DOMAIN"
echo "Email: $SSL_EMAIL"
echo ""

# Crear directorios
echo "[1/5] Creando directorios..."
mkdir -p certbot/www certbot/conf nginx/ssl

# Verificar que nginx esta usando config inicial
echo "[2/5] Verificando nginx config..."
if [ ! -f nginx/nginx.conf ]; then
    cp nginx/nginx.initial.conf nginx/nginx.conf
    echo "Copiado nginx.initial.conf"
fi

# Asegurar que los servicios estan corriendo
echo "[3/5] Iniciando servicios..."
docker-compose -f docker-compose.cloud.yml up -d nginx

# Esperar a que nginx este listo
sleep 5

# Verificar que el dominio responde
echo "[4/5] Verificando conectividad..."
if ! curl -s "http://$DOMAIN/.well-known/acme-challenge/test" > /dev/null 2>&1; then
    echo ""
    echo "Advertencia: No se pudo conectar a http://$DOMAIN"
    echo "Asegurate que:"
    echo "  1. El DNS apunta a este servidor"
    echo "  2. Los puertos 80 y 443 estan abiertos"
    echo ""
    read -p "Continuar de todos modos? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Obtener certificados
echo "[5/5] Obteniendo certificados SSL..."
docker run --rm \
    -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    -d "$DOMAIN" \
    -d "api.$DOMAIN" \
    -d "admin.$DOMAIN" \
    -d "evolution.$DOMAIN" \
    --email "$SSL_EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal

# Verificar que los certificados existen
if [ ! -f "certbot/conf/live/$DOMAIN/fullchain.pem" ]; then
    echo ""
    echo "Error: No se pudieron obtener los certificados"
    echo "Revisa los logs arriba para mas detalles"
    exit 1
fi

# Copiar certificados
echo ""
echo "Copiando certificados..."
cp "certbot/conf/live/$DOMAIN/fullchain.pem" nginx/ssl/
cp "certbot/conf/live/$DOMAIN/privkey.pem" nginx/ssl/

# Cambiar a config con SSL
echo "Activando SSL..."
cp nginx/nginx.prod.conf nginx/nginx.conf

# Reiniciar nginx
echo "Reiniciando nginx..."
docker-compose -f docker-compose.cloud.yml restart nginx

echo ""
echo "==================================="
echo "SSL configurado exitosamente!"
echo "==================================="
echo ""
echo "URLs disponibles:"
echo "  - https://$DOMAIN (Frontend)"
echo "  - https://api.$DOMAIN (API)"
echo "  - https://evolution.$DOMAIN (WhatsApp)"
echo ""
echo "Los certificados se renovaran automaticamente"
echo "via el contenedor certbot"
echo ""

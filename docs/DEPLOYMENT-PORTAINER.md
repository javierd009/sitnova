# SITNOVA - Guia de Deployment con Portainer

## Arquitectura Hibrida

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUD (Contabo ~$14/mes)                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌───────────────┐  │
│  │ Nginx   │  │ Frontend │  │ Backend │  │ Evolution API │  │
│  │ (proxy) │  │ Next.js  │  │ FastAPI │  │  (WhatsApp)   │  │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └───────┬───────┘  │
│       │            │             │               │          │
│       └────────────┴──────┬──────┴───────────────┘          │
│                           │                                 │
│                     ┌─────┴─────┐                           │
│                     │   Redis   │                           │
│                     └───────────┘                           │
└─────────────────────────────────────────────────────────────┘
                            │
                     HTTPS/WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                  LOCAL (Condominio)                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ OCR Service │  │ Sync Service │  │ Redis Local       │   │
│  │ YOLO+EasyOCR│  │              │  │ (cache)           │   │
│  └──────┬──────┘  └──────────────┘  └───────────────────┘   │
│         │                                                   │
│    ┌────┴────┐                                              │
│    │ Camaras │  Hikvision, FreePBX, etc.                    │
│    └─────────┘                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Parte 1: Deployment en Cloud (Contabo)

### Prerequisitos

- Servidor Contabo con Portainer instalado
- Dominio apuntando al servidor (ej: `sitnova.com`)
- Acceso SSH al servidor

### Paso 1: Preparar archivos en el servidor

```bash
# Conectar por SSH
ssh root@tu-servidor-contabo

# Crear directorio del proyecto
mkdir -p /opt/sitnova
cd /opt/sitnova

# Clonar repositorio (o subir archivos)
git clone https://tu-repo.git .
# O usar SCP para subir archivos
```

### Paso 2: Configurar variables de entorno

```bash
# Copiar template
cp .env.prod.example .env.prod

# Editar con tus valores
nano .env.prod
```

**Variables criticas a configurar:**

```env
# Domain
DOMAIN=tu-dominio.com

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# LLM
LLM_PROVIDER=google
GOOGLE_API_KEY=AIza...

# Evolution API
EVOLUTION_API_KEY=tu-key-segura

# Frontend
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=https://api.tu-dominio.com
```

### Paso 3: Deployment inicial (sin SSL)

```bash
# Usar config nginx inicial (HTTP only)
cp nginx/nginx.initial.conf nginx/nginx.conf

# Crear directorios necesarios
mkdir -p data/images data/logs certbot/www certbot/conf

# Build y start
docker-compose -f docker-compose.cloud.yml up -d --build
```

### Paso 4: Verificar servicios

```bash
# Ver estado
docker-compose -f docker-compose.cloud.yml ps

# Ver logs
docker-compose -f docker-compose.cloud.yml logs -f

# Health check
curl http://localhost/health
curl http://localhost/api/health
```

### Paso 5: Obtener certificados SSL

```bash
# Asegurate que el dominio apunta al servidor
# Luego ejecuta certbot

docker run --rm \
  -v /opt/sitnova/certbot/conf:/etc/letsencrypt \
  -v /opt/sitnova/certbot/www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d tu-dominio.com \
  -d api.tu-dominio.com \
  -d evolution.tu-dominio.com \
  --email tu@email.com \
  --agree-tos \
  --no-eff-email
```

### Paso 6: Activar SSL

```bash
# Copiar certificados al directorio de nginx
mkdir -p nginx/ssl
cp certbot/conf/live/tu-dominio.com/fullchain.pem nginx/ssl/
cp certbot/conf/live/tu-dominio.com/privkey.pem nginx/ssl/

# Cambiar a config con SSL
cp nginx/nginx.prod.conf nginx/nginx.conf

# Reiniciar nginx
docker-compose -f docker-compose.cloud.yml restart nginx
```

### Paso 7: Configurar en Portainer

1. Accede a Portainer: `https://tu-servidor:9443`
2. Ve a **Stacks** > **Add Stack**
3. Nombre: `sitnova`
4. Metodo: **Upload** o **Repository**
5. Selecciona `docker-compose.cloud.yml`
6. En **Environment variables**, agrega las variables de `.env.prod`
7. Click **Deploy the stack**

---

## Parte 2: Deployment Local (Condominio)

### Prerequisitos

- PC/Mini PC con Docker instalado
- 4GB+ RAM
- Conexion a red local con camaras
- Acceso a internet para sync con cloud

### Paso 1: Preparar equipo local

```bash
# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Crear directorio
mkdir -p /opt/sitnova-local
cd /opt/sitnova-local
```

### Paso 2: Copiar archivos necesarios

```bash
# Copiar solo lo necesario para OCR
scp -r tu-servidor:/opt/sitnova/docker-compose.local.yml .
scp -r tu-servidor:/opt/sitnova/Dockerfile.ocr .
scp -r tu-servidor:/opt/sitnova/Dockerfile.sync .
scp -r tu-servidor:/opt/sitnova/src/services/ ./src/services/
scp -r tu-servidor:/opt/sitnova/models/ ./models/
```

### Paso 3: Configurar conexion al cloud

```bash
# Crear archivo de environment
cat > .env << 'EOF'
# Cloud Connection
CLOUD_BACKEND_URL=https://api.tu-dominio.com
CLOUD_API_KEY=tu-api-key-segura

# Cameras (ajustar IPs segun tu red)
CAMERA_ENTRADA_URL=rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101
CAMERA_CEDULA_URL=rtsp://admin:password@192.168.1.102:554/Streaming/Channels/101

# OCR Config
YOLO_DEVICE=cpu
EOF
```

### Paso 4: Descargar modelos YOLO

```bash
mkdir -p models

# Modelo base
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt

# Modelo de placas (si tienes uno custom)
# cp /path/to/yolov8_plates.pt models/
```

### Paso 5: Iniciar servicios locales

```bash
docker-compose -f docker-compose.local.yml up -d --build

# Ver logs
docker-compose -f docker-compose.local.yml logs -f
```

### Paso 6: Verificar conexion

```bash
# Health check OCR
curl http://localhost:8001/health

# Health check sync
curl http://localhost:8002/health

# Ver logs de sync
docker logs sitnova-sync -f
```

---

## Verificacion Final

### Cloud

- [ ] `https://tu-dominio.com` - Frontend carga
- [ ] `https://api.tu-dominio.com/health` - Backend healthy
- [ ] `https://api.tu-dominio.com/docs` - Swagger UI
- [ ] SSL valido (candado verde)

### Local

- [ ] OCR service responde en `:8001`
- [ ] Sync service conecta al cloud
- [ ] Camaras accesibles via RTSP

### Integracion

- [ ] Crear evento de prueba desde local
- [ ] Verificar que llega al cloud
- [ ] Verificar notificacion WhatsApp

---

## Comandos Utiles

### Cloud (Contabo)

```bash
# Ver todos los logs
docker-compose -f docker-compose.cloud.yml logs -f

# Reiniciar un servicio
docker-compose -f docker-compose.cloud.yml restart backend

# Rebuild despues de cambios
docker-compose -f docker-compose.cloud.yml up -d --build

# Ver uso de recursos
docker stats

# Limpiar imagenes no usadas
docker system prune -a
```

### Local (Condominio)

```bash
# Ver logs OCR
docker logs sitnova-ocr -f

# Ver logs sync
docker logs sitnova-sync -f

# Reiniciar todo
docker-compose -f docker-compose.local.yml restart

# Ver uso de memoria
docker stats sitnova-ocr
```

---

## Troubleshooting

### Error: "Cannot connect to cloud backend"

```bash
# Verificar conectividad
curl https://api.tu-dominio.com/health

# Verificar API key
docker logs sitnova-sync | grep -i auth
```

### Error: "Camera connection failed"

```bash
# Probar RTSP directamente
ffprobe rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101

# Verificar red
ping 192.168.1.101
```

### Error: "Out of memory"

```bash
# Ver memoria disponible
free -h

# Reducir limites en docker-compose
# memory: 1G -> memory: 512M
```

### Certificados SSL expiran

```bash
# Renovar manualmente
docker run --rm \
  -v /opt/sitnova/certbot/conf:/etc/letsencrypt \
  -v /opt/sitnova/certbot/www:/var/www/certbot \
  certbot/certbot renew

# Copiar nuevos certs
cp certbot/conf/live/tu-dominio.com/*.pem nginx/ssl/
docker-compose -f docker-compose.cloud.yml restart nginx
```

---

## Contacto y Soporte

- **Logs**: Siempre revisar logs primero
- **Health checks**: Usar endpoints `/health`
- **Metricas**: `docker stats` para recursos

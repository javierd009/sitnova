# SITNOVA - Checklist de Deployment

## Subdominios Requeridos

Crea estos registros DNS apuntando a la IP del servidor Contabo:

| Subdominio | Tipo | Valor |
|------------|------|-------|
| `sitnova.integratec-ia.com` | A | IP_DEL_SERVIDOR |
| `api.sitnova.integratec-ia.com` | A | IP_DEL_SERVIDOR |
| `evolution.sitnova.integratec-ia.com` | A | IP_DEL_SERVIDOR |

---

## Paso 1: Preparar el Servidor

```bash
# Conectar por SSH
ssh root@IP_DEL_SERVIDOR

# Crear directorio
mkdir -p /opt/sitnova
cd /opt/sitnova

# Clonar repositorio
git clone https://github.com/tu-repo/sitnova.git .
```

---

## Paso 2: Configurar Variables de Entorno

```bash
# Copiar template
cp .env.prod.example .env.prod

# Editar con valores reales
nano .env.prod
```

### Variables que DEBES configurar:

```env
# Ya configurados
DOMAIN=sitnova.integratec-ia.com
SSL_EMAIL=tu-email@integratec-ia.com

# Supabase (obtener de dashboard)
SUPABASE_URL=https://lgqeeumflbzzmqysqkiq.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# LLM (Google AI)
GOOGLE_API_KEY=AIzaSyBH-80nXdk2rHO2iJcpFPPRBC4EkN0rV1o

# Ultravox
ULTRAVOX_API_KEY=ciMYOzjs.rJnxftAnulCkxpzXz5sYkhXrq3SQ6e49

# Evolution (generar key segura)
EVOLUTION_API_KEY=$(openssl rand -hex 32)

# Seguridad (generar key segura)
SECRET_KEY=$(openssl rand -hex 32)
```

---

## Paso 3: Deploy Inicial (HTTP)

```bash
# Usar nginx config inicial (sin SSL)
cp nginx/nginx.initial.conf nginx/nginx.conf

# Crear directorios
mkdir -p data/images data/logs

# Build y arrancar
docker-compose -f docker-compose.cloud.yml up -d --build

# Ver logs
docker-compose -f docker-compose.cloud.yml logs -f
```

### Verificar que funciona:

- [ ] `http://sitnova.integratec-ia.com` - Carga frontend
- [ ] `http://api.sitnova.integratec-ia.com/health` - Retorna OK
- [ ] `docker-compose -f docker-compose.cloud.yml ps` - Todos running

---

## Paso 4: Obtener Certificados SSL

```bash
# Ejecutar certbot
docker run --rm \
  -v /opt/sitnova/certbot/conf:/etc/letsencrypt \
  -v /opt/sitnova/certbot/www:/var/www/certbot \
  certbot/certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d sitnova.integratec-ia.com \
  -d api.sitnova.integratec-ia.com \
  -d evolution.sitnova.integratec-ia.com \
  --email tu-email@integratec-ia.com \
  --agree-tos \
  --no-eff-email
```

---

## Paso 5: Activar HTTPS

```bash
# Cambiar a config con SSL
cp nginx/nginx.prod.conf nginx/nginx.conf

# Reiniciar nginx
docker-compose -f docker-compose.cloud.yml restart nginx
```

### Verificar HTTPS:

- [ ] `https://sitnova.integratec-ia.com` - Candado verde
- [ ] `https://api.sitnova.integratec-ia.com/health` - Candado verde
- [ ] `https://api.sitnova.integratec-ia.com/docs` - Swagger UI

---

## Paso 6: Configurar en Portainer (Alternativo)

1. Accede a `https://devportainer.integratec-ia.com`
2. **Stacks** > **Add Stack**
3. Nombre: `sitnova`
4. **Build method**: Repository o Upload
5. En **Environment variables**, agrega:

| Variable | Valor |
|----------|-------|
| `SUPABASE_URL` | https://lgqeeumflbzzmqysqkiq.supabase.co |
| `SUPABASE_SERVICE_ROLE_KEY` | eyJ... |
| `GOOGLE_API_KEY` | AIza... |
| `ULTRAVOX_API_KEY` | ciMYOzjs... |
| `EVOLUTION_API_KEY` | (generar) |
| `SECRET_KEY` | (generar) |

6. Click **Deploy the stack**

---

## Verificacion Final

### URLs Funcionando:

- [ ] https://sitnova.integratec-ia.com - Dashboard admin
- [ ] https://api.sitnova.integratec-ia.com/docs - API docs
- [ ] https://api.sitnova.integratec-ia.com/health - Health check
- [ ] https://evolution.sitnova.integratec-ia.com - Evolution API

### Servicios Activos:

```bash
docker-compose -f docker-compose.cloud.yml ps
```

| Servicio | Estado |
|----------|--------|
| sitnova-redis | Running |
| sitnova-backend | Running |
| sitnova-frontend | Running |
| sitnova-evolution | Running |
| sitnova-nginx | Running |
| sitnova-certbot | Running |

### Logs sin errores:

```bash
docker-compose -f docker-compose.cloud.yml logs --tail=50
```

---

## Troubleshooting

### DNS no propaga
```bash
# Verificar DNS
dig sitnova.integratec-ia.com
nslookup sitnova.integratec-ia.com
```

### Certbot falla
```bash
# Ver logs de certbot
docker logs sitnova-certbot

# Verificar que puerto 80 responde
curl -v http://sitnova.integratec-ia.com/.well-known/acme-challenge/test
```

### Backend no arranca
```bash
# Ver logs del backend
docker logs sitnova-backend -f

# Verificar variables de entorno
docker exec sitnova-backend env | grep -E "(SUPABASE|GOOGLE|REDIS)"
```

### Frontend muestra error
```bash
# Ver logs del frontend
docker logs sitnova-frontend -f

# Rebuild frontend
docker-compose -f docker-compose.cloud.yml up -d --build frontend
```

---

## Comandos Utiles

```bash
# Ver estado
docker-compose -f docker-compose.cloud.yml ps

# Ver logs de todos
docker-compose -f docker-compose.cloud.yml logs -f

# Ver logs de un servicio
docker logs sitnova-backend -f

# Reiniciar todo
docker-compose -f docker-compose.cloud.yml restart

# Rebuild y reiniciar
docker-compose -f docker-compose.cloud.yml up -d --build

# Limpiar todo (cuidado!)
docker-compose -f docker-compose.cloud.yml down -v
```

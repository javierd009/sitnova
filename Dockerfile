# ============================================
# Multi-stage Dockerfile para SITNOVA Agent
# ============================================

# ============================================
# STAGE 1: Base con dependencias del sistema
# ============================================
FROM python:3.11-slim as base

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Configurar timezone
ENV TZ=America/Costa_Rica
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# ============================================
# STAGE 2: Builder con dependencias Python
# ============================================
FROM base as builder

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias en un virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================
# STAGE 3: Development (con hot-reload)
# ============================================
FROM base as development

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar código fuente
COPY src/ /app/src/
COPY .env.example /app/.env

# Crear directorios necesarios
RUN mkdir -p /app/data /app/logs /app/models

# Usuario no-root
RUN useradd -m -u 1000 sitnova && \
    chown -R sitnova:sitnova /app
USER sitnova

# Exponer puerto
EXPOSE 8000

# Comando de desarrollo (con reload)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================
# STAGE 4: Production (optimizado)
# ============================================
FROM base as production

# Copiar virtualenv desde builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar solo el código fuente necesario
COPY src/ /app/src/

# Crear directorios
RUN mkdir -p /app/data /app/logs /app/models

# Usuario no-root
RUN useradd -m -u 1000 sitnova && \
    chown -R sitnova:sitnova /app
USER sitnova

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Exponer puerto
EXPOSE 8000

# Comando de producción (sin reload, con workers)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

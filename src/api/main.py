"""
FastAPI Application principal para SITNOVA.
Gateway para webhooks, eventos y administración.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from loguru import logger

from src.config.settings import settings
from src.api.routes import webhooks, vision, admin, tools, voice


# ============================================
# LIFECYCLE EVENTS
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle del app: startup y shutdown.
    """
    # STARTUP
    logger.info("🚀 Iniciando SITNOVA Agent...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Model: {settings.llm_model}")

    yield

    # SHUTDOWN
    logger.info("🛑 Apagando SITNOVA Agent...")


# ============================================
# APP CREATION
# ============================================
app = FastAPI(
    title="SITNOVA API",
    description="Sistema Inteligente de Control de Acceso para Condominios",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)


# ============================================
# MIDDLEWARE
# ============================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de todas las requests"""
    start_time = time.time()

    # Log request
    logger.info(f"➡️  {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log response
    logger.info(
        f"⬅️  {request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Duration: {duration:.3f}s"
    )

    return response


# ============================================
# ROUTES
# ============================================

# Health check
@app.get("/health")
async def health_check():
    """
    Health check endpoint para Docker healthcheck y monitoring.
    """
    return {
        "status": "healthy",
        "service": "sitnova-agent",
        "environment": settings.environment,
        "version": "1.0.0",
    }


# Supabase health check
@app.get("/health/supabase")
async def supabase_health_check():
    """
    Verifica la conexión con Supabase y retorna información de diagnóstico.
    """
    from src.database.connection import get_supabase

    try:
        supabase = get_supabase()

        if supabase is None:
            return {
                "status": "error",
                "connected": False,
                "message": "Supabase no configurado - Variables de entorno faltantes",
                "details": {
                    "supabase_url_configured": bool(settings.supabase_url),
                    "supabase_key_configured": bool(settings.supabase_service_role_key),
                }
            }

        # Intentar hacer una query simple para verificar conexión
        result = supabase.table("residents").select("id").limit(1).execute()

        return {
            "status": "ok",
            "connected": True,
            "message": "Conexión exitosa a Supabase",
            "details": {
                "supabase_url": settings.supabase_url,
                "table_accessible": True,
                "sample_query_success": True,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "connected": False,
            "message": f"Error conectando a Supabase: {str(e)}",
            "details": {
                "supabase_url_configured": bool(settings.supabase_url),
                "supabase_key_configured": bool(settings.supabase_service_role_key),
                "error_type": type(e).__name__,
            }
        }


# Root
@app.get("/")
async def root():
    """
    Endpoint raíz con información del servicio.
    """
    return {
        "service": "SITNOVA - Sistema Inteligente de Control de Acceso",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.is_development else "disabled",
    }


# Include routers
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(vision.router, prefix="/vision", tags=["Vision"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(voice.router, prefix="/voice", tags=["Voice"])
app.include_router(tools.router, prefix="/tools", tags=["Tools"])


# ============================================
# ERROR HANDLERS
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global de excepciones.
    """
    logger.error(f"❌ Error no manejado: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "Ha ocurrido un error interno",
            "detail": str(exc) if settings.is_development else None,
        },
    )


# ============================================
# STARTUP MESSAGE
# ============================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )

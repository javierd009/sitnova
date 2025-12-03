"""
Configuración centralizada del sistema SITNOVA usando Pydantic Settings.
Todas las variables de entorno se cargan y validan aquí.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, Literal


class Settings(BaseSettings):
    """Configuración global de SITNOVA"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================
    # GENERAL
    # ============================================
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    project_name: str = "SITNOVA"

    # ============================================
    # LLM CONFIGURATION
    # ============================================
    llm_provider: Literal["anthropic", "openai", "google"] = "google"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""  # Para Gemini
    llm_model: str = "gemini-2.0-flash-exp"  # Default: Gemini 2.0 Flash
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096

    # ============================================
    # SUPABASE (Cloud Database)
    # ============================================
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # ============================================
    # REDIS (State & Cache)
    # ============================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_session_ttl: int = 3600  # 1 hora

    # ============================================
    # HIKVISION (Access Control)
    # ============================================
    hikvision_host: str = "192.168.1.100"
    hikvision_port: int = 80
    hikvision_user: str = "admin"
    hikvision_password: str = ""
    hikvision_door_id: int = 1
    hikvision_timeout: int = 10

    # ============================================
    # CÁMARAS RTSP
    # ============================================
    camera_entrada_url: str = "rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101"
    camera_cedula_url: str = "rtsp://admin:password@192.168.1.102:554/Streaming/Channels/101"
    camera_entrada_id: str = "cam_entrada"
    camera_cedula_id: str = "cam_cedula"

    # ============================================
    # FREEPBX (PBX para llamadas)
    # ============================================
    freepbx_host: str = "192.168.1.50"
    freepbx_ami_port: int = 5038
    freepbx_ami_user: str = "portero"
    freepbx_ami_secret: str = ""
    freepbx_context: str = "from-internal"
    freepbx_timeout: int = 30

    # ============================================
    # ULTRAVOX (Voice AI)
    # ============================================
    ultravox_api_key: str = ""
    ultravox_webhook_secret: str = ""
    ultravox_voice: str = "es-CR-SofiaNeural"  # Voz en español Costa Rica
    ultravox_model: str = "fixie-ai/ultravox-v0_2"

    # ============================================
    # ASTERSIPVOX (Bridge FreePBX <-> Ultravox)
    # ============================================
    astersipvox_url: str = "http://localhost:7070"  # URL del servidor AsterSIPVox
    astersipvox_api_key: str = ""  # Bearer token para autenticacion
    astersipvox_extension: str = "205"  # Extension del asistente virtual

    # ============================================
    # VISIÓN ARTIFICIAL
    # ============================================
    yolo_model_path: str = "models/yolov8n.pt"
    yolo_device: str = "cpu"  # "cuda" si hay GPU
    plate_ocr_engine: Literal["paddleocr", "easyocr"] = "easyocr"
    cedula_ocr_engine: Literal["paddleocr", "easyocr"] = "easyocr"
    ocr_confidence_threshold: float = 0.7
    ocr_languages: list[str] = ["es", "en"]

    # Rutas de modelos
    yolo_plate_model: str = "models/yolov8_plates.pt"
    yolo_person_model: str = "models/yolov8n.pt"

    # ============================================
    # FASTAPI
    # ============================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    api_workers: int = 1
    cors_origins: list[str] = ["*"]

    # ============================================
    # LANGGRAPH
    # ============================================
    checkpoint_db_path: str = "data/sitnova_checkpoints.db"
    max_retries: int = 3
    session_timeout: int = 300  # 5 minutos

    # ============================================
    # STORAGE
    # ============================================
    images_path: str = "data/images"
    logs_path: str = "data/logs"
    models_path: str = "models"

    # ============================================
    # SEGURIDAD
    # ============================================
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # ============================================
    # NOTIFICACIONES
    # ============================================
    # Evolution API (WhatsApp)
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance_name: str = "sitnova"

    # OneSignal (Push)
    onesignal_app_id: str = ""
    onesignal_rest_api_key: str = ""

    # ============================================
    # OPERADOR HUMANO (Human in the Loop)
    # ============================================
    operator_phone: str = ""  # Telefono del operador de respaldo (WhatsApp)
    operator_timeout: int = 120  # Segundos antes de ofrecer transferir a operador

    # ============================================
    # PROPIEDADES COMPUTADAS
    # ============================================
    @property
    def redis_url(self) -> str:
        """URL de conexión a Redis"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def is_development(self) -> bool:
        """Verifica si estamos en desarrollo"""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Verifica si estamos en producción"""
        return self.environment == "production"

    @property
    def hikvision_base_url(self) -> str:
        """URL base de Hikvision ISAPI"""
        return f"http://{self.hikvision_host}:{self.hikvision_port}/ISAPI"


# Singleton global
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Obtiene la instancia singleton de configuración.
    Se cachea para evitar re-leer las variables de entorno.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Exportar para uso directo
settings = get_settings()

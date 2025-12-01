"""
Modulo de servicios de voz para SITNOVA.
Integra Ultravox Voice AI para el portero virtual.
"""
from src.services.voice.ultravox_client import (
    UltravoxClient,
    UltravoxCall,
    UltravoxCallConfig,
    UltravoxWebhookEvent,
    get_ultravox_client,
)
from src.services.voice.webhook_handler import (
    process_ultravox_webhook,
    verify_ultravox_signature,
    get_active_sessions,
    get_session_transcript,
)

__all__ = [
    # Client
    "UltravoxClient",
    "UltravoxCall",
    "UltravoxCallConfig",
    "UltravoxWebhookEvent",
    "get_ultravox_client",
    # Webhook Handler
    "process_ultravox_webhook",
    "verify_ultravox_signature",
    "get_active_sessions",
    "get_session_transcript",
]

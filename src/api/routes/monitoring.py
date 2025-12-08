"""
API Routes para Monitoring & Alertas.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.services.monitoring import (
    get_monitoring_service,
    AlertLevel,
    ServiceStatus,
)

router = APIRouter()


class AlertCreate(BaseModel):
    level: AlertLevel
    service: str
    message: str


class AlertResolve(BaseModel):
    alert_id: str


@router.get("/health")
async def get_system_health():
    """
    Obtiene el estado de salud completo del sistema.

    Incluye:
    - Estado de cada servicio (Supabase, AsterSIPVox, Hikvision, etc.)
    - Estadísticas de acceso del día
    - Alertas activas
    """
    monitoring = get_monitoring_service()
    metrics = await monitoring.get_system_health()

    return {
        "timestamp": metrics.timestamp.isoformat(),
        "overall_status": metrics.overall_status.value,
        "services": [
            {
                "name": s.name,
                "status": s.status.value,
                "response_time_ms": s.response_time_ms,
                "last_check": s.last_check.isoformat(),
                "message": s.message,
                "details": s.details,
            }
            for s in metrics.services
        ],
        "access_stats": metrics.access_stats,
        "alerts": metrics.alerts,
    }


@router.get("/services")
async def get_services_status():
    """
    Obtiene solo el estado de los servicios.
    Útil para health checks rápidos.
    """
    monitoring = get_monitoring_service()
    metrics = await monitoring.get_system_health()

    return {
        "overall_status": metrics.overall_status.value,
        "services": {
            s.name: {
                "status": s.status.value,
                "response_time_ms": s.response_time_ms,
                "message": s.message,
            }
            for s in metrics.services
        },
        "timestamp": metrics.timestamp.isoformat(),
    }


@router.get("/stats")
async def get_access_stats():
    """
    Obtiene estadísticas de acceso del día.
    """
    monitoring = get_monitoring_service()
    stats = await monitoring.get_access_stats()

    return {
        "date": datetime.now().date().isoformat(),
        "stats": stats,
    }


@router.get("/alerts")
async def get_alerts():
    """
    Obtiene todas las alertas activas.
    """
    monitoring = get_monitoring_service()
    alerts = monitoring.get_active_alerts()

    return {
        "count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "level": a.level.value,
                "service": a.service,
                "message": a.message,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in alerts
        ],
    }


@router.post("/alerts")
async def create_alert(alert_data: AlertCreate):
    """
    Crea una nueva alerta manualmente.
    """
    monitoring = get_monitoring_service()
    alert = monitoring.create_alert(
        level=alert_data.level,
        service=alert_data.service,
        message=alert_data.message,
    )

    return {
        "id": alert.id,
        "level": alert.level.value,
        "service": alert.service,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat(),
    }


@router.post("/alerts/resolve")
async def resolve_alert(data: AlertResolve):
    """
    Resuelve una alerta existente.
    """
    monitoring = get_monitoring_service()
    alert = monitoring.resolve_alert(data.alert_id)

    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {data.alert_id} no encontrada o ya resuelta"
        )

    return {
        "id": alert.id,
        "resolved": True,
        "resolved_at": alert.resolved_at.isoformat(),
    }


@router.get("/dashboard")
async def get_dashboard_data():
    """
    Endpoint consolidado para el dashboard de monitoreo.
    Retorna todos los datos necesarios en una sola llamada.
    """
    monitoring = get_monitoring_service()
    metrics = await monitoring.get_system_health()

    # Calcular uptime simulado (en producción vendría de métricas reales)
    services_healthy = sum(
        1 for s in metrics.services
        if s.status == ServiceStatus.HEALTHY
    )
    total_services = len(metrics.services)
    uptime_percentage = (services_healthy / total_services * 100) if total_services > 0 else 0

    return {
        "timestamp": metrics.timestamp.isoformat(),
        "system": {
            "status": metrics.overall_status.value,
            "uptime_percentage": round(uptime_percentage, 1),
            "services_total": total_services,
            "services_healthy": services_healthy,
        },
        "services": [
            {
                "name": s.name,
                "display_name": _get_display_name(s.name),
                "status": s.status.value,
                "response_time_ms": s.response_time_ms,
                "message": s.message,
            }
            for s in metrics.services
        ],
        "access_stats": {
            **metrics.access_stats,
            "success_rate": _calculate_success_rate(metrics.access_stats),
        },
        "alerts": {
            "count": len(metrics.alerts),
            "items": metrics.alerts[:5],  # Últimas 5 alertas
        },
    }


def _get_display_name(service_name: str) -> str:
    """Convierte nombre técnico a nombre legible."""
    names = {
        "supabase": "Base de Datos",
        "astersipvox": "Voice AI",
        "hikvision": "Control de Acceso",
        "evolution_api": "WhatsApp",
        "langgraph": "Agente IA",
    }
    return names.get(service_name, service_name.title())


def _calculate_success_rate(stats: dict) -> float:
    """Calcula tasa de éxito de accesos."""
    total = stats.get("total_today", 0)
    granted = stats.get("granted_today", 0)
    if total == 0:
        return 100.0
    return round((granted / total) * 100, 1)

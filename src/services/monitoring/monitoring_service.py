"""
Servicio de Monitoring & Alertas para SITNOVA.
Centraliza la recolección de métricas, health checks y alertas.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
from loguru import logger
import httpx

from src.config.settings import settings


class ServiceStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ServiceHealth(BaseModel):
    name: str
    status: ServiceStatus
    response_time_ms: Optional[float] = None
    last_check: datetime
    message: Optional[str] = None
    details: Dict[str, Any] = {}


class SystemMetrics(BaseModel):
    timestamp: datetime
    services: List[ServiceHealth]
    overall_status: ServiceStatus
    access_stats: Dict[str, int] = {}
    alerts: List[Dict[str, Any]] = []


class Alert(BaseModel):
    id: str
    level: AlertLevel
    service: str
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MonitoringService:
    """
    Servicio centralizado de monitoreo.

    Funcionalidades:
    - Health checks de todos los servicios
    - Recolección de métricas de acceso
    - Sistema de alertas
    - Dashboard de estado
    """

    def __init__(self):
        self.alerts: List[Alert] = []
        self._alert_counter = 0

    async def check_supabase(self) -> ServiceHealth:
        """Verifica conexión a Supabase."""
        start = datetime.now()
        try:
            from src.database.connection import get_supabase
            supabase = get_supabase()

            if not supabase:
                return ServiceHealth(
                    name="supabase",
                    status=ServiceStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    message="No configurado",
                )

            result = supabase.table("residents").select("id").limit(1).execute()
            response_time = (datetime.now() - start).total_seconds() * 1000

            return ServiceHealth(
                name="supabase",
                status=ServiceStatus.HEALTHY,
                response_time_ms=response_time,
                last_check=datetime.now(),
                message="Conectado",
                details={"url": settings.supabase_url[:30] + "..."}
            )
        except Exception as e:
            return ServiceHealth(
                name="supabase",
                status=ServiceStatus.UNHEALTHY,
                response_time_ms=(datetime.now() - start).total_seconds() * 1000,
                last_check=datetime.now(),
                message=str(e),
            )

    async def check_astersipvox(self) -> ServiceHealth:
        """Verifica conexión a AsterSIPVox."""
        start = datetime.now()
        try:
            if not settings.astersipvox_url:
                return ServiceHealth(
                    name="astersipvox",
                    status=ServiceStatus.UNKNOWN,
                    last_check=datetime.now(),
                    message="URL no configurada",
                )

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.astersipvox_url}/health")
                response_time = (datetime.now() - start).total_seconds() * 1000

                if response.status_code == 200:
                    return ServiceHealth(
                        name="astersipvox",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message="Voice AI conectado",
                    )
                else:
                    return ServiceHealth(
                        name="astersipvox",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message=f"HTTP {response.status_code}",
                    )
        except httpx.ConnectError:
            return ServiceHealth(
                name="astersipvox",
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                message="No se puede conectar",
            )
        except Exception as e:
            return ServiceHealth(
                name="astersipvox",
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                message=str(e),
            )

    async def check_hikvision(self) -> ServiceHealth:
        """Verifica conexión al sistema Hikvision."""
        start = datetime.now()
        try:
            if not settings.hikvision_host:
                return ServiceHealth(
                    name="hikvision",
                    status=ServiceStatus.UNKNOWN,
                    last_check=datetime.now(),
                    message="Host no configurado",
                )

            async with httpx.AsyncClient(
                timeout=5.0,
                auth=(settings.hikvision_user, settings.hikvision_password),
                verify=False
            ) as client:
                url = f"http://{settings.hikvision_host}/ISAPI/System/deviceInfo"
                response = await client.get(url)
                response_time = (datetime.now() - start).total_seconds() * 1000

                if response.status_code == 200:
                    return ServiceHealth(
                        name="hikvision",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message="Control de acceso conectado",
                    )
                else:
                    return ServiceHealth(
                        name="hikvision",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message=f"HTTP {response.status_code}",
                    )
        except Exception as e:
            return ServiceHealth(
                name="hikvision",
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                message=str(e)[:50],
            )

    async def check_evolution_api(self) -> ServiceHealth:
        """Verifica conexión a Evolution API (WhatsApp)."""
        start = datetime.now()
        try:
            if not settings.evolution_api_url:
                return ServiceHealth(
                    name="evolution_api",
                    status=ServiceStatus.UNKNOWN,
                    last_check=datetime.now(),
                    message="URL no configurada",
                )

            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {"apikey": settings.evolution_api_key}
                response = await client.get(
                    f"{settings.evolution_api_url}/instance/fetchInstances",
                    headers=headers
                )
                response_time = (datetime.now() - start).total_seconds() * 1000

                if response.status_code == 200:
                    return ServiceHealth(
                        name="evolution_api",
                        status=ServiceStatus.HEALTHY,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message="WhatsApp conectado",
                    )
                else:
                    return ServiceHealth(
                        name="evolution_api",
                        status=ServiceStatus.DEGRADED,
                        response_time_ms=response_time,
                        last_check=datetime.now(),
                        message=f"HTTP {response.status_code}",
                    )
        except Exception as e:
            return ServiceHealth(
                name="evolution_api",
                status=ServiceStatus.UNHEALTHY,
                last_check=datetime.now(),
                message=str(e)[:50],
            )

    async def check_langgraph(self) -> ServiceHealth:
        """Verifica que LangGraph esté funcionando."""
        start = datetime.now()
        try:
            from src.agent.graph import get_graph
            graph = get_graph()
            response_time = (datetime.now() - start).total_seconds() * 1000

            if graph:
                return ServiceHealth(
                    name="langgraph",
                    status=ServiceStatus.HEALTHY,
                    response_time_ms=response_time,
                    last_check=datetime.now(),
                    message="Agente operativo",
                    details={"checkpoint_enabled": True}
                )
            else:
                return ServiceHealth(
                    name="langgraph",
                    status=ServiceStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    message="No se pudo inicializar",
                )
        except Exception as e:
            return ServiceHealth(
                name="langgraph",
                status=ServiceStatus.DEGRADED,
                last_check=datetime.now(),
                message=str(e)[:50],
            )

    async def get_access_stats(self) -> Dict[str, int]:
        """Obtiene estadísticas de acceso del día."""
        try:
            from src.database.connection import get_supabase
            supabase = get_supabase()

            if not supabase:
                return {}

            today = datetime.now().date().isoformat()

            result = supabase.table("access_logs")\
                .select("access_decision")\
                .gte("created_at", today)\
                .execute()

            stats = {
                "total_today": 0,
                "granted_today": 0,
                "denied_today": 0,
                "pending_today": 0,
            }

            if result.data:
                stats["total_today"] = len(result.data)
                for row in result.data:
                    decision = row.get("access_decision", "")
                    if decision == "granted":
                        stats["granted_today"] += 1
                    elif decision == "denied":
                        stats["denied_today"] += 1
                    elif decision == "pending":
                        stats["pending_today"] += 1

            return stats
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return {}

    def create_alert(
        self,
        level: AlertLevel,
        service: str,
        message: str
    ) -> Alert:
        """Crea una nueva alerta."""
        self._alert_counter += 1
        alert = Alert(
            id=f"ALR-{self._alert_counter:06d}",
            level=level,
            service=service,
            message=message,
            timestamp=datetime.now(),
        )
        self.alerts.append(alert)

        # Log según nivel
        if level == AlertLevel.CRITICAL:
            logger.critical(f"🚨 ALERTA: [{service}] {message}")
        elif level == AlertLevel.ERROR:
            logger.error(f"⚠️ ALERTA: [{service}] {message}")
        elif level == AlertLevel.WARNING:
            logger.warning(f"⚡ ALERTA: [{service}] {message}")
        else:
            logger.info(f"ℹ️ INFO: [{service}] {message}")

        return alert

    def get_active_alerts(self) -> List[Alert]:
        """Retorna alertas activas (no resueltas)."""
        return [a for a in self.alerts if not a.resolved]

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Resuelve una alerta."""
        for alert in self.alerts:
            if alert.id == alert_id and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                return alert
        return None

    async def get_system_health(self) -> SystemMetrics:
        """
        Ejecuta todos los health checks y retorna el estado del sistema.
        """
        # Ejecutar checks en paralelo
        checks = await asyncio.gather(
            self.check_supabase(),
            self.check_astersipvox(),
            self.check_hikvision(),
            self.check_evolution_api(),
            self.check_langgraph(),
            return_exceptions=True
        )

        services = []
        for check in checks:
            if isinstance(check, Exception):
                services.append(ServiceHealth(
                    name="unknown",
                    status=ServiceStatus.UNHEALTHY,
                    last_check=datetime.now(),
                    message=str(check),
                ))
            else:
                services.append(check)

                # Crear alertas automáticas para servicios no saludables
                if check.status == ServiceStatus.UNHEALTHY:
                    existing = [a for a in self.get_active_alerts()
                               if a.service == check.name]
                    if not existing:
                        self.create_alert(
                            AlertLevel.ERROR,
                            check.name,
                            f"Servicio no disponible: {check.message}"
                        )

        # Calcular estado general
        unhealthy_count = sum(1 for s in services if s.status == ServiceStatus.UNHEALTHY)
        degraded_count = sum(1 for s in services if s.status == ServiceStatus.DEGRADED)

        if unhealthy_count >= 2:
            overall_status = ServiceStatus.UNHEALTHY
        elif unhealthy_count >= 1 or degraded_count >= 2:
            overall_status = ServiceStatus.DEGRADED
        else:
            overall_status = ServiceStatus.HEALTHY

        # Obtener stats de acceso
        access_stats = await self.get_access_stats()

        return SystemMetrics(
            timestamp=datetime.now(),
            services=services,
            overall_status=overall_status,
            access_stats=access_stats,
            alerts=[a.model_dump() for a in self.get_active_alerts()[-10:]],
        )


# Singleton
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Obtiene la instancia singleton del servicio de monitoreo."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service

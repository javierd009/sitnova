"""
SITNOVA - Sync Service
Synchronizes local OCR events with cloud backend
"""

import asyncio
import os
import json
from datetime import datetime
from typing import Optional

import httpx
import redis


class SyncService:
    """Handles synchronization between local OCR and cloud backend."""

    def __init__(self):
        self.cloud_url = os.getenv("CLOUD_BACKEND_URL", "https://api.sitnova.com")
        self.api_key = os.getenv("CLOUD_API_KEY", "")
        self.redis_host = os.getenv("REDIS_HOST", "redis-local")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", "5"))

        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    async def connect(self):
        """Initialize connections."""
        self.redis_client = redis.Redis(
            host=self.redis_host,
            port=self.redis_port,
            decode_responses=True
        )

        self.http_client = httpx.AsyncClient(
            base_url=self.cloud_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

        print(f"[SYNC] Connected to Redis: {self.redis_host}:{self.redis_port}")
        print(f"[SYNC] Cloud backend: {self.cloud_url}")

    async def close(self):
        """Close connections."""
        if self.redis_client:
            self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()

    async def sync_ocr_event(self, event: dict) -> bool:
        """Send OCR event to cloud backend."""
        try:
            response = await self.http_client.post(
                "/api/v1/ocr/event",
                json=event
            )

            if response.status_code == 200:
                print(f"[SYNC] Event synced: {event.get('event_type', 'unknown')}")
                return True
            else:
                print(f"[SYNC] Failed to sync: {response.status_code}")
                # Queue for retry
                await self.queue_failed_event(event)
                return False

        except Exception as e:
            print(f"[SYNC] Error syncing event: {e}")
            await self.queue_failed_event(event)
            return False

    async def queue_failed_event(self, event: dict):
        """Queue failed event for retry."""
        event["retry_count"] = event.get("retry_count", 0) + 1
        event["failed_at"] = datetime.utcnow().isoformat()

        self.redis_client.rpush(
            "sitnova:failed_events",
            json.dumps(event)
        )

    async def process_failed_queue(self):
        """Retry failed events."""
        while True:
            event_json = self.redis_client.lpop("sitnova:failed_events")
            if not event_json:
                break

            event = json.loads(event_json)

            # Max 5 retries
            if event.get("retry_count", 0) >= 5:
                print(f"[SYNC] Event exceeded max retries, discarding")
                continue

            success = await self.sync_ocr_event(event)
            if not success:
                break  # Stop if still failing

    async def listen_for_events(self):
        """Subscribe to OCR events via Redis pub/sub."""
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe("sitnova:ocr_events")

        print("[SYNC] Listening for OCR events...")

        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    await self.sync_ocr_event(event)
                except json.JSONDecodeError:
                    print(f"[SYNC] Invalid event data: {message['data']}")

    async def health_check_loop(self):
        """Periodically check cloud connectivity."""
        while True:
            try:
                response = await self.http_client.get("/health")
                if response.status_code == 200:
                    print("[SYNC] Cloud backend healthy")
                else:
                    print(f"[SYNC] Cloud backend unhealthy: {response.status_code}")
            except Exception as e:
                print(f"[SYNC] Cloud backend unreachable: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def retry_loop(self):
        """Periodically retry failed events."""
        while True:
            await asyncio.sleep(self.sync_interval * 60)  # Every N minutes
            await self.process_failed_queue()

    async def run(self):
        """Main run loop."""
        await self.connect()

        try:
            # Run all tasks concurrently
            await asyncio.gather(
                self.listen_for_events(),
                self.health_check_loop(),
                self.retry_loop()
            )
        finally:
            await self.close()


# Simple HTTP health endpoint
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "sync"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs


def start_health_server():
    """Start health check HTTP server in background."""
    server = HTTPServer(("0.0.0.0", 8002), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("[SYNC] Health server started on :8002")


if __name__ == "__main__":
    start_health_server()

    sync = SyncService()
    asyncio.run(sync.run())

from typing import Any, Dict
import httpx
from app.config import settings

class ProcessingClient:
    def __init__(self, base_url: str = settings.processing_service_url):
        self.base_url = base_url.rstrip("/")

    async def forward_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/process"
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(url, json={"payload": payload})
            response.raise_for_status()
            return response.json()

processing_client = ProcessingClient()

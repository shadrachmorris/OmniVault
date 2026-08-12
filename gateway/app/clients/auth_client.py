import httpx
from app.config import settings
from app.schemas.common import TokenValidationResult

class AuthClient:
    def __init__(self, base_url: str = settings.auth_service_url):
        self.base_url = base_url.rstrip("/")

    async def validate_token(self, token: str) -> TokenValidationResult:
        url = f"{self.base_url}/auth/validate"
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            try:
                response = await client.post(url, json={"token": token})
            except httpx.RequestError as exc:
                return TokenValidationResult(valid=False, detail=f"Auth service unreachable: {exc}")

        if response.status_code != 200:
            return TokenValidationResult(valid=False, detail="Token rejected by Auth Service")

        data = response.json()
        return TokenValidationResult(
            valid=data.get("valid", False),
            subject=data.get("subject"),
            detail=data.get("detail"),
        )

auth_client = AuthClient()

import httpx

from app.config import settings
from app.schemas.common import TokenValidationResult


class AuthClient:
    def __init__(self, base_url: str = settings.auth_service_url):
        self.base_url = base_url.rstrip("/")

    async def validate_token(self, token: str) -> TokenValidationResult:
        url = f"{self.base_url}/auth/validate"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            try:
                response = await client.post(
                    url,
                    json={"token": token},
                )
            except httpx.RequestError as exc:
                return TokenValidationResult(
                    valid=False,
                    detail=f"Auth service unreachable: {exc}",
                )

        if response.status_code != 200:
            return TokenValidationResult(
                valid=False,
                detail="Token rejected by Auth Service",
            )

        data = response.json()

        return TokenValidationResult(
    		valid=data.get("valid", False),
    		subject=data.get("subject"),
    		user_id=data.get("user_id"),
    		detail=data.get("detail"),
	)

    async def register(
        self,
        username: str,
        password: str,
    ) -> dict:
        url = f"{self.base_url}/auth/register"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                json={
                    "username": username,
                    "password": password,
                },
            )

        response.raise_for_status()
        return response.json()

    async def login(
        self,
        username: str,
        password: str,
    ) -> dict:
        url = f"{self.base_url}/auth/login"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                json={
                    "username": username,
                    "password": password,
                },
            )

        response.raise_for_status()
        return response.json()

    async def create_account(
        self,
        user_id: int,
        name: str,
        account_type: str,
        balance: float,
        institution_name: str | None = None,
    ) -> dict:
        url = f"{self.base_url}/finance/accounts"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params={"user_id": user_id},
                json={
                    "name": name,
                    "account_type": account_type,
                    "balance": balance,
                    "institution_name": institution_name,
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_accounts(
        self,
        user_id: int,
    ) -> list:
        url = f"{self.base_url}/finance/accounts"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params={"user_id": user_id},
            )

        response.raise_for_status()
        return response.json()

    async def create_budget(
        self,
        user_id: int,
        category: str,
        monthly_limit: float,
    ) -> dict:
        url = f"{self.base_url}/finance/budgets"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params={"user_id": user_id},
                json={
                    "category": category,
                    "monthly_limit": monthly_limit,
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_budgets(
        self,
        user_id: int,
    ) -> list:
        url = f"{self.base_url}/finance/budgets"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params={"user_id": user_id},
            )

        response.raise_for_status()
        return response.json()

auth_client = AuthClient()
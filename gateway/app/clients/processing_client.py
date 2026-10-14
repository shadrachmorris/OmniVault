import httpx

from app.config import settings


class ProcessingClient:
    def __init__(
        self,
        base_url: str = settings.processing_service_url,
    ):
        self.base_url = base_url.rstrip("/")

    async def forward_payload(
        self,
        payload: dict,
    ) -> dict:
        url = f"{self.base_url}/process"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                json={"payload": payload},
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

    async def create_transaction(
        self,
        user_id: int,
        account_id: int,
        amount: float,
        description: str,
        category: str | None,
        transaction_date: str,
        is_subscription: bool = False,
    ) -> dict:
        url = f"{self.base_url}/finance/transactions"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params={"user_id": user_id},
                json={
                    "account_id": account_id,
                    "amount": amount,
                    "description": description,
                    "category": category,
                    "transaction_date": transaction_date,
                    "is_subscription": is_subscription,
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_transactions(
        self,
        user_id: int,
    ) -> list:
        url = f"{self.base_url}/finance/transactions"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params={"user_id": user_id},
            )

        response.raise_for_status()
        return response.json()

    async def create_subscription(
        self,
        user_id: int,
        name: str,
        amount: float,
        billing_frequency: str,
        next_billing_date: str | None,
        is_active: bool = True,
        merchant_id: int | None = None,
    ) -> dict:
        url = f"{self.base_url}/finance/subscriptions"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.post(
                url,
                params={"user_id": user_id},
                json={
                    "name": name,
                    "amount": amount,
                    "billing_frequency": billing_frequency,
                    "next_billing_date": next_billing_date,
                    "is_active": is_active,
                    "merchant_id": merchant_id,
                },
            )

        response.raise_for_status()
        return response.json()

    async def get_subscriptions(
        self,
        user_id: int,
    ) -> list:
        url = f"{self.base_url}/finance/subscriptions"

        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params={"user_id": user_id},
            )

        response.raise_for_status()
        return response.json()

processing_client = ProcessingClient()
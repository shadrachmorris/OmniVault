
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.config import settings
from app.middleware.auth_middleware import require_valid_token


router = APIRouter(
    prefix="/api/subscriptions",
    tags=["Subscription Management"],
)


async def forward(
    method: str,
    path: str,
    user_id: int,
    payload: dict | None = None,
    params: dict | None = None,
):
    url = (
        settings.processing_service_url.rstrip("/")
        + "/finance/subscriptions"
        + path
    )

    query = {"user_id": user_id}
    if params:
        query.update(params)

    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.request(
                method,
                url,
                params=query,
                json=payload,
            )

        if response.is_error:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text

            raise HTTPException(
                status_code=response.status_code,
                detail=detail,
            )

        return response.json()

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Finance service unavailable",
        )


@router.get("/upcoming")
async def upcoming(
    days: int = Query(default=30, ge=1, le=365),
    user: dict = Depends(require_valid_token),
):
    return await forward(
        "GET",
        "/upcoming",
        user_id=user["user_id"],
        params={"days": days},
    )


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    request: Request,
    user: dict = Depends(require_valid_token),
):
    payload = await request.json()

    return await forward(
        "PATCH",
        f"/{subscription_id}",
        user_id=user["user_id"],
        payload=payload,
    )


@router.post("/{subscription_id}/deactivate")
async def deactivate(
    subscription_id: int,
    user: dict = Depends(require_valid_token),
):
    return await forward(
        "POST",
        f"/{subscription_id}/deactivate",
        user_id=user["user_id"],
    )


@router.post("/{subscription_id}/activate")
async def activate(
    subscription_id: int,
    user: dict = Depends(require_valid_token),
):
    return await forward(
        "POST",
        f"/{subscription_id}/activate",
        user_id=user["user_id"],
    )

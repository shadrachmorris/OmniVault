
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.middleware.auth_middleware import require_valid_token


router = APIRouter(
    prefix="/api",
    tags=["OmniVault Analytics"],
)


async def finance_get(
    path: str,
    user_id: int,
    year: int | None = None,
    month: int | None = None,
days: int | None = None,

):
    params = {"user_id": user_id}

    if year is not None:
        params["year"] = year

    if month is not None:
        params["month"] = month

    if days is not None:
    	params["days"] = days

    url = (
        settings.processing_service_url.rstrip("/")
        + path
    )

    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout_seconds
        ) as client:
            response = await client.get(
                url,
                params=params,
            )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json()
        except ValueError:
            detail = exc.response.text

        raise HTTPException(
            status_code=exc.response.status_code,
            detail=detail,
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Finance service unavailable",
        )


@router.get("/dashboard")
async def dashboard(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user: dict = Depends(require_valid_token),
):
    return await finance_get(
        "/finance/dashboard",
        user_id=user["user_id"],
        year=year,
        month=month,
    )


@router.get("/spending")
async def spending(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user: dict = Depends(require_valid_token),
):
    return await finance_get(
        "/finance/spending",
        user_id=user["user_id"],
        year=year,
        month=month,
    )


@router.get("/budgets/progress")
async def budget_progress(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    user: dict = Depends(require_valid_token),
):
    return await finance_get(
        "/finance/budgets/progress",
        user_id=user["user_id"],
        year=year,
        month=month,
    )
@router.get("/forecast")
async def forecast(
    days: int = Query(default=30, ge=7, le=365),
    user: dict = Depends(require_valid_token),
):
    return await finance_get(
        "/finance/forecast",
        user_id=user["user_id"],
        days=days,
    )

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.finance_models import Subscription


router = APIRouter(
    prefix="/finance/subscriptions",
    tags=["Subscription Management"],
)


class SubscriptionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    amount: Decimal | None = Field(default=None, ge=0)
    billing_frequency: str | None = None
    next_billing_date: date | None = None
    is_active: bool | None = None


def serialize_subscription(sub):
    return {
        "id": sub.id,
        "user_id": sub.user_id,
        "name": sub.name,
        "amount": str(sub.amount),
        "billing_frequency": sub.billing_frequency,
        "next_billing_date": (
            sub.next_billing_date.isoformat()
            if sub.next_billing_date else None
        ),
        "is_active": sub.is_active,
        "merchant_id": sub.merchant_id,
    }


async def get_owned_subscription(db, user_id, subscription_id):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == user_id,
        )
    )

    sub = result.scalar_one_or_none()

    if sub is None:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found",
        )

    return sub


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    request: SubscriptionUpdate,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    sub = await get_owned_subscription(
        db, user_id, subscription_id
    )

    changes = request.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] is None:
        raise HTTPException(422, "Name cannot be null")

    if "amount" in changes and changes["amount"] is None:
        raise HTTPException(422, "Amount cannot be null")

    if (
        "billing_frequency" in changes
        and changes["billing_frequency"] is not None
    ):
        frequency = changes["billing_frequency"].lower()

        allowed = {
            "daily", "weekly", "biweekly",
            "monthly", "quarterly", "yearly",
        }

        if frequency not in allowed:
            raise HTTPException(
                status_code=422,
                detail="Invalid billing frequency",
            )

        changes["billing_frequency"] = frequency

    for field, value in changes.items():
        if field in {"billing_frequency", "is_active"} and value is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )
        setattr(sub, field, value)

    await db.commit()
    await db.refresh(sub)

    return {
        "status": "updated",
        "subscription": serialize_subscription(sub),
    }


@router.post("/{subscription_id}/deactivate")
async def deactivate_subscription(
    subscription_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    sub = await get_owned_subscription(
        db, user_id, subscription_id
    )

    sub.is_active = False

    await db.commit()
    await db.refresh(sub)

    return {
        "status": "deactivated",
        "subscription": serialize_subscription(sub),
        "message": (
            "Removed from active subscription tracking. "
            "This does not cancel billing with the merchant."
        ),
    }


@router.post("/{subscription_id}/activate")
async def activate_subscription(
    subscription_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    sub = await get_owned_subscription(
        db, user_id, subscription_id
    )

    sub.is_active = True

    await db.commit()
    await db.refresh(sub)

    return {
        "status": "activated",
        "subscription": serialize_subscription(sub),
    }


@router.get("/upcoming")
async def upcoming_subscriptions(
    user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    end = today + timedelta(days=days)

    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
            Subscription.next_billing_date >= today,
            Subscription.next_billing_date <= end,
        ).order_by(Subscription.next_billing_date)
    )

    subscriptions = result.scalars().all()

    return {
        "user_id": user_id,
        "window_days": days,
        "upcoming_count": len(subscriptions),
        "upcoming_total": str(
            sum(
                (sub.amount for sub in subscriptions),
                Decimal("0.00"),
            )
        ),
        "subscriptions": [
            serialize_subscription(sub)
            for sub in subscriptions
        ],
    }


from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.finance_models import Account, Subscription, Transaction


router = APIRouter(
    prefix="/finance",
    tags=["Forecasting"],
)

ZERO = Decimal("0.00")


def money(value):
    return str(
        Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def monthly_equivalent(amount, frequency):
    amount = Decimal(str(amount))
    frequency = (frequency or "").lower()

    factors = {
        "daily": Decimal("365") / 12,
        "weekly": Decimal("52") / 12,
        "biweekly": Decimal("26") / 12,
        "monthly": Decimal("1"),
        "quarterly": Decimal("1") / 3,
        "yearly": Decimal("1") / 12,
    }

    return amount * factors.get(frequency, ZERO)


@router.get("/forecast")
async def forecast(
    user_id: int,
    days: int = Query(default=30, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    history_start = today - timedelta(days=90)

    account_result = await db.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = account_result.scalars().all()

    transaction_result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= history_start,
            Transaction.transaction_date < today,
            Transaction.pending.is_(False),
        )
    )
    transactions = transaction_result.scalars().all()

    subscription_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active.is_(True),
        )
    )
    subscriptions = subscription_result.scalars().all()

    starting_balance = sum(
        (Decimal(str(account.balance)) for account in accounts),
        ZERO,
    )

    historical_spending = sum(
        (
            Decimal(str(tx.amount))
            for tx in transactions
            if Decimal(str(tx.amount)) > 0
        ),
        ZERO,
    )

    historical_inflow = sum(
        (
            abs(Decimal(str(tx.amount)))
            for tx in transactions
            if Decimal(str(tx.amount)) < 0
        ),
        ZERO,
    )

    daily_spending = historical_spending / Decimal("90")
    daily_inflow = historical_inflow / Decimal("90")

    monthly_subscriptions = sum(
        (
            monthly_equivalent(
                sub.amount,
                sub.billing_frequency,
            )
            for sub in subscriptions
        ),
        ZERO,
    )

    # Baseline forecast uses observed transaction history.
    # Subscription costs are reported separately because they may
    # already be represented in the historical spending data.
    projected_change = (
        daily_inflow - daily_spending
    ) * Decimal(days)

    projected_balance = starting_balance + projected_change

    points = []

    for day in range(0, days + 1):
        projected_day = today + timedelta(days=day)

        balance = starting_balance + (
            daily_inflow - daily_spending
        ) * Decimal(day)

        points.append({
            "date": projected_day.isoformat(),
            "balance": money(balance),
        })

    return {
        "user_id": user_id,
        "forecast_days": days,
        "starting_balance": money(starting_balance),
        "projected_balance": money(projected_balance),
        "projected_change": money(projected_change),
        "historical_daily_inflow": money(daily_inflow),
        "historical_daily_spending": money(daily_spending),
        "estimated_monthly_subscriptions": money(
            monthly_subscriptions
        ),
        "transactions_analyzed": len(transactions),
        "forecast": points,
        "method": "90-day historical cash-flow average",
        "limitations": [
            "Negative transactions are treated as inflows, "
            "including refunds and credits.",
            "Transfers may distort income and spending.",
            "The forecast assumes historical daily cash flow "
            "continues at the same rate.",
            "Subscription charges are not added again to avoid "
            "double-counting historical expenses.",
            "This is an estimate, not a guaranteed future balance.",
        ],
    }

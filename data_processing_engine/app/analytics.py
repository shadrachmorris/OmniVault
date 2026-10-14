
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.finance_models import (
    Account,
    Budget,
    Subscription,
    Transaction,
)

router = APIRouter(prefix="/finance", tags=["Analytics"])


def money(value):
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def month_bounds(year, month):
    if month < 1 or month > 12:
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12",
        )

    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=400,
            detail="Invalid year",
        )

    start = date(year, month, 1)

    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)

    return start, end


def category_name(value):
    return (value or "UNCATEGORIZED").strip().upper()


async def monthly_transactions(db, user_id, year, month):
    start, end = month_bounds(year, month)

    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
            Transaction.pending == False,
        )
    )

    return result.scalars().all()


@router.get("/budgets/progress")
async def budget_progress(
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    year = year or today.year
    month = month or today.month

    transactions = await monthly_transactions(
        db, user_id, year, month
    )

    result = await db.execute(
        select(Budget).where(Budget.user_id == user_id)
    )
    budgets = result.scalars().all()

    spending = defaultdict(lambda: Decimal("0.00"))

    for tx in transactions:
        category = category_name(tx.category)
        amount = Decimal(str(tx.amount))
        spending[category] += amount

    response = []

    for budget in budgets:
        category = category_name(budget.category)
        limit = Decimal(str(budget.monthly_limit))
        spent = max(Decimal("0"), spending[category])
        remaining = limit - spent

        percentage = (
            round(float(spent / limit * 100), 2)
            if limit > 0 else 0
        )

        if remaining < 0:
            status = "over_budget"
        elif percentage >= 80:
            status = "warning"
        else:
            status = "on_track"

        response.append({
            "id": budget.id,
            "category": budget.category,
            "monthly_limit": money(limit),
            "spent": money(spent),
            "remaining": money(remaining),
            "percentage_used": percentage,
            "status": status,
        })

    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "budgets": response,
    }


@router.get("/spending")
async def spending_analysis(
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    year = year or today.year
    month = month or today.month

    transactions = await monthly_transactions(
        db, user_id, year, month
    )

    categories = defaultdict(lambda: Decimal("0"))
    expenses = Decimal("0")
    income = Decimal("0")

    for tx in transactions:
        amount = Decimal(str(tx.amount))

        if amount > 0:
            expenses += amount
            categories[category_name(tx.category)] += amount
        elif amount < 0:
            income += abs(amount)

    breakdown = [
        {"category": category, "amount": money(amount)}
        for category, amount in sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "income": money(income),
        "expenses": money(expenses),
        "net_cash_flow": money(income - expenses),
        "categories": breakdown,
        "transaction_count": len(transactions),
    }


@router.get("/dashboard")
async def dashboard(
    user_id: int,
    year: int | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    year = year or today.year
    month = month or today.month

    account_result = await db.execute(
        select(Account).where(Account.user_id == user_id)
    )
    accounts = account_result.scalars().all()

    subscription_result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.is_active == True,
        )
    )
    subscriptions = subscription_result.scalars().all()

    spending = await spending_analysis(
        user_id=user_id,
        year=year,
        month=month,
        db=db,
    )

    budgets = await budget_progress(
        user_id=user_id,
        year=year,
        month=month,
        db=db,
    )

    total_balance = sum(
        (Decimal(str(a.balance)) for a in accounts),
        Decimal("0"),
    )

    monthly_subscriptions = Decimal("0")

    for sub in subscriptions:
        amount = Decimal(str(sub.amount))
        frequency = sub.billing_frequency.lower()

        if frequency == "weekly":
            monthly_subscriptions += amount * Decimal("52") / 12
        elif frequency == "biweekly":
            monthly_subscriptions += amount * Decimal("26") / 12
        elif frequency == "monthly":
            monthly_subscriptions += amount
        elif frequency == "quarterly":
            monthly_subscriptions += amount / 3
        elif frequency == "yearly":
            monthly_subscriptions += amount / 12

    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "total_account_balance": money(total_balance),
        "account_count": len(accounts),
        "accounts": [
            {
                "id": a.id,
                "name": a.name,
                "type": a.account_type,
                "balance": money(a.balance),
                "institution_name": a.institution_name,
                "connected_to_plaid": bool(a.plaid_account_id),
            }
            for a in accounts
        ],
        "income": spending["income"],
        "expenses": spending["expenses"],
        "net_cash_flow": spending["net_cash_flow"],
        "spending_categories": spending["categories"],
        "budgets": budgets["budgets"],
        "active_subscription_count": len(subscriptions),
        "estimated_monthly_subscriptions": money(
            monthly_subscriptions
        ),
    }

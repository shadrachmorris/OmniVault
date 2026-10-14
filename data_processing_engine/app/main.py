import asyncio
import logging
import os

from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict

import plaid

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import (
    LinkTokenCreateRequest,
)
from plaid.model.link_token_create_request_user import (
    LinkTokenCreateRequestUser,
)
from plaid.model.products import Products
from plaid.model.transactions_sync_request import (
    TransactionsSyncRequest,
)

from app.database import Base, engine, get_db
from app.finance_models import (
    Account,
    Budget,
    PlaidItem,
    Subscription,
    Transaction,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =========================================================
# PLAID CONFIGURATION
# =========================================================

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")


if PLAID_ENV == "sandbox":
    plaid_host = plaid.Environment.Sandbox
elif PLAID_ENV == "production":
    plaid_host = plaid.Environment.Production
else:
    plaid_host = plaid.Environment.Sandbox


plaid_configuration = plaid.Configuration(
    host=plaid_host,
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
    },
)

plaid_api_client = plaid.ApiClient(
    plaid_configuration
)

plaid_client = plaid_api.PlaidApi(
    plaid_api_client
)


# =========================================================
# DATABASE STARTUP
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    max_retries = 10

    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(
                    Base.metadata.create_all
                )

            logger.info(
                "Database connection successful."
            )

            break

        except Exception as exc:
            logger.warning(
                "Database connection attempt %s failed: %s",
                attempt + 1,
                exc,
            )

            if attempt == max_retries - 1:
                raise

            await asyncio.sleep(2)

    yield


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="OmniVault Data Processing Engine",
    version="1.0.0",
    lifespan=lifespan,
)


# Development only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# REQUEST MODELS
# =========================================================

class AccountRequest(BaseModel):
    name: str
    account_type: str
    opening_balance: Decimal = Decimal("0.00")


class BudgetRequest(BaseModel):
    category: str
    monthly_limit: Decimal


class TransactionRequest(BaseModel):
    account_id: int
    amount: Decimal
    description: str
    category: str | None = None
    transaction_date: date
    is_subscription: bool = False


class SubscriptionRequest(BaseModel):
    name: str
    amount: Decimal
    billing_frequency: str = "monthly"
    next_billing_date: date | None = None
    is_active: bool = True
    merchant_id: int | None = None


class PublicTokenRequest(BaseModel):
    public_token: str


# =========================================================
# BASIC ROUTES
# =========================================================

@app.get("/")
async def root():
    return {
        "service": "OmniVault Data Processing Engine",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.post("/process")
async def process_data(
    payload: Dict[str, Any],
):
    return {
        "status": "processed",
        "data": payload,
    }


# =========================================================
# ACCOUNTS
# =========================================================

@app.post("/finance/accounts")
async def create_account(
    request: AccountRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    account = Account(
        user_id=user_id,
        name=request.name,
        account_type=request.account_type,
        opening_balance=request.opening_balance,
        balance=request.opening_balance,
    )

    db.add(account)

    await db.commit()
    await db.refresh(account)

    return {
        "id": account.id,
        "user_id": account.user_id,
        "name": account.name,
        "account_type": account.account_type,
        "opening_balance": str(
            account.opening_balance
        ),
        "balance": str(
            account.balance
        ),
        "institution_name": (
            account.institution_name
        ),
        "plaid_account_id": (
            account.plaid_account_id
        ),
    }


@app.get("/finance/accounts")
async def get_accounts(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(
            Account.user_id == user_id
        )
    )

    accounts = result.scalars().all()

    return [
        {
            "id": account.id,
            "user_id": account.user_id,
            "name": account.name,
            "account_type": account.account_type,
            "opening_balance": str(
                account.opening_balance
            ),
            "balance": str(
                account.balance
            ),
            "institution_name": (
                account.institution_name
            ),
            "plaid_account_id": (
                account.plaid_account_id
            ),
        }
        for account in accounts
    ]


@app.post(
    "/finance/accounts/{account_id}/recalculate"
)
async def recalculate_account_balance(
    account_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.user_id == user_id,
        )
    )

    account = (
        account_result.scalar_one_or_none()
    )

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    transaction_result = await db.execute(
        select(
            func.coalesce(
                func.sum(Transaction.amount),
                0,
            )
        ).where(
            Transaction.account_id == account_id,
            Transaction.user_id == user_id,
        )
    )

    total_transactions = Decimal(
        str(
            transaction_result.scalar_one()
        )
    )

    account.balance = (
        account.opening_balance
        - total_transactions
    )

    await db.commit()
    await db.refresh(account)

    return {
        "account_id": account.id,
        "opening_balance": str(
            account.opening_balance
        ),
        "total_transactions": str(
            total_transactions
        ),
        "balance": str(
            account.balance
        ),
    }


# =========================================================
# BUDGETS
# =========================================================

@app.post("/finance/budgets")
async def create_budget(
    request: BudgetRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    budget = Budget(
        user_id=user_id,
        category=request.category,
        monthly_limit=request.monthly_limit,
    )

    db.add(budget)

    await db.commit()
    await db.refresh(budget)

    return {
        "id": budget.id,
        "user_id": budget.user_id,
        "category": budget.category,
        "monthly_limit": str(
            budget.monthly_limit
        ),
    }


@app.get("/finance/budgets")
async def get_budgets(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_id
        )
    )

    budgets = result.scalars().all()

    return [
        {
            "id": budget.id,
            "user_id": budget.user_id,
            "category": budget.category,
            "monthly_limit": str(
                budget.monthly_limit
            ),
        }
        for budget in budgets
    ]


# =========================================================
# TRANSACTIONS
# =========================================================

@app.post("/finance/transactions")
async def create_transaction(
    request: TransactionRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    account_result = await db.execute(
        select(Account).where(
            Account.id == request.account_id,
            Account.user_id == user_id,
        )
    )

    account = (
        account_result.scalar_one_or_none()
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found",
        )

    transaction = Transaction(
        user_id=user_id,
        account_id=request.account_id,
        amount=request.amount,
        description=request.description,
        category=request.category,
        transaction_date=(
            request.transaction_date
        ),
        pending=False,
        is_subscription=(
            request.is_subscription
        ),
    )

    account.balance = (
        account.balance
        - request.amount
    )

    db.add(transaction)

    await db.commit()
    await db.refresh(transaction)
    await db.refresh(account)

    return {
        "id": transaction.id,
        "user_id": transaction.user_id,
        "account_id": transaction.account_id,
        "amount": str(transaction.amount),
        "description": transaction.description,
        "category": transaction.category,
        "transaction_date": str(
            transaction.transaction_date
        ),
        "is_subscription": (
            transaction.is_subscription
        ),
        "new_account_balance": str(
            account.balance
        ),
    }


@app.get("/finance/transactions")
async def get_transactions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.user_id == user_id
        )
        .order_by(
            Transaction.transaction_date.desc()
        )
    )

    transactions = result.scalars().all()

    return [
        {
            "id": transaction.id,
            "user_id": transaction.user_id,
            "account_id": transaction.account_id,
            "plaid_transaction_id": (
                transaction.plaid_transaction_id
            ),
            "plaid_account_id": (
                transaction.plaid_account_id
            ),
            "merchant_name": (
                transaction.merchant_name
            ),
            "amount": str(
                transaction.amount
            ),
            "description": (
                transaction.description
            ),
            "category": transaction.category,
            "transaction_date": str(
                transaction.transaction_date
            ),
            "pending": transaction.pending,
            "is_subscription": (
                transaction.is_subscription
            ),
        }
        for transaction in transactions
    ]


# =========================================================
# SUBSCRIPTIONS
# =========================================================

@app.post("/finance/subscriptions")
async def create_subscription(
    request: SubscriptionRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    subscription = Subscription(
        user_id=user_id,
        merchant_id=request.merchant_id,
        name=request.name,
        amount=request.amount,
        billing_frequency=(
            request.billing_frequency
        ),
        next_billing_date=(
            request.next_billing_date
        ),
        is_active=request.is_active,
    )

    db.add(subscription)

    await db.commit()
    await db.refresh(subscription)

    return {
        "id": subscription.id,
        "user_id": subscription.user_id,
        "merchant_id": (
            subscription.merchant_id
        ),
        "name": subscription.name,
        "amount": str(
            subscription.amount
        ),
        "billing_frequency": (
            subscription.billing_frequency
        ),
        "next_billing_date": (
            str(subscription.next_billing_date)
            if subscription.next_billing_date
            else None
        ),
        "is_active": subscription.is_active,
    }


@app.get("/finance/subscriptions")
async def get_subscriptions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id
        )
    )

    subscriptions = result.scalars().all()

    return [
        {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "merchant_id": (
                subscription.merchant_id
            ),
            "name": subscription.name,
            "amount": str(
                subscription.amount
            ),
            "billing_frequency": (
                subscription.billing_frequency
            ),
            "next_billing_date": (
                str(
                    subscription.next_billing_date
                )
                if subscription.next_billing_date
                else None
            ),
            "is_active": (
                subscription.is_active
            ),
        }
        for subscription in subscriptions
    ]


# =========================================================
# PLAID - CREATE LINK TOKEN
# =========================================================

@app.post("/plaid/link-token")
async def create_plaid_link_token(
    user_id: int,
):
    try:
        request = LinkTokenCreateRequest(
            products=[
                Products("transactions")
            ],
            client_name="OmniVault",
            country_codes=[
                CountryCode("US")
            ],
            language="en",
            user=LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            ),
        )

        request["transactions"] = {
            "days_requested": 180
        }

        response = (
            plaid_client.link_token_create(
                request
            )
        )

        return {
            "link_token": response["link_token"]
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# PLAID - EXCHANGE TOKEN
# =========================================================

@app.post("/plaid/exchange-token")
async def exchange_plaid_public_token(
    request: PublicTokenRequest,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    exchange_request = (
        ItemPublicTokenExchangeRequest(
            public_token=request.public_token
        )
    )

    try:
        response = (
            plaid_client
            .item_public_token_exchange(
                exchange_request
            )
        )

        access_token = response["access_token"]
        item_id = response["item_id"]

        result = await db.execute(
            select(PlaidItem).where(
                PlaidItem.item_id == item_id
            )
        )

        plaid_item = (
            result.scalar_one_or_none()
        )

        if plaid_item is None:
            plaid_item = PlaidItem(
                user_id=user_id,
                item_id=item_id,
                access_token=access_token,
                sync_cursor=None,
            )

            db.add(plaid_item)

        else:
            plaid_item.user_id = user_id
            plaid_item.access_token = (
                access_token
            )

        await db.commit()
        await db.refresh(plaid_item)

        return {
            "status": "connected",
            "item_id": item_id,
            "connection_id": plaid_item.id,
        }

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# PLAID - ACCOUNTS
# =========================================================

@app.get("/plaid/accounts")
async def get_plaid_accounts(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlaidItem).where(
            PlaidItem.user_id == user_id
        )
    )

    plaid_item = (
        result.scalar_one_or_none()
    )

    if plaid_item is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No Plaid connection found "
                "for this user."
            ),
        )

    try:
        request = AccountsGetRequest(
            access_token=plaid_item.access_token
        )

        response = (
            plaid_client.accounts_get(
                request
            )
        )

        accounts = []

        for account in response["accounts"]:
            accounts.append(
                {
                    "account_id": (
                        account["account_id"]
                    ),
                    "name": account["name"],
                    "official_name": (
                        account.get(
                            "official_name"
                        )
                    ),
                    "type": str(
                        account["type"]
                    ),
                    "subtype": str(
                        account["subtype"]
                    ),
                    "balance_available": (
                        account["balances"][
                            "available"
                        ]
                    ),
                    "balance_current": (
                        account["balances"][
                            "current"
                        ]
                    ),
                    "currency": (
                        account["balances"][
                            "iso_currency_code"
                        ]
                    ),
                }
            )

        return {
            "user_id": user_id,
            "accounts": accounts,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# PLAID - VIEW NEW TRANSACTION CHANGES
# =========================================================

@app.get("/plaid/transactions")
async def get_plaid_transactions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlaidItem).where(
            PlaidItem.user_id == user_id
        )
    )

    plaid_item = (
        result.scalar_one_or_none()
    )

    if plaid_item is None:
        raise HTTPException(
            status_code=404,
            detail="No Plaid connection found.",
        )

    try:
        added_transactions = []
        modified_transactions = []
        removed_transactions = []

        cursor = plaid_item.sync_cursor
        has_more = True

        while has_more:
            if cursor is None:
                request = TransactionsSyncRequest(
                    access_token=(
                        plaid_item.access_token
                    ),
                    count=500,
                )
            else:
                request = TransactionsSyncRequest(
                    access_token=(
                        plaid_item.access_token
                    ),
                    cursor=cursor,
                    count=500,
                )

            response = (
                plaid_client.transactions_sync(
                    request
                )
            )

            added_transactions.extend(
                response["added"]
            )

            modified_transactions.extend(
                response["modified"]
            )

            removed_transactions.extend(
                response["removed"]
            )

            cursor = response["next_cursor"]
            has_more = response["has_more"]

        # Preview only. POST /plaid/sync owns the persisted cursor.

        transactions = []

        for transaction in added_transactions:
            personal_category = (
                transaction.get(
                    "personal_finance_category"
                )
            )

            category = None

            if personal_category:
                category = (
                    personal_category.get(
                        "primary"
                    )
                )

            transactions.append(
                {
                    "transaction_id": (
                        transaction[
                            "transaction_id"
                        ]
                    ),
                    "account_id": (
                        transaction["account_id"]
                    ),
                    "name": transaction["name"],
                    "merchant_name": (
                        transaction.get(
                            "merchant_name"
                        )
                    ),
                    "amount": (
                        transaction["amount"]
                    ),
                    "date": str(
                        transaction["date"]
                    ),
                    "pending": (
                        transaction["pending"]
                    ),
                    "category": category,
                }
            )

        return {
            "user_id": user_id,
            "transaction_count": len(
                transactions
            ),
            "transactions": transactions,
            "modified_count": len(
                modified_transactions
            ),
            "removed_count": len(
                removed_transactions
            ),
            "next_cursor": cursor,
        }

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# =========================================================
# PLAID - IMPORT INTO OMNIVAULT
# =========================================================

@app.post("/plaid/sync")
async def sync_plaid_data(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PlaidItem).where(
            PlaidItem.user_id == user_id
        )
    )

    plaid_item = (
        result.scalar_one_or_none()
    )

    if plaid_item is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No Plaid connection found "
                "for this user."
            ),
        )

    try:
        # ---------------------------------------------
        # ACCOUNTS
        # ---------------------------------------------

        accounts_request = AccountsGetRequest(
            access_token=plaid_item.access_token
        )

        accounts_response = (
            plaid_client.accounts_get(
                accounts_request
            )
        )

        account_map = {}

        accounts_created = 0
        accounts_updated = 0

        for plaid_account in (
            accounts_response["accounts"]
        ):
            plaid_account_id = (
                plaid_account["account_id"]
            )

            account_result = await db.execute(
                select(Account).where(
                    Account.plaid_account_id
                    == plaid_account_id
                )
            )

            account = (
                account_result.scalar_one_or_none()
            )

            current_balance = Decimal(
                str(
                    plaid_account[
                        "balances"
                    ]["current"]
                    or 0
                )
            )

            account_type = str(
                plaid_account["subtype"]
            )

            if account is None:
                account = Account(
                    user_id=user_id,
                    name=plaid_account["name"],
                    account_type=account_type,
                    opening_balance=current_balance,
                    balance=current_balance,
                    institution_name=None,
                    plaid_account_id=(
                        plaid_account_id
                    ),
                )

                db.add(account)
                await db.flush()

                accounts_created += 1

            else:
                account.name = (
                    plaid_account["name"]
                )

                account.account_type = (
                    account_type
                )

                account.balance = (
                    current_balance
                )

                accounts_updated += 1

            account_map[
                plaid_account_id
            ] = account

        # ---------------------------------------------
        # TRANSACTIONS
        # ---------------------------------------------

        cursor = plaid_item.sync_cursor
        has_more = True

        added = []
        modified = []
        removed = []

        while has_more:
            if cursor is None:
                sync_request = (
                    TransactionsSyncRequest(
                        access_token=(
                            plaid_item.access_token
                        ),
                        count=500,
                    )
                )
            else:
                sync_request = (
                    TransactionsSyncRequest(
                        access_token=(
                            plaid_item.access_token
                        ),
                        cursor=cursor,
                        count=500,
                    )
                )

            sync_response = (
                plaid_client.transactions_sync(
                    sync_request
                )
            )

            added.extend(
                sync_response["added"]
            )

            modified.extend(
                sync_response["modified"]
            )

            removed.extend(
                sync_response["removed"]
            )

            cursor = (
                sync_response["next_cursor"]
            )

            has_more = (
                sync_response["has_more"]
            )

        def get_category(
            plaid_transaction,
        ):
            personal_category = (
                plaid_transaction.get(
                    "personal_finance_category"
                )
            )

            if personal_category:
                return (
                    personal_category.get(
                        "primary"
                    )
                )

            return None

        transactions_created = 0
        transactions_updated = 0
        transactions_removed = 0

        # ---------------------------------------------
        # ADDED
        # ---------------------------------------------

        for plaid_transaction in added:
            plaid_transaction_id = (
                plaid_transaction[
                    "transaction_id"
                ]
            )

            existing_result = await db.execute(
                select(Transaction).where(
                    Transaction.plaid_transaction_id
                    == plaid_transaction_id
                )
            )

            existing_transaction = (
                existing_result
                .scalar_one_or_none()
            )

            plaid_account_id = (
                plaid_transaction[
                    "account_id"
                ]
            )

            local_account = account_map.get(
                plaid_account_id
            )

            if local_account is None:
                continue

            if existing_transaction is None:
                transaction = Transaction(
                    user_id=user_id,
                    account_id=local_account.id,
                    plaid_transaction_id=(
                        plaid_transaction_id
                    ),
                    plaid_account_id=(
                        plaid_account_id
                    ),
                    merchant_name=(
                        plaid_transaction.get(
                            "merchant_name"
                        )
                    ),
                    amount=Decimal(
                        str(
                            plaid_transaction[
                                "amount"
                            ]
                        )
                    ),
                    description=(
                        plaid_transaction["name"]
                    ),
                    category=get_category(
                        plaid_transaction
                    ),
                    transaction_date=(
                        plaid_transaction["date"]
                    ),
                    pending=(
                        plaid_transaction["pending"]
                    ),
                    is_subscription=False,
                )

                db.add(transaction)

                transactions_created += 1

            else:
                existing_transaction.account_id = (
                    local_account.id
                )

                existing_transaction.plaid_account_id = (
                    plaid_account_id
                )

                existing_transaction.merchant_name = (
                    plaid_transaction.get(
                        "merchant_name"
                    )
                )

                existing_transaction.amount = Decimal(
                    str(
                        plaid_transaction["amount"]
                    )
                )

                existing_transaction.description = (
                    plaid_transaction["name"]
                )

                existing_transaction.category = (
                    get_category(
                        plaid_transaction
                    )
                )

                existing_transaction.transaction_date = (
                    plaid_transaction["date"]
                )

                existing_transaction.pending = (
                    plaid_transaction["pending"]
                )

                transactions_updated += 1

        # ---------------------------------------------
        # MODIFIED
        # ---------------------------------------------

        for plaid_transaction in modified:
            plaid_transaction_id = (
                plaid_transaction[
                    "transaction_id"
                ]
            )

            transaction_result = await db.execute(
                select(Transaction).where(
                    Transaction.plaid_transaction_id
                    == plaid_transaction_id
                )
            )

            transaction = (
                transaction_result
                .scalar_one_or_none()
            )

            plaid_account_id = (
                plaid_transaction[
                    "account_id"
                ]
            )

            local_account = account_map.get(
                plaid_account_id
            )

            if transaction is None:
                if local_account is None:
                    continue

                transaction = Transaction(
                    user_id=user_id,
                    account_id=local_account.id,
                    plaid_transaction_id=(
                        plaid_transaction_id
                    ),
                    plaid_account_id=(
                        plaid_account_id
                    ),
                    merchant_name=(
                        plaid_transaction.get(
                            "merchant_name"
                        )
                    ),
                    amount=Decimal(
                        str(
                            plaid_transaction[
                                "amount"
                            ]
                        )
                    ),
                    description=(
                        plaid_transaction["name"]
                    ),
                    category=get_category(
                        plaid_transaction
                    ),
                    transaction_date=(
                        plaid_transaction["date"]
                    ),
                    pending=(
                        plaid_transaction["pending"]
                    ),
                    is_subscription=False,
                )

                db.add(transaction)

                transactions_created += 1

            else:
                if local_account is not None:
                    transaction.account_id = (
                        local_account.id
                    )

                transaction.plaid_account_id = (
                    plaid_account_id
                )

                transaction.merchant_name = (
                    plaid_transaction.get(
                        "merchant_name"
                    )
                )

                transaction.amount = Decimal(
                    str(
                        plaid_transaction["amount"]
                    )
                )

                transaction.description = (
                    plaid_transaction["name"]
                )

                transaction.category = (
                    get_category(
                        plaid_transaction
                    )
                )

                transaction.transaction_date = (
                    plaid_transaction["date"]
                )

                transaction.pending = (
                    plaid_transaction["pending"]
                )

                transactions_updated += 1

        # ---------------------------------------------
        # REMOVED
        # ---------------------------------------------

        for removed_transaction in removed:
            plaid_transaction_id = (
                removed_transaction[
                    "transaction_id"
                ]
            )

            transaction_result = await db.execute(
                select(Transaction).where(
                    Transaction.plaid_transaction_id
                    == plaid_transaction_id
                )
            )

            transaction = (
                transaction_result
                .scalar_one_or_none()
            )

            if transaction is not None:
                await db.delete(transaction)
                transactions_removed += 1

        plaid_item.sync_cursor = cursor

        await db.flush()

        subscription_analysis = await analyze_subscriptions(
            user_id=user_id,
            db=db,
        )

        await db.commit()

        return {
            "status": "success",
            "user_id": user_id,
            "accounts_created": (
                accounts_created
            ),
            "accounts_updated": (
                accounts_updated
            ),
            "transactions_created": (
                transactions_created
            ),
            "transactions_updated": (
                transactions_updated
            ),
            "transactions_removed": (
                transactions_removed
            ),
            "sync_cursor_saved": True,
            "subscription_analysis": subscription_analysis,
        }

    except Exception as exc:
        await db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

# =========================================================
# SUBSCRIPTION CONFIDENCE ENGINE
# =========================================================

async def analyze_subscriptions(user_id: int, db: AsyncSession):
    result = await db.execute(
        select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.plaid_transaction_id.is_not(None),
            Transaction.pending == False,
            Transaction.amount > 0,
        ).order_by(Transaction.transaction_date.asc())
    )
    transactions = result.scalars().all()

    for transaction in transactions:
        transaction.is_subscription = False

    merchant_groups = defaultdict(list)
    for transaction in transactions:
        merchant = transaction.merchant_name or transaction.description
        if merchant:
            merchant_groups[merchant.strip().lower()].append(transaction)

    risky = {"FOOD_AND_DRINK", "TRANSPORTATION", "TRAVEL"}
    ambiguous = {"GENERAL_MERCHANDISE"}
    confirmed, possible, ignored = [], [], []

    for group in merchant_groups.values():
        if len(group) < 3:
            continue
        group.sort(key=lambda tx: tx.transaction_date)

        amounts = [Decimal(str(tx.amount)) for tx in group]
        avg = sum(amounts) / Decimal(len(amounts))
        tolerance = max(Decimal("1.00"), avg * Decimal("0.10"))
        if not all(abs(x - avg) <= tolerance for x in amounts):
            continue

        gaps = [(group[i].transaction_date - group[i-1].transaction_date).days
                for i in range(1, len(group))]
        if not gaps:
            continue
        avg_gap = sum(gaps) / len(gaps)

        frequency = None
        expected = None
        gap_tol = None
        cadence_points = 0
        if 5 <= avg_gap <= 9:
            frequency, expected, gap_tol, cadence_points = "weekly", 7, 3, 10
        elif 12 <= avg_gap <= 16:
            frequency, expected, gap_tol, cadence_points = "biweekly", 14, 4, 10
        elif 25 <= avg_gap <= 35:
            frequency, expected, gap_tol, cadence_points = "monthly", 30, 7, 25
        elif 80 <= avg_gap <= 100:
            frequency, expected, gap_tol, cadence_points = "quarterly", 90, 15, 20
        elif 340 <= avg_gap <= 390:
            frequency, expected, gap_tol, cadence_points = "yearly", 365, 30, 25
        if frequency is None or not all(abs(g-expected) <= gap_tol for g in gaps):
            continue

        latest = group[-1]
        name = latest.merchant_name or latest.description
        category = latest.category
        rounded = avg.quantize(Decimal("0.01"))
        next_date = latest.transaction_date + timedelta(days=expected)

        score = 25 if len(group) >= 6 else 20 if len(group) >= 4 else 15
        max_diff = max(abs(x-avg) for x in amounts)
        score += 25 if max_diff <= Decimal("0.25") else 15
        score += cadence_points
        reasons = ["recurring charges", "consistent amount", f"consistent {frequency} schedule"]

        if category in risky:
            score -= 35
            reasons.append("discretionary-spending category")
        elif category in ambiguous:
            score -= 20
            reasons.append("broad merchant category needs confirmation")
        else:
            score += 10
            reasons.append("category supports recurring-payment confidence")
        if frequency in {"weekly", "biweekly"}:
            score -= 10
            reasons.append("frequent cadence lowers confidence")

        score = max(0, min(100, score))
        if score >= 80:
            confidence, classification = "high", "subscription"
        elif score >= 50:
            confidence, classification = "medium", "possible_recurring"
        else:
            confidence, classification = "low", "ignored"

        data = {
            "name": name, "amount": str(rounded), "category": category,
            "billing_frequency": frequency, "occurrences": len(group),
            "average_gap_days": round(avg_gap, 1),
            "next_billing_date": str(next_date),
            "confidence_score": score, "confidence": confidence,
            "classification": classification, "reasons": reasons,
        }

        if classification == "subscription":
            q = await db.execute(select(Subscription).where(
                Subscription.user_id == user_id,
                func.lower(Subscription.name) == name.lower(),
            ))
            sub = q.scalar_one_or_none()
            if sub is None:
                sub = Subscription(
                    user_id=user_id, name=name, amount=rounded,
                    billing_frequency=frequency, next_billing_date=next_date,
                    is_active=True, merchant_id=latest.merchant_id,
                )
                db.add(sub)
            else:
                sub.amount = rounded
                sub.billing_frequency = frequency
                sub.next_billing_date = next_date
                sub.is_active = True
            for tx in group:
                tx.is_subscription = True
            confirmed.append(data)
        elif classification == "possible_recurring":
            possible.append(data)
        else:
            ignored.append(data)

    return {
        "subscriptions_detected": len(confirmed), "subscriptions": confirmed,
        "possible_recurring_count": len(possible), "possible_recurring": possible,
        "ignored_recurring_count": len(ignored), "ignored_recurring": ignored,
    }


@app.post("/finance/subscriptions/detect")
async def detect_subscriptions(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        analysis = await analyze_subscriptions(user_id, db)
        await db.commit()
        return {"status": "success", "user_id": user_id, **analysis}
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))

from app.analytics import router as analytics_router
app.include_router(analytics_router)

from app.subscription_management import (
    router as subscription_management_router,
)

app.include_router(subscription_management_router)

from app.forecasting import router as forecasting_router

app.include_router(forecasting_router)

from app.omnivault_features import router as omnivault_features_router

app.include_router(omnivault_features_router)

from app.intelligence import router as intelligence_router

app.include_router(intelligence_router)

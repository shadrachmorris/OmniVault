from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# =========================================================
# ACCOUNTS
# =========================================================

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=0,
        nullable=False,
    )

    institution_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Plaid's unique ID for the connected bank account.
    # Manual OmniVault accounts will leave this NULL.
    plaid_account_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# BRANDS
# =========================================================

class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )

    website: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


# =========================================================
# MERCHANTS
# =========================================================

class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id"),
        nullable=True,
    )


# =========================================================
# TRANSACTIONS
# =========================================================

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    # Local OmniVault account ID.
    account_id: Mapped[int] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=True,
    )

    # Plaid's unique transaction ID.
    #
    # UNIQUE prevents the same Plaid transaction
    # from being imported multiple times.
    #
    # NULL is allowed because manually entered
    # transactions don't have Plaid IDs.
    plaid_transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    # Plaid's bank-account identifier.
    #
    # This is different from account_id above.
    # account_id = OmniVault database ID
    # plaid_account_id = Plaid account ID
    plaid_account_id: Mapped[str | None] = mapped_column(
        String(255),
        index=True,
        nullable=True,
    )

    merchant_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    pending: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_subscription: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )


# =========================================================
# BUDGETS
# =========================================================

class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    monthly_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )


# =========================================================
# SUBSCRIPTIONS
# =========================================================

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    merchant_id: Mapped[int | None] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    billing_frequency: Mapped[str] = mapped_column(
        String(50),
        default="monthly",
        nullable=False,
    )

    next_billing_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


# =========================================================
# USER BRAND PREFERENCES
# =========================================================

class UserBrandPreference(Base):
    __tablename__ = "user_brand_preferences"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    brand_id: Mapped[int] = mapped_column(
        ForeignKey(
            "brands.id",
            ondelete="CASCADE",
        ),
        index=True,
        nullable=False,
    )

    preference_source: Mapped[str] = mapped_column(
        String(50),
        default="transaction_history",
        nullable=False,
    )

    score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=0,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


# =========================================================
# PLAID CONNECTIONS
# =========================================================

class PlaidItem(Base):
    __tablename__ = "plaid_items"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        index=True,
        nullable=False,
    )

    # Plaid Item ID identifies the connected
    # financial institution connection.
    item_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    # Sensitive Plaid credential.
    #
    # Fine for our local development test.
    # Before production this should be encrypted
    # rather than stored as plaintext.
    access_token: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Plaid Transactions Sync cursor.
    #
    # Lets OmniVault request only changes after
    # the previous successful synchronization.
    sync_cursor: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
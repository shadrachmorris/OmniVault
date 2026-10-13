
import httpx
from datetime import date
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.clients.auth_client import auth_client
from app.clients.processing_client import processing_client
from app.middleware.auth_middleware import require_valid_token
from app.schemas.common import SubmitRequest, SubmitResponse

app = FastAPI(
    title="OmniVault API Gateway",
    version="1.0.0",
)

class AuthRequest(BaseModel):
    username: str
    password: str

class AccountRequest(BaseModel):
    name: str
    account_type: str
    opening_balance: float = 0.0

class BudgetRequest(BaseModel):
    category: str
    monthly_limit: float

class TransactionRequest(BaseModel):
    account_id: int
    amount: float
    description: str
    category: str | None = None
    transaction_date: date
    is_subscription: bool = False

class SubscriptionRequest(BaseModel):
    name: str
    amount: float
    billing_frequency: str = "monthly"
    next_billing_date: date | None = None
    is_active: bool = True
    merchant_id: int | None = None

def handle_error(exc: httpx.HTTPStatusError):
    try:
        detail = exc.response.json()
    except Exception:
        detail = exc.response.text
    raise HTTPException(
        status_code=exc.response.status_code,
        detail=detail,
    )

@app.get("/")
async def root():
    return {"service": "OmniVault Gateway", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/auth/register")
async def register(request: AuthRequest):
    try:
        return await auth_client.register(
            username=request.username,
            password=request.password,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.post("/auth/login")
async def login(request: AuthRequest):
    try:
        return await auth_client.login(
            username=request.username,
            password=request.password,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.get("/api/me")
async def current_user(user: dict = Depends(require_valid_token)):
    return user

@app.post("/api/accounts")
async def create_account(
    request: AccountRequest,
    user: dict = Depends(require_valid_token),
):
    try:
        return await processing_client.create_account(
            user_id=user["user_id"],
            name=request.name,
            account_type=request.account_type,
            opening_balance=request.opening_balance,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.get("/api/accounts")
async def get_accounts(user: dict = Depends(require_valid_token)):
    try:
        return await processing_client.get_accounts(user["user_id"])
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.post("/api/budgets")
async def create_budget(
    request: BudgetRequest,
    user: dict = Depends(require_valid_token),
):
    try:
        return await processing_client.create_budget(
            user_id=user["user_id"],
            category=request.category,
            monthly_limit=request.monthly_limit,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.get("/api/budgets")
async def get_budgets(user: dict = Depends(require_valid_token)):
    try:
        return await processing_client.get_budgets(user["user_id"])
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.post("/api/transactions")
async def create_transaction(
    request: TransactionRequest,
    user: dict = Depends(require_valid_token),
):
    try:
        return await processing_client.create_transaction(
            user_id=user["user_id"],
            account_id=request.account_id,
            amount=request.amount,
            description=request.description,
            category=request.category,
            transaction_date=request.transaction_date.isoformat(),
            is_subscription=request.is_subscription,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.get("/api/transactions")
async def get_transactions(user: dict = Depends(require_valid_token)):
    try:
        return await processing_client.get_transactions(user["user_id"])
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.post("/api/subscriptions")
async def create_subscription(
    request: SubscriptionRequest,
    user: dict = Depends(require_valid_token),
):
    try:
        return await processing_client.create_subscription(
            user_id=user["user_id"],
            name=request.name,
            amount=request.amount,
            billing_frequency=request.billing_frequency,
            next_billing_date=(
                request.next_billing_date.isoformat()
                if request.next_billing_date else None
            ),
            is_active=request.is_active,
            merchant_id=request.merchant_id,
        )
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.get("/api/subscriptions")
async def get_subscriptions(user: dict = Depends(require_valid_token)):
    try:
        return await processing_client.get_subscriptions(user["user_id"])
    except httpx.HTTPStatusError as exc:
        handle_error(exc)

@app.post("/api/submit", response_model=SubmitResponse)
async def submit_payload(
    request: SubmitRequest,
    user: dict = Depends(require_valid_token),
):
    try:
        result = await processing_client.forward_payload(request.payload)
        return SubmitResponse(status="success", result=result)
    except httpx.HTTPStatusError as exc:
        handle_error(exc)
# =========================================================
# DASHBOARD AND ANALYTICS
# =========================================================

@app.get("/api/dashboard")
async def get_dashboard(
    user: dict = Depends(require_valid_token),
):
    return await processing_client.request(
        "GET",
        "/finance/dashboard",
        user_id=user["user_id"],
    )


@app.get("/api/spending")
async def get_spending(
    user: dict = Depends(require_valid_token),
):
    return await processing_client.request(
        "GET",
        "/finance/spending",
        user_id=user["user_id"],
    )


@app.get("/api/budgets/progress")
async def get_budget_progress(
    user: dict = Depends(require_valid_token),
):
    return await processing_client.request(
        "GET",
        "/finance/budgets/progress",
        user_id=user["user_id"],
    )
from app.analytics_routes import router as analytics_router

app.include_router(analytics_router)

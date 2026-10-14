import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db
from app.models import User


logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------
# JWT / AUTH SETTINGS
# ---------------------------------------------------------

SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-change-me",
)

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ---------------------------------------------------------
# DATABASE STARTUP
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    max_retries = 10

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Auth database initialized successfully.")
            break

        except Exception as exc:
            logger.warning(
                "Database connection attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )

            if attempt == max_retries:
                raise

            await asyncio.sleep(2)

    yield


app = FastAPI(
    title="OmniVault Auth Service",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenRequest(BaseModel):
    token: str


# ---------------------------------------------------------
# PASSWORD HELPERS
# ---------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )


# ---------------------------------------------------------
# JWT HELPERS
# ---------------------------------------------------------

def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": username,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        username = payload.get("sub")

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return username

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ---------------------------------------------------------
# BASIC ROUTES
# ---------------------------------------------------------

@app.get("/")
async def root():
    return {
        "service": "OmniVault Auth Service",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }


# ---------------------------------------------------------
# REGISTER
# ---------------------------------------------------------

@app.post("/auth/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.username == request.username
        )
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    new_user = User(
        username=request.username,
        hashed_password=hash_password(
            request.password
        ),
        is_active=True,
    )

    db.add(new_user)

    await db.commit()
    await db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "message": "User registered successfully",
    }


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

@app.post("/auth/login")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(
            User.username == request.username
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not verify_password(
        request.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(
        user.username
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ---------------------------------------------------------
# VALIDATE TOKEN
# ---------------------------------------------------------

@app.post("/auth/validate")
async def validate_token(
    request: TokenRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        username = decode_access_token(
            request.token
        )

        result = await db.execute(
            select(User).where(
                User.username == username
            )
        )

        user = result.scalar_one_or_none()

        if not user:
            return {
                "valid": False,
                "subject": None,
                "user_id": None,
                "detail": "User no longer exists",
            }

        if not user.is_active:
            return {
                "valid": False,
                "subject": None,
                "user_id": None,
                "detail": "User account is inactive",
            }

        return {
            "valid": True,
            "subject": user.username,
            "user_id": user.id,
            "detail": "Token is valid",
        }

    except HTTPException as exc:
        return {
            "valid": False,
            "subject": None,
            "user_id": None,
            "detail": exc.detail,
        }


# ---------------------------------------------------------
# CURRENT USER
# ---------------------------------------------------------

@app.get("/auth/me")
async def auth_me(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    username = decode_access_token(token)

    result = await db.execute(
        select(User).where(
            User.username == username
        )
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
    }
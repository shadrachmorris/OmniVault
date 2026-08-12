import asyncio
import logging
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from app.database import engine, Base, get_db

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    retries = 5
    while retries > 0:
        try:
            logger.info("Attempting database connection and table creation...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database connection established and tables verified.")
            break
        except Exception as e:
            retries -= 1
            logger.warning(f"Database not ready yet ({retries} retries left). Waiting 2 seconds... Error: {e}")
            await asyncio.sleep(2)
    else:
        logger.critical("Could not connect to the database. Exiting application.")
        raise RuntimeError("Database connection failed permanently.")
        
    yield

app = FastAPI(title="Auth Service", lifespan=lifespan)

class TokenRequest(BaseModel):
    token: str

@app.post("/auth/validate")
async def validate_token(request: TokenRequest, db: AsyncSession = Depends(get_db)):
    if request.token == "valid-token":
        return {"valid": True, "subject": "user123", "detail": "Token is valid"}
    return {"valid": False, "subject": None, "detail": "Invalid token matching"}
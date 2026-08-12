from fastapi import Depends, FastAPI, HTTPException, status
import httpx
from app.clients.processing_client import processing_client
from app.middleware.auth_middleware import require_valid_token
from app.schemas.common import SubmitRequest, SubmitResponse

app = FastAPI(title="FastAPI Gateway", version="1.0.0")

@app.post("/api/submit", response_model=SubmitResponse)
async def submit_payload(request: SubmitRequest, username: str = Depends(require_valid_token)):
    try:
        result = await processing_client.forward_payload(request.payload)
        return SubmitResponse(status="success", result=result)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Data Processing error: {exc.response.text}")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

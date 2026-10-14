import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from app.config import settings
from app.middleware.auth_middleware import require_valid_token

router = APIRouter(prefix='/api/intelligence', tags=['Financial Intelligence'])

@router.get('/overview')
async def overview(days: int = Query(30, ge=7, le=90), safety_balance: float = Query(100, ge=0), user: dict = Depends(require_valid_token)):
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(
                settings.processing_service_url.rstrip('/') + '/finance/intelligence/overview',
                params={'user_id':user['user_id'], 'days':days, 'safety_balance':safety_balance},
            )
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail='Finance intelligence service unavailable')
    try:
        result = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail='Invalid response from finance service')
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail=result)
    return result

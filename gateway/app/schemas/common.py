from typing import Any, Dict, Optional
from pydantic import BaseModel

class SubmitRequest(BaseModel):
    payload: Dict[str, Any]

class SubmitResponse(BaseModel):
    status: str
    result: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None

class TokenValidationResult(BaseModel):
    valid: bool
    subject: Optional[str] = None
    detail: Optional[str] = None

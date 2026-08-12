import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Draft2Code Dashboard")
templates = Jinja2Templates(directory="templates")

API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    system_metrics = {
        "total_users": 128,
        "active_sessions": 42,
        "db_status": "Connected",
        "api_health": "Healthy"
    }
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{API_GATEWAY_URL}/health")
            if response.status_code == 200:
                system_metrics["api_health"] = "Healthy"
    except Exception:
        system_metrics["api_health"] = "Degraded (Gateway Unreachable)"

    # Pass request as the first positional argument to match modern Starlette signatures
    return templates.TemplateResponse(
        request,
        "index.html", 
        {"metrics": system_metrics}
    )

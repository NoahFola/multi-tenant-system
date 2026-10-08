from fastapi import FastAPI
from fastapi.responses import JSONResponse
from common.errors import AppError
from app.api.routes_notifications import router as notif_router

app = FastAPI(title="NotificationService")

@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(notif_router, prefix="/notifications", tags=["notifications"])

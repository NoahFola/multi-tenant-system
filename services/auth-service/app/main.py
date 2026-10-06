from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from common.errors import AppError

from app.api import routes_auth, routes_verify, routes_password

app = FastAPI(title="AuthService")

# Global error handler
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# Register all routers
app.include_router(routes_auth.router, prefix="/auth", tags=["auth"])
app.include_router(routes_verify.router, prefix="/auth", tags=["auth"])
app.include_router(routes_password.router, prefix="/auth", tags=["auth"])

@app.get("/health")
def health():
    return {"status": "ok"}

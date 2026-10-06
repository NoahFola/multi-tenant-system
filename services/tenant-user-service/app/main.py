from fastapi import FastAPI
from fastapi.responses import JSONResponse
from common.errors import AppError
from app.api import routes_users, routes_invitations

app = FastAPI(title="TenantUserService")

@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(routes_users.router, prefix="/users", tags=["users"])
app.include_router(routes_invitations.router, prefix="/invitations", tags=["invitations"])

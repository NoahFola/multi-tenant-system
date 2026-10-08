from fastapi import FastAPI
from fastapi.responses import JSONResponse
from common.errors import AppError
from app.api import routes_projects, routes_workflows

app = FastAPI(title="WorkflowService")

@app.exception_handler(AppError)
async def app_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(routes_projects.router,  prefix="/projects",  tags=["projects"])
app.include_router(routes_workflows.router, prefix="/workflows", tags=["workflows"])

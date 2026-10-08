import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes_audit import router as audit_router
from common.errors import AppError
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)

import threading
from common.firestore_client import get_db
from common.redis_client import get_redis
from app.consumers.audit_consumer import AuditConsumer
import app.repositories.audit_repo as repo

stop_event = threading.Event()

def consumer_loop():
    db = get_db()
    redis_client = get_redis()
    consumer = AuditConsumer(db=db, redis_client=redis_client, repo=repo)
    consumer.ensure_group()
    
    while not stop_event.is_set():
        consumer.run_once()

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=consumer_loop, daemon=True)
    thread.start()
    yield
    stop_event.set()
    thread.join(timeout=3.0)

app = FastAPI(title="Audit Service", lifespan=lifespan)

@app.exception_handler(AppError)
async def app_error_handler(request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

app.include_router(audit_router)

"""Application entry point, router registration, and static Web UI mounting.

FastAPI reads this file to build the app. Every API group lives in its
own router file under app/api/v1/ — main.py wires them together,
registers the /health check, and serves the static frontend UI at /.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import chat, documents, evaluate, feedback, history
from app.core.config import LOG_LEVEL
from app.core.logging_config import get_logger, setup_logging
from app.db.database import initialize_database
from app.models import db_models  # registers all SQLAlchemy models before startup

setup_logging(LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Run startup tasks before the server begins accepting requests."""
    initialize_database()
    yield


app = FastAPI(
    title="ContextFlow AI",
    description="A RAG-powered document knowledge assistant backend & Web UI.",
    version="0.2.0",
    lifespan=lifespan,
)

# API Routers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat.router,      prefix="/api/v1/chat",      tags=["chat"])
app.include_router(history.router,   prefix="/api/v1/chat",      tags=["chat"])
app.include_router(feedback.router,  prefix="/api/v1/feedback",  tags=["feedback"])
app.include_router(evaluate.router,  prefix="/api/v1/evaluate",  tags=["evaluate"])

# Mount static files directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_ui():
    """Serve the single-page application frontend at the root URL."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
def health_check():
    """Quick liveness check — confirms the server is running and accepting requests."""
    return {"status": "ok", "service": "ContextFlow AI"}

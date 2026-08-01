"""Application entry point, router registration, and API-only backend.

FastAPI reads this file to build the app. Every API group lives in its
own router file under app/api/v1/ — main.py wires them together,
registers the /health check, and provides a REST API backend.

For the UI, use the Streamlit frontend in app.py at the project root.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

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
    description="A RAG-powered document knowledge assistant backend API. Use the Streamlit frontend (app.py) for UI.",
    version="0.2.0",
    lifespan=lifespan,
)

# API Routers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat.router,      prefix="/api/v1/chat",      tags=["chat"])
app.include_router(history.router,   prefix="/api/v1/chat",      tags=["chat"])
app.include_router(feedback.router,  prefix="/api/v1/feedback",  tags=["feedback"])
app.include_router(evaluate.router,  prefix="/api/v1/evaluate",  tags=["evaluate"])


@app.get("/")
def root():
    """API root endpoint - redirects to documentation."""
    return {
        "message": "ContextFlow AI Backend API",
        "docs": "/docs",
        "health": "/health",
        "note": "Use the Streamlit frontend (run: streamlit run app.py) for the web UI"
    }


@app.get("/health")
def health_check():
    """Quick liveness check — confirms the server is running and accepting requests."""
    return {"status": "ok", "service": "ContextFlow AI"}

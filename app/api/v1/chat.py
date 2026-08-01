"""POST /api/v1/chat/ask — ask a question against the indexed documents.

Picks up the provider from the request body (or falls back to
DEFAULT_LLM_PROVIDER in .env), runs the RAG pipeline, saves the
message to the database, and returns the answer with its sources.

A session_id groups messages into a conversation. If the caller
doesn't provide one, a new UUID is generated for each request.
"""
import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import DEFAULT_LLM_PROVIDER
from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models.db_models import ChatMessage
from app.schemas.chat_schema import AskRequest, AskResponse
from app.services.rag_pipeline import answer_question

logger = get_logger(__name__)
router = APIRouter()

SUPPORTED_PROVIDERS = {"gemini", "groq"}


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, db: Session = Depends(get_db)):
    """Run the RAG pipeline and return a grounded answer."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")
    
    # Add maximum question length
    if len(request.question) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Question too long. Maximum 1000 characters allowed."
        )
    
    if request.provider not in (None, *SUPPORTED_PROVIDERS):
        raise HTTPException(status_code=400, detail="provider must be 'gemini' or 'groq'.")

    provider   = request.provider or DEFAULT_LLM_PROVIDER
    session_id = request.session_id or str(uuid.uuid4())
    started_at = time.perf_counter()

    try:
        result = answer_question(request.question, provider=provider)
    except ValueError as exc:
        # ValueError means a config problem (missing API key, etc.) — 503 is appropriate.
        logger.info("RAG request could not be completed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("RAG pipeline failed for question: '%s'", request.question)
        raise HTTPException(
            status_code=502,
            detail="Failed to generate an answer. The AI provider may be unavailable.",
        ) from exc

    latency_ms = round((time.perf_counter() - started_at) * 1000)

    # Save the exchange to the database so /history can retrieve it.
    # If the DB write fails, we still return the answer — a write failure
    # is not a reason to discard a successfully generated response.
    message_id = None
    try:
        message = ChatMessage(
            session_id=session_id,
            question=request.question,
            answer=result["answer"],
            sources=json.dumps(result["sources"]),  # stored as JSON string, decoded by /history
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        message_id = message.id
    except Exception:
        db.rollback()
        logger.exception("Failed to save chat message for session '%s'", session_id)

    return {
        "session_id": session_id,
        "message_id": message_id,
        "provider":   provider,
        "answer":     result["answer"],
        "sources":    result["sources"],
        "latency_ms": latency_ms,
    }

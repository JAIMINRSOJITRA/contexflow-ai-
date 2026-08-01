"""Pydantic schemas for the /chat/ask and /chat/history endpoints.

Schemas do two jobs:
  1. Validate incoming request bodies (FastAPI rejects bad input automatically).
  2. Define exactly what shape the JSON response will have.

Keeping schemas separate from db_models means the HTTP layer and
the database layer can evolve independently.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Body of POST /api/v1/chat/ask."""

    question:   str
    session_id: str | None = None
    provider:   str | None = Field(
        default=None,
        description="Which LLM to use: 'gemini' or 'groq'. Defaults to DEFAULT_LLM_PROVIDER in .env.",
    )


class AskResponse(BaseModel):
    """Shape of a successful /ask response."""

    session_id: str           # continue a conversation by sending this back
    message_id: int | None    # None if the DB write failed (answer still returned)
    provider:   str           # which provider actually generated the answer
    answer:     str
    sources:    list[str]     # filenames of the documents that informed the answer
    latency_ms: int           # wall-clock time for the RAG pipeline call


class ChatHistoryItem(BaseModel):
    """One message in a GET /history/{session_id} response."""

    question:   str
    answer:     str
    sources:    list[str]
    created_at: datetime


class SessionSummary(BaseModel):
    """Summary of a past chat session for sidebar listing."""

    session_id:    str
    last_question: str
    message_count: int
    updated_at:    datetime

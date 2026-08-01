"""GET /api/v1/chat/history/{session_id} — retrieve a past conversation.
GET /api/v1/chat/sessions               — list all past chat sessions.
DELETE /api/v1/chat/history/{session_id} — delete a past session.

Kept in a separate file from chat.py so the answer-generation route
and the history route can evolve independently.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.db_models import ChatMessage
from app.schemas.chat_schema import ChatHistoryItem, SessionSummary

router = APIRouter()


def _decode_sources(value: str | None) -> list[str]:
    """Parse sources from either JSON list or comma-separated string.

    Handles both current format ('["a.txt","b.txt"]') and the older
    plain-text format ('a.txt, b.txt') so history stays readable for
    documents uploaded before the format was standardised.
    """
    if not value:
        return []
    try:
        sources = json.loads(value)
    except json.JSONDecodeError:
        # Fall back to comma-split for legacy records.
        return [s.strip() for s in value.split(",") if s.strip()]
    return sources if isinstance(sources, list) else []


@router.get("/sessions", response_model=list[SessionSummary])
def get_sessions(db: Session = Depends(get_db)):
    """Return a summary list of all chat sessions, newest first."""
    # Query distinct sessions with message count and latest timestamp
    subquery = (
        db.query(
            ChatMessage.session_id,
            func.max(ChatMessage.created_at).label("latest_at"),
            func.count(ChatMessage.id).label("total_messages")
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    results = (
        db.query(subquery.c.session_id, subquery.c.latest_at, subquery.c.total_messages)
        .order_by(subquery.c.latest_at.desc())
        .all()
    )

    summaries = []
    for s_id, latest_at, msg_count in results:
        # Get the latest question snippet for preview
        last_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == s_id)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        last_question = last_msg.question if last_msg else "Chat Session"
        summaries.append({
            "session_id": s_id,
            "last_question": last_question,
            "message_count": msg_count,
            "updated_at": latest_at,
        })

    return summaries


@router.get("/history/{session_id}", response_model=list[ChatHistoryItem])
def get_history(session_id: str, db: Session = Depends(get_db)):
    """Return all messages in a session, oldest first.

    Returns an empty list for unknown session IDs — not a 404.
    """
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {
            "question":   message.question,
            "answer":     message.answer,
            "sources":    _decode_sources(message.sources),
            "created_at": message.created_at,
        }
        for message in messages
    ]


@router.delete("/history/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete all messages for a specific session."""
    deleted_count = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .delete(synchronize_session=False)
    )
    db.commit()

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found.")

    return {"status": "deleted", "session_id": session_id, "messages_deleted": deleted_count}

"""POST /api/v1/feedback — rate an individual answer as thumbs up or down.

Feedback is stored against a chat_messages.id so it can later be
aggregated to measure overall answer quality and guide optimisation
decisions (e.g. which chunk size produces better-rated answers).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.db_models import ChatMessage, Feedback

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: int   # the id returned by /chat/ask
    rating:     str   # must be "up" or "down"


@router.post("")
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """Record a thumbs-up or thumbs-down rating for one chat message."""
    if request.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'.")

    # Verify the message exists before writing — prevents orphaned feedback rows.
    if db.get(ChatMessage, request.message_id) is None:
        raise HTTPException(status_code=404, detail="message_id not found.")

    db.add(Feedback(message_id=request.message_id, rating=request.rating))
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not record feedback.") from exc

    return {
        "status":     "feedback recorded",
        "message_id": request.message_id,
        "rating":     request.rating,
    }

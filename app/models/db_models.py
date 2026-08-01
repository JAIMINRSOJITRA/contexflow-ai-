"""SQLAlchemy models for the three database tables.

Each class maps to one table. SQLAlchemy handles the SQL — we just
work with Python objects and let the ORM translate.

Tables:
  - documents     : every file that has been uploaded and indexed
  - chat_messages : every question/answer pair from the RAG pipeline
  - feedback      : thumbs-up / thumbs-down ratings for individual answers
"""
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.database import Base


def _now():
    """Return the current UTC time without timezone info (SQLite stores naive datetimes)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Document(Base):
    __tablename__ = "documents"

    id               = Column(Integer, primary_key=True, index=True)
    filename         = Column(String, nullable=False)           # original name shown to the user
    storage_filename = Column(String, nullable=True)            # uuid-prefixed name on disk
    source_id        = Column(String, nullable=True, index=True)  # stable ID used in the vector index
    uploaded_at      = Column(DateTime, default=_now, nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)       # groups messages into one conversation
    question   = Column(String, nullable=False)
    answer     = Column(String, nullable=False)
    sources    = Column(String)                   # JSON-encoded list of source filenames
    created_at = Column(DateTime, default=_now)


class Feedback(Base):
    __tablename__ = "feedback"

    id         = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False)
    rating     = Column(String, nullable=False)   # "up" or "down"
    created_at = Column(DateTime, default=_now)

"""Pydantic schemas for the /documents endpoints.

DocumentSummary      — one row in a GET /documents list response
DocumentUploadResponse — returned after a successful upload
DocumentDeleteResponse — returned after a successful delete
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentSummary(BaseModel):
    """Lightweight representation of a document — used in list responses."""

    # from_attributes lets Pydantic read values off SQLAlchemy model instances
    # directly, so we don't need to convert them to dicts manually.
    model_config = ConfigDict(from_attributes=True)

    id:          int
    filename:    str
    uploaded_at: datetime


class DocumentUploadResponse(DocumentSummary):
    """Returned after a successful upload — extends summary with processing details."""

    chunks_created: int   # how many text chunks were stored in the FAISS index
    status:         str   # always "uploaded and indexed" on success


class DocumentDeleteResponse(BaseModel):
    """Returned after a successful delete."""

    id:             int
    filename:       str
    chunks_removed: int   # number of vector index entries removed
    file_deleted:   bool  # False if the file was already gone from disk
    status:         str   # always "deleted" on success

"""
Shared test fixtures used by every test module.

pytest automatically discovers conftest.py and makes everything
defined here available to all tests without any imports needed.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import Base
from app.models import db_models  # ensures all models are registered with Base


# ---------------------------------------------------------------------------
# In-memory SQLite database (isolated per test session)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite://"  # pure in-memory, nothing persisted to disk

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def isolate_upload_directory(tmp_path, monkeypatch):
    """Keep upload tests from creating files in the real runtime data directory."""
    from app.api.v1 import documents as documents_api

    monkeypatch.setattr(documents_api, "UPLOAD_FOLDER", str(tmp_path / "uploads"))


@pytest.fixture(autouse=True)
def reset_database():
    """
    Drops and recreates all tables before every test so each test
    starts with a clean, empty database - no test can pollute another.
    """
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def db_session():
    """
    Provides a database session scoped to a single test.
    Rolls back on teardown so writes never leak between tests.
    """
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    """
    Provides a FastAPI TestClient that uses the in-memory test database
    instead of the real contextflow.db file on disk.
    """
    from app.db import database as db_module

    # Swap the real session factory for the test one
    original = db_module.SessionLocal
    db_module.SessionLocal = TestSessionLocal

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    # Restore the real session factory after the test
    db_module.SessionLocal = original

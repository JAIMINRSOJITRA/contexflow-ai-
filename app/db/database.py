"""Database engine, sessions, and schema management.

One engine is created at import time and shared across the app.
get_db() provides one session per HTTP request via FastAPI's Depends().
initialize_database() runs at startup to create tables and apply
lightweight schema additions without a full migration framework.
"""
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import DATABASE_URL


def _ensure_sqlite_parent_directory(database_url: str) -> None:
    """Create the directory that will hold the SQLite file, if needed.

    Does nothing for non-SQLite connection strings or in-memory databases.
    """
    if not database_url.startswith("sqlite:///"):
        return
    database_path = database_url.removeprefix("sqlite:///")
    if database_path and database_path != ":memory:":
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_directory(DATABASE_URL)

# SQLite needs check_same_thread=False because FastAPI uses a thread pool.
# Other databases (Postgres, etc.) don't need this option.
_engine_options = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield one SQLAlchemy session per request and always close it afterward.

    Used with FastAPI's Depends() pattern so routes never manage
    session lifecycle manually.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    """Create all tables and apply schema additions introduced after v0.1.

    Using ALTER TABLE for additive changes keeps the database usable
    without wiping it — a lightweight alternative to Alembic for a
    project at this scale.
    """
    Base.metadata.create_all(bind=engine)

    # Schema upgrades only apply to SQLite and only when the table already exists
    # (i.e., this is not a fresh database where create_all just ran).
    if engine.dialect.name != "sqlite" or "documents" not in inspect(engine).get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspect(engine).get_columns("documents")
    }
    # Columns added after the initial release — added here if missing.
    additions = {
        "storage_filename": "VARCHAR",
        "source_id": "VARCHAR",
    }
    with engine.begin() as connection:
        for name, column_type in additions.items():
            if name not in existing_columns:
                connection.execute(text(f"ALTER TABLE documents ADD COLUMN {name} {column_type}"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_documents_source_id ON documents (source_id)")
        )

"""Reset the database and FAISS index after explicit confirmation.

Run from the project root:
    python scripts/reset_db.py          # interactive — type RESET to confirm
    python scripts/reset_db.py --yes    # skip the prompt (useful in CI)

What gets deleted:
  - All rows in documents, chat_messages, and feedback tables
  - The FAISS index files (index.faiss and metadata.pkl)

What is NOT deleted:
  - The uploaded files in data/uploads/ (delete those manually if needed)
"""
import argparse
import sys
from pathlib import Path

# Add the project root to sys.path so app.* imports work when this
# script is run directly rather than as part of the installed package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import Base, engine, initialize_database
from app.models import db_models  # registers all models with Base before drop_all
from app.services.vector_store import reset_index


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Delete all ContextFlow AI database records and indexed vectors."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    args = parser.parse_args()

    if not args.yes:
        confirmation = input(
            "This deletes ALL document, chat, feedback, and vector data. Type RESET to confirm: "
        )
        if confirmation != "RESET":
            print("Reset cancelled.")
            return

    Base.metadata.drop_all(bind=engine)
    reset_index()
    initialize_database()  # recreates empty tables so the app is ready to use immediately
    print("Done. Tables and vector index have been reset. Uploaded files were NOT deleted.")


if __name__ == "__main__":
    main()

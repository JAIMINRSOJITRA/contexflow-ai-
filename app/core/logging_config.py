"""Logging configuration for the entire application.

Call setup_logging() once at startup (in main.py). After that, every
module can get its own logger with:

    from app.core.logging_config import get_logger
    logger = get_logger(__name__)

All loggers inherit the format and level set here automatically.
Output goes to stdout so Docker and cloud platforms capture it without
any extra configuration.
"""
import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """Configure the root logger with a consistent format.

    The 'force=True' flag overrides handlers that Uvicorn may have
    already attached before this runs.
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # removes any handlers Uvicorn added before main.py ran
    )

    # Third-party libraries that are very chatty at INFO level — silence them.
    for noisy_logger in ("httpx", "httpcore", "faiss", "urllib3"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.

    Usage in any file:
        logger = get_logger(__name__)
        logger.info("Something happened: %s", value)
    """
    return logging.getLogger(name)

"""Embedding providers: Gemini (default) via google-genai SDK, or Sentence-Transformers as a local fallback.

No LangChain here — the google-genai SDK is called directly, the same way
document_processor.py calls it for vision/OCR.
"""
from functools import lru_cache

from app.core.config import (
    EMBEDDING_PROVIDER,
    GEMINI_API_KEY,
    LOCAL_EMBEDDING_MODEL,
)

GEMINI_EMBEDDING_MODEL = "models/text-embedding-004"


def _gemini_client():
    """Build and return a google-genai Client, failing early with a clear message."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or set to its placeholder value. "
            "Configure it in .env, or set EMBEDDING_PROVIDER=sentence-transformers "
            "to use a free local model instead."
        )
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "Gemini embeddings require the google-genai package. "
            "Run: pip install -r requirements.txt"
        ) from exc
    return genai.Client(api_key=GEMINI_API_KEY)


@lru_cache(maxsize=1)
def _local_embedding_model():
    """Load the Sentence-Transformers model once and cache it for the process lifetime."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Local embeddings require sentence-transformers. "
            "Run: pip install -r requirements.txt"
        ) from exc
    return SentenceTransformer(LOCAL_EMBEDDING_MODEL)


def embed_text(text: str) -> list[float]:
    """Embed a single string using the configured provider.

    Returns a list of floats ready to hand straight to FAISS.
    """
    if EMBEDDING_PROVIDER == "gemini":
        client = _gemini_client()
        response = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=text,
        )
        return list(response.embeddings[0].values)

    # Local fallback — no API key or network required.
    return _local_embedding_model().encode(text, normalize_embeddings=True).tolist()


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    """Embed every chunk in the list, preserving their original order.

    Gemini accepts a batch in a single API call; Sentence-Transformers
    also batches internally, so either way this is one round-trip.
    """
    if not chunks:
        return []

    if EMBEDDING_PROVIDER == "gemini":
        client = _gemini_client()
        response = client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=chunks,
        )
        return [list(embedding.values) for embedding in response.embeddings]

    # Local fallback.
    vectors = _local_embedding_model().encode(chunks, normalize_embeddings=True)
    return vectors.tolist()

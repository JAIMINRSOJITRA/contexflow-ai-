"""Persistence helpers for the local FAISS vector index & Hybrid Search (Vector + Keyword RRF).

FAISS stores dense float vectors and can search millions of them in
milliseconds. We pair it with a metadata list (pickle) that maps each
vector's position in the index back to its source text and filename.

Hybrid Search (Reciprocal Rank Fusion - RRF):
  Combines dense vector similarity (FAISS) with lexical keyword matching (BM25 token search).
  Ensures both conceptual queries ("annual time off") and exact keyword matches
  ("INV-9021", "serial #") rank at the top of results.

Performance Optimization:
  Uses in-memory caching to avoid reloading FAISS index from disk on every operation.
"""
import math
import os
import pickle
import re

import faiss
import numpy as np

from app.core.config import METADATA_PATH, VECTOR_INDEX_PATH, HYBRID_SEARCH_MULTIPLIER, RRF_K

_FALLBACK_DIM = 768

# In-memory cache to avoid reloading FAISS index from disk on every operation
_index_cache = None
_metadata_cache = None
_cache_initialized = False


def _ensure_storage_directory() -> None:
    """Create the directory that will hold index.faiss and metadata.pkl."""
    directory = os.path.dirname(VECTOR_INDEX_PATH)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _load_index_from_disk():
    """Load the persisted index and metadata from disk."""
    if os.path.exists(VECTOR_INDEX_PATH) and os.path.exists(METADATA_PATH):
        index = faiss.read_index(VECTOR_INDEX_PATH)
        with open(METADATA_PATH, "rb") as f:
            metadata = pickle.load(f)
        if index.ntotal != len(metadata):
            raise RuntimeError(
                f"FAISS index has {index.ntotal} vectors but metadata has "
                f"{len(metadata)} entries. Delete both files and re-upload."
            )
        return index, metadata

    return faiss.IndexFlatL2(_FALLBACK_DIM), []


def _load_index():
    """Load the index and metadata, using in-memory cache when available."""
    global _index_cache, _metadata_cache, _cache_initialized
    
    # If cache is not initialized, load from disk
    if not _cache_initialized:
        _index_cache, _metadata_cache = _load_index_from_disk()
        _cache_initialized = True
    
    return _index_cache, _metadata_cache


def _invalidate_cache():
    """Clear the in-memory cache, forcing next load to read from disk."""
    global _index_cache, _metadata_cache, _cache_initialized
    _index_cache = None
    _metadata_cache = None
    _cache_initialized = False


def _save_index(index, metadata) -> None:
    """Save index and metadata to disk, then update the in-memory cache."""
    global _index_cache, _metadata_cache, _cache_initialized
    
    _ensure_storage_directory()
    faiss.write_index(index, VECTOR_INDEX_PATH)
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(metadata, f)
    
    # Update cache with the new index and metadata
    _index_cache = index
    _metadata_cache = metadata
    _cache_initialized = True


def add_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    filename: str,
    document_id: str | None = None,
) -> None:
    """Add document chunks and their embeddings to the persistent index."""
    if not embeddings:
        return
    if len(chunks) != len(embeddings):
        raise ValueError("Each text chunk must have exactly one embedding.")

    index, metadata = _load_index()
    dimension = len(embeddings[0])

    if index.ntotal == 0 and index.d != dimension:
        index = faiss.IndexFlatL2(dimension)

    if index.d != dimension:
        raise ValueError(
            f"Embedding dimension {dimension} does not match the existing "
            f"index dimension {index.d}. Delete the index files and re-upload."
        )

    vectors = np.ascontiguousarray(np.asarray(embeddings, dtype="float32"))
    index.add(vectors)

    stable_id = document_id or filename
    metadata.extend(
        {"text": chunk, "source": filename, "document_id": stable_id}
        for chunk in chunks
    )
    _save_index(index, metadata)


def has_chunks() -> bool:
    """Return True if at least one chunk has been indexed."""
    index, _ = _load_index()
    return index.ntotal > 0


def _tokenize(text: str) -> set[str]:
    """Extract clean lowercase word tokens for lexical keyword matching."""
    return set(re.findall(r"\w+", text.lower()))


def _lexical_search(query_text: str, metadata: list[dict[str, str]], top_n: int) -> list[int]:
    """Score chunks by keyword frequency and return indices of top matches."""
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return []

    scores = []
    for idx, item in enumerate(metadata):
        chunk_tokens = _tokenize(item.get("text", ""))
        match_count = sum(1 for token in query_tokens if token in chunk_tokens)
        if match_count > 0:
            scores.append((idx, match_count))

    # Sort descending by match count
    scores.sort(key=lambda x: x[1], reverse=True)
    return [idx for idx, _ in scores[:top_n]]


def search(
    query_embedding: list[float],
    query_text: str | None = None,
    top_k: int = 4,
) -> list[dict[str, str]]:
    """Return top_k results using Hybrid Search (Reciprocal Rank Fusion - RRF).

    Combines dense FAISS vector search with BM25-style lexical keyword search.
    If query_text is None, falls back to pure FAISS vector search.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    index, metadata = _load_index()
    if index.ntotal == 0:
        return []

    if len(query_embedding) != index.d:
        raise ValueError(
            f"Query embedding has {len(query_embedding)} dimensions but "
            f"the index expects {index.d}. Mismatched embedding models?"
        )

    # 1. Dense Vector Search (FAISS)
    search_count = min(top_k * HYBRID_SEARCH_MULTIPLIER, index.ntotal)
    query_vector = np.ascontiguousarray(np.asarray([query_embedding], dtype="float32"))
    _, dense_indices = index.search(query_vector, search_count)
    dense_valid = [idx for idx in dense_indices[0] if idx != -1]

    # If no query_text provided, return dense results directly
    if not query_text:
        return [metadata[i] for i in dense_valid[:top_k]]

    # 2. Lexical Keyword Search
    lexical_indices = _lexical_search(query_text, metadata, search_count)

    # 3. Reciprocal Rank Fusion (RRF)
    # RRF Score = 1 / (k + rank)  where k=RRF_K (configurable)
    scores: dict[int, float] = {}

    for rank, idx in enumerate(dense_valid):
        scores[idx] = scores.get(idx, 0.0) + (1.0 / (RRF_K + rank + 1))

    for rank, idx in enumerate(lexical_indices):
        scores[idx] = scores.get(idx, 0.0) + (1.0 / (RRF_K + rank + 1))

    # Sort candidates by combined RRF score descending
    sorted_candidates = sorted(scores.keys(), key=lambda i: scores[i], reverse=True)
    return [metadata[i] for i in sorted_candidates[:top_k]]


def remove_document_chunks(document_id: str) -> int:
    """Remove every chunk that belongs to one document and rebuild the index."""
    index, metadata = _load_index()

    to_remove = {
        i for i, item in enumerate(metadata)
        if item.get("document_id", item.get("source")) == document_id
    }
    if not to_remove:
        return 0

    kept = [i for i in range(len(metadata)) if i not in to_remove]
    rebuilt = faiss.IndexFlatL2(index.d)
    if kept:
        retained_vectors = np.ascontiguousarray(
            np.vstack([index.reconstruct(i) for i in kept]), dtype="float32"
        )
        rebuilt.add(retained_vectors)

    _save_index(rebuilt, [metadata[i] for i in kept])
    return len(to_remove)


def reset_index() -> None:
    """Delete the persisted index files entirely and clear the cache."""
    for path in (VECTOR_INDEX_PATH, METADATA_PATH):
        if os.path.exists(path):
            os.remove(path)
    
    # Clear the in-memory cache
    _invalidate_cache()

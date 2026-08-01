"""Splits text into overlapping, sentence-aware chunks for embedding and retrieval."""

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[str]:
    """
    Splits text into overlapping, sentence-aware chunks of roughly `chunk_size` characters.

    Uses recursive separator splitting (paragraphs '\\n\\n', line breaks '\\n',
    sentences '. ', spaces ' ') so chunk boundaries prefer natural language
    break points over arbitrary mid-sentence cuts.
    """
    chunk_size = CHUNK_SIZE if chunk_size is None else chunk_size
    chunk_overlap = CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap

    if not text or not text.strip():
        return []

    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be at least 0 and smaller than chunk_size")

    separators = ["\n\n", "\n", ". ", "? ", "! ", " "]

    def _split_text(content: str, current_separators: list[str]) -> list[str]:
        if len(content) <= chunk_size:
            return [content]

        if not current_separators:
            # Fallback: character-based sliding window if no separators remain
            results = []
            stride = max(1, chunk_size - chunk_overlap)
            start = 0
            while start < len(content):
                chunk = content[start : start + chunk_size]
                results.append(chunk)
                start += stride
            return results

        sep = current_separators[0]
        splits = content.split(sep)
        final_chunks = []
        current_chunk = []
        current_length = 0

        for i, piece in enumerate(splits):
            part = piece + (sep if i < len(splits) - 1 else "")
            if not part:
                continue

            if len(part) > chunk_size:
                if current_chunk:
                    final_chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                sub_chunks = _split_text(part, current_separators[1:])
                final_chunks.extend(sub_chunks)
            elif current_length + len(part) <= chunk_size:
                current_chunk.append(part)
                current_length += len(part)
            else:
                final_chunks.append("".join(current_chunk))
                # Build overlap buffer from previous chunks
                overlap_buf = []
                overlap_len = 0
                for item in reversed(current_chunk):
                    if overlap_len + len(item) <= chunk_overlap:
                        overlap_buf.insert(0, item)
                        overlap_len += len(item)
                    else:
                        break
                current_chunk = overlap_buf + [part]
                current_length = sum(len(x) for x in current_chunk)

        if current_chunk:
            final_chunks.append("".join(current_chunk))

        return [c for c in final_chunks if c]

    return _split_text(text, separators)

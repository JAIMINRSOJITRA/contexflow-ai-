"""RAG pipeline — retrieve relevant chunks, build a prompt, generate an answer.

Includes HyDE (Hypothetical Document Embeddings) Query Expansion,
Hybrid Vector + Lexical Search, and Enterprise Multi-Step Grounding.
"""
from app.core.config import TOP_K_RESULTS
from app.core.logging_config import get_logger
from app.services.embeddings import embed_text
from app.services.llm_provider import generate_answer
from app.services.vector_store import has_chunks, search

logger = get_logger(__name__)


def _build_prompt(question: str, matches: list[dict[str, str]]) -> str:
    """
    Assemble a high-grade, multi-step enterprise RAG prompt with Chain-of-Thought
    reasoning, strict source attribution, conflict resolution, and structured
    few-shot formatting.
    """
    context_blocks = "\n\n".join(
        f"[[DOCUMENT SOURCE #{idx + 1} | FILENAME: {match['source']}]]\n{match['text']}\n[[END DOCUMENT SOURCE #{idx + 1}]]"
        for idx, match in enumerate(matches)
    )

    return f"""SYSTEM ROLE & OBJECTIVE:
You are ContextFlow AI, an elite enterprise document intelligence engine. Your objective is to process retrieved context passages and deliver hyper-accurate, fully grounded, and structured answers to user inquiries.

=== MANDATORY GOVERNING RULES ===
1. ZERO HALLUCINATION & STRICT GROUNDING:
   - Your answer must be derived EXCLUSIVELY from facts explicitly mentioned in the provided Context.
   - Do NOT extrapolate, assume, infer unstated logical leaps, or introduce external training knowledge.
   - If the retrieved context is insufficient or silent on the question, respond ONLY with:
     "I cannot locate sufficient information in the indexed documents to answer this question."

2. SOURCE ATTRIBUTION & IN-LINE CITATION:
   - Every factual claim, number, or rule statement MUST include an in-line citation linking directly to its source file.
   - Citation Format: `[Source: <filename>]` (e.g., [Source: HR_Policy_2026.pdf]).

3. STRUCTURED RESPONSE LAYOUT:
   Format your response using the following structured section headings:
   - **Executive Summary**: A concise 1-2 sentence direct response.
   - **Detailed Breakdown**: Bulleted analysis with in-line source citations.
   - **Source References**: Bulleted list of every source file consulted.

4. CONFLICT & DISCREPANCY MANAGEMENT:
   - If two or more source passages provide conflicting information (e.g. differing dates, policies, or figures), explicitly identify the conflict and cite both sources.

=== FEW-SHOT DEMONSTRATION ===
[Example Input Context]
[[DOCUMENT SOURCE #1 | FILENAME: Security_Policy.pdf]]
All employees must rotate their passwords every 90 days. Multi-factor authentication is mandatory.
[[END DOCUMENT SOURCE #1]]

[Example User Question]
How often should passwords be changed?

[Example Model Output]
**Executive Summary**:
Passwords must be rotated every 90 days according to the corporate security guidelines [Source: Security_Policy.pdf].

**Detailed Breakdown**:
- **Rotation Schedule**: Passwords require mandatory rotation every 90 days [Source: Security_Policy.pdf].
- **Authentication**: Multi-factor authentication (MFA) is strictly enforced alongside password rules [Source: Security_Policy.pdf].

**Source References**:
- `Security_Policy.pdf`
=== END DEMONSTRATION ===

=== CURRENT TASK DATA ===
[RETRIEVED CONTEXT PASSAGES]
{context_blocks}

[USER QUESTION]
{question}

=== GENERATED RESPONSE ===:"""


def _generate_hypothetical_document(question: str, provider: str | None = None) -> str:
    """Generate a short hypothetical answer passage for HyDE query expansion.

    Translates short or vague user questions into a rich passage that aligns
    vector space closer to true document chunks.
    """
    hyde_prompt = (
        f"Write a short hypothetical document passage that directly answers the following question. "
        f"Output ONLY 1-2 factual sentences as if excerpted from a document.\n\n"
        f"Question: {question}\n\n"
        f"Passage:"
    )
    try:
        return generate_answer(hyde_prompt, provider=provider)
    except Exception as exc:
        logger.warning("HyDE expansion skipped due to provider error: %s", exc)
        return question


def answer_question(
    question: str,
    top_k: int | None = None,
    provider: str | None = None,
    use_hyde: bool = False,
) -> dict[str, str | list[str]]:
    """Retrieve document context and generate a grounded answer."""
    if not has_chunks():
        return {
            "answer": "I don't have any documents to search yet — upload one first.",
            "sources": [],
        }

    top_k = TOP_K_RESULTS if top_k is None else top_k

    # 1. Query Expansion via HyDE (Hypothetical Document Embeddings)
    if use_hyde:
        hypothetical_doc = _generate_hypothetical_document(question, provider=provider)
        search_text = f"{question}\n{hypothetical_doc}"
    else:
        search_text = question

    # 2. Vector Embedding & Hybrid Search (FAISS + Lexical BM25 RRF)
    question_embedding = embed_text(search_text)
    matches = search(question_embedding, query_text=question, top_k=top_k)

    logger.info(
        "Question: '%s' | Provider: %s | Chunks retrieved: %d",
        question,
        provider or "default",
        len(matches),
    )

    if not matches:
        return {
            "answer": "I could not find relevant information in the indexed documents.",
            "sources": [],
        }

    prompt = _build_prompt(question, matches)
    answer_text = generate_answer(prompt, provider=provider)

    # Deduplicate sources while preserving the order they were retrieved in.
    sources = list(dict.fromkeys(match["source"] for match in matches))

    return {"answer": answer_text, "sources": sources}

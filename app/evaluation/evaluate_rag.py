"""Ragas evaluation for single-turn ContextFlow AI responses.

WHY LANGCHAIN IS STILL HERE (and only here):
  Ragas (the evaluation library) requires LangChain-compatible LLM and
  Embeddings objects as its judge models — it is a hard internal dependency
  of the library itself, not a choice we made. Every other file in this
  codebase uses google-genai and groq SDKs directly.
  LangChain is imported in this file solely to satisfy Ragas, nowhere else.
"""
import asyncio
from collections.abc import Awaitable
from typing import Any, TypeVar

from app.core.config import GEMINI_API_KEY, GROQ_API_KEY
from app.core.logging_config import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


def _require_any_key() -> None:
    has_gemini = GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here"
    has_groq = GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here"
    if not has_gemini and not has_groq:
        raise ValueError(
            "Neither GEMINI_API_KEY nor GROQ_API_KEY is configured. "
            "Set at least one valid key in your .env file to run evaluations."
        )


def _run(coroutine: Awaitable[T]) -> T:
    """Run a Ragas async metric from this synchronous API and CLI boundary."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    raise RuntimeError("Ragas evaluation cannot run inside an active event loop.")


def _ragas_dependencies() -> tuple[Any, Any, Any, Any, Any]:
    try:
        from ragas import SingleTurnSample
        from ragas.metrics import (
            Faithfulness,
            LLMContextPrecisionWithoutReference,
            LLMContextRecall,
            ResponseRelevancy,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Ragas is not installed. Run pip install -r requirements.txt before evaluating."
        ) from exc
    return (
        SingleTurnSample,
        Faithfulness,
        ResponseRelevancy,
        LLMContextPrecisionWithoutReference,
        LLMContextRecall,
    )


def _ragas_judge_models() -> tuple[Any, Any]:
    """
    Return the LLM and embeddings objects that Ragas uses as its judge.

    Prefers Groq (fast, free tier) if GROQ_API_KEY is set.
    Falls back to Gemini if only GEMINI_API_KEY is available.
    Ragas requires LangChain-compatible objects — this is the only
    place in the entire codebase where langchain wrappers are imported.
    """
    _require_any_key()

    has_groq = GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here"
    has_gemini = GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here"

    if has_groq:
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:
            raise RuntimeError(
                "Ragas evaluation with Groq requires langchain-groq. "
                "Run: pip install langchain-groq"
            ) from exc

        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            temperature=0,
        )
    elif has_gemini:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise RuntimeError(
                "Ragas evaluation with Gemini requires langchain-google-genai. "
                "Run: pip install langchain-google-genai"
            ) from exc

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0,
        )

    # For embeddings, use HuggingFace (local, free, no API key needed)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
        except ImportError as exc:
            raise RuntimeError(
                "Ragas evaluation requires langchain-huggingface or langchain-community. "
                "Run: pip install langchain-huggingface"
            ) from exc

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return llm, embeddings


def _score_value(result: Any, metric_name: str) -> tuple[float, str]:
    value = getattr(result, "value", result)
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Ragas returned an invalid {metric_name} score.") from exc
    if not 0 <= score <= 1:
        raise ValueError(f"Ragas returned {metric_name} outside the 0 to 1 range.")
    reason = str(getattr(result, "reason", "Ragas metric completed."))
    return round(score, 4), reason


def evaluate_sample(
    question: str,
    answer: str,
    contexts: list[str],
    reference: str | None = None,
) -> dict[str, Any]:
    """Evaluate a response with the four Ragas metrics named in the README."""
    (
        SingleTurnSample,
        Faithfulness,
        ResponseRelevancy,
        LLMContextPrecisionWithoutReference,
        LLMContextRecall,
    ) = _ragas_dependencies()
    llm, embeddings = _ragas_judge_models()

    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=contexts,
        # Context recall requires a reference answer. When callers only have a
        # generated response, use it as a conservative proxy and expose that
        # choice in the returned detail.
        reference=reference or answer,
    )
    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "answer_relevancy": ResponseRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": LLMContextPrecisionWithoutReference(llm=llm),
        "context_recall": LLMContextRecall(llm=llm),
    }

    result: dict[str, Any] = {}
    details: dict[str, str] = {}
    for name, metric in metrics.items():
        score, reason = _score_value(_run(metric.single_turn_ascore(sample)), name)
        result[name] = score
        details[f"{name}_reason"] = reason

    if reference is None:
        details["context_recall_reference"] = (
            "The generated answer was used as the reference because none was provided."
        )
    logger.info("Completed Ragas evaluation for question: %s", question[:80])
    return {**result, "scores_detail": details}


def evaluate_batch(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate a list of samples while retaining each source question."""
    results = []
    for sample in samples:
        result = evaluate_sample(
            question=sample["question"],
            answer=sample["answer"],
            contexts=sample["contexts"],
            reference=sample.get("reference"),
        )
        result["question"] = sample["question"]
        results.append(result)
    return results

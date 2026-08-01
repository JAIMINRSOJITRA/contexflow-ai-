"""POST /api/v1/evaluate — score a RAG response with four Ragas metrics.

Metrics:
  faithfulness      : is the answer grounded in the retrieved context?
  answer_relevancy  : does the answer actually address the question?
  context_precision : are the retrieved chunks relevant to the question?
  context_recall    : do the chunks contain enough info to answer fully?

All four scores are floats in the 0–1 range. Higher is better.
Groq (Llama 3.3 70B) acts as the judge — a valid GROQ_API_KEY is required.

Request body:
    {
        "question": "What is the leave policy?",
        "answer":   "Employees get 18 days of paid leave.",
        "contexts": ["The company provides 18 days paid leave per year."]
    }

Response:
    {
        "faithfulness":      0.95,
        "answer_relevancy":  0.90,
        "context_precision": 0.85,
        "context_recall":    0.88,
        "scores_detail": { ... one reason string per metric ... }
    }
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.evaluation.evaluate_rag import evaluate_sample

logger = get_logger(__name__)
router = APIRouter()


class EvaluateRequest(BaseModel):
    question:  str        = Field(..., description="The original user question.")
    answer:    str        = Field(..., description="The generated answer to evaluate.")
    contexts:  list[str]  = Field(..., min_length=1, description="Retrieved text chunks used to generate the answer.")
    reference: str | None = Field(default=None, description="Optional known-correct answer for context recall scoring.")


@router.post("")
def evaluate(request: EvaluateRequest):
    """Run all four Ragas metrics and return the scores."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question cannot be empty.")
    if not request.answer.strip():
        raise HTTPException(status_code=400, detail="answer cannot be empty.")
    if not any(c.strip() for c in request.contexts):
        raise HTTPException(status_code=400, detail="at least one non-empty context is required.")

    try:
        result = evaluate_sample(
            question=request.question,
            answer=request.answer,
            contexts=request.contexts,
            reference=request.reference,
        )
    except Exception:
        logger.exception("Ragas evaluation failed.")
        raise HTTPException(
            status_code=502,
            detail="Evaluation failed — LLM judge API may be unavailable. Check your API keys in .env.",
        )

    return result

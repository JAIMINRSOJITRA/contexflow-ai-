"""Standalone RAG evaluation runner.

Runs a set of Q&A samples through the Ragas evaluator and prints a
formatted score report to the console.

Usage (from the project root):
    python scripts/run_evaluation.py

Requirements:
  - GEMINI_API_KEY set in .env (Gemini acts as the judge model)
  - At least one document already uploaded and indexed

Replace EVAL_SAMPLES below with real question/answer pairs from your
indexed documents. The "contexts" should be the actual chunks your
FAISS index returns for each question — you can get these by adding a
debug log to rag_pipeline.py temporarily.
"""
import os
import sys

# Add the project root to sys.path so app.* imports work when this
# script is run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.evaluation.evaluate_rag import evaluate_batch

# ---------------------------------------------------------------------------
# Replace these with real Q&A pairs from your indexed documents.
# ---------------------------------------------------------------------------
EVAL_SAMPLES = [
    {
        "question": "What is the annual paid leave entitlement?",
        "answer":   "Employees are entitled to 18 days of paid leave per year.",
        "contexts": [
            "All permanent employees are entitled to 18 days of paid annual leave per calendar year.",
            "Leave must be applied for at least 2 weeks in advance through the HR portal.",
        ],
    },
    {
        "question": "What is the process to apply for leave?",
        "answer":   "Leave should be applied for through the HR portal at least 2 weeks in advance.",
        "contexts": [
            "All permanent employees are entitled to 18 days of paid annual leave per calendar year.",
            "Leave must be applied for at least 2 weeks in advance through the HR portal.",
        ],
    },
    {
        # Example where the context doesn't support the answer — expect low faithfulness.
        "question": "What is the company refund policy?",
        "answer":   "Refunds are processed within 7 business days.",
        "contexts": [
            "All permanent employees are entitled to 18 days of paid annual leave per calendar year.",
            "Leave must be applied for at least 2 weeks in advance through the HR portal.",
        ],
    },
]


def print_report(results: list[dict]) -> None:
    """Print a formatted score report with per-sample details and averages."""
    divider = "-" * 72
    print("\n" + "=" * 72)
    print("  ContextFlow AI — RAG Evaluation Report")
    print("=" * 72)

    totals = {
        "faithfulness":      0.0,
        "answer_relevancy":  0.0,
        "context_precision": 0.0,
        "context_recall":    0.0,
    }

    for i, r in enumerate(results):
        detail = r["scores_detail"]
        print(f"\nSample {i + 1}: {r.get('question', '')[:60]}")
        print(divider)
        print(f"  Faithfulness       : {r['faithfulness']:.2f}  | {detail['faithfulness_reason']}")
        print(f"  Answer Relevancy   : {r['answer_relevancy']:.2f}  | {detail['answer_relevancy_reason']}")
        print(f"  Context Precision  : {r['context_precision']:.2f}  | {detail['context_precision_reason']}")
        print(f"  Context Recall     : {r['context_recall']:.2f}  | {detail['context_recall_reason']}")
        for key in totals:
            totals[key] += r[key]

    n = len(results)
    print("\n" + "=" * 72)
    print("  AVERAGES")
    print(divider)
    for key, label in [
        ("faithfulness",      "Faithfulness      "),
        ("answer_relevancy",  "Answer Relevancy  "),
        ("context_precision", "Context Precision "),
        ("context_recall",    "Context Recall    "),
    ]:
        print(f"  {label}: {totals[key] / n:.2f}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    print(f"Running evaluation on {len(EVAL_SAMPLES)} samples...")
    results = evaluate_batch(EVAL_SAMPLES)
    print_report(results)

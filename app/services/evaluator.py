"""Backward-compatible re-export for code that imports from app.services.evaluator.

The evaluation logic was moved to app.evaluation.evaluate_rag.
Any code that still imports from here will continue to work.
"""
from app.evaluation.evaluate_rag import evaluate_batch, evaluate_sample

__all__ = ["evaluate_sample", "evaluate_batch"]

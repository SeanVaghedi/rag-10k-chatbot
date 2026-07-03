"""Scoring / grading harness for evaluation runs.

Planned responsibilities:

- Run each question in :mod:`eval.questions` through the RAG pipeline and
  collect the generated answer plus retrieved sources.
- Score results along dimensions such as retrieval relevance (did the right
  company/year chunks surface?) and answer correctness (optionally via an
  LLM-as-judge grader against the reference note).
- Aggregate per-provider metrics so chat/embedding providers can be compared,
  and emit a summary report.
"""

from typing import List


def run_evaluation(pipeline: "object", questions: List[dict]) -> dict:
    """Run ``questions`` through ``pipeline`` and return scored results.

    To be implemented.
    """
    raise NotImplementedError

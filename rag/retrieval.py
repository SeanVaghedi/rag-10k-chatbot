"""Retrieval and RAG chain assembly.

Planned responsibilities:

- Wrap the FAISS vectorstore in a retriever (top-k / MMR, with optional
  per-company metadata filtering for targeted comparisons).
- Define the prompt template that instructs the LLM to answer strictly from
  retrieved 10-K context and to cite company/year/page.
- Assemble the end-to-end RAG chain (retrieve -> format context -> LLM) and
  return both the answer and its supporting source chunks.
"""

from typing import List, Tuple


def build_retriever(vectorstore: "object", k: int = 5) -> "object":
    """Create a retriever over ``vectorstore``. To be implemented."""
    raise NotImplementedError


def answer_question(
    question: str,
    retriever: "object",
    llm: "object",
) -> Tuple[str, List["object"]]:
    """Answer ``question`` from retrieved 10-K context.

    Returns the generated answer plus the list of source chunks used, so the UI
    can display citations. To be implemented.
    """
    raise NotImplementedError

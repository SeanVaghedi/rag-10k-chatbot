"""Document chunking for the 10-K corpus.

Planned responsibilities:

- Split loaded ``Document`` objects into retrieval-sized chunks using a
  recursive/token-aware splitter (``RecursiveCharacterTextSplitter`` with a
  ``tiktoken`` length function) for consistent chunk token budgets.
- Preserve source metadata (company, year, page) on every chunk so citations
  survive the split.
- Expose configurable chunk size and overlap to tune retrieval granularity.
"""

from typing import List


def chunk_documents(
    documents: List["object"],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List["object"]:
    """Split ``documents`` into overlapping, token-aware chunks.

    Returns a list of chunk ``Document`` objects with metadata preserved.
    To be implemented.
    """
    raise NotImplementedError

"""Token-aware chunking for the 10-K corpus.

Splits page-level ``Document`` objects into retrieval-sized chunks using
``RecursiveCharacterTextSplitter`` with a tiktoken length function, so
``chunk_size`` / ``chunk_overlap`` are measured in **tokens**, not characters.
All page metadata (company, year, source_filename, page) is preserved on every
resulting chunk.

``chunk_size`` and ``chunk_overlap`` are parameters so they can be swept during
the Stage 2 comparison.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# tiktoken encoding used purely as a length function. cl100k_base is a
# reasonable, provider-neutral token proxy for measuring chunk sizes.
_TIKTOKEN_ENCODING = "cl100k_base"


def chunk_documents(
    docs: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> List[Document]:
    """Split ``docs`` into token-aware, overlapping chunks.

    Args:
        docs: Page-level documents (typically from ``load_10k_pdfs``).
        chunk_size: Target chunk length in tokens.
        chunk_overlap: Overlap between consecutive chunks, in tokens.

    Returns:
        A list of chunk ``Document`` objects with all source metadata preserved.
    """
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=_TIKTOKEN_ENCODING,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    # split_documents copies each source document's metadata onto its chunks.
    return splitter.split_documents(docs)

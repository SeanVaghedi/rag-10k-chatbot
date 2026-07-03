"""Retrieval and RAG prompt assembly for 10-K question answering.

Provides:

- :func:`build_retriever` — a top-k similarity retriever over the FAISS index.
- :data:`RAG_PROMPT` — a ChatPromptTemplate tuned for grounded, citation-aware
  answers over the Alphabet / Amazon / Microsoft 10-K filings.
- :func:`format_docs` — renders retrieved chunks (with company/year/page
  metadata) into the context string the model cites from.
"""

from __future__ import annotations

from typing import Sequence

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore


def build_retriever(vectorstore: VectorStore, k: int = 5) -> BaseRetriever:
    """Return a similarity-search retriever yielding the top-``k`` chunks."""
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})


def format_docs(docs: Sequence[Document]) -> str:
    """Format retrieved chunks into a numbered, citation-friendly context block.

    Each chunk is prefixed with a header carrying its company, fiscal year, page,
    and source file so the model can attribute every figure it cites.
    """
    blocks = []
    for i, doc in enumerate(docs, start=1):
        meta = doc.metadata
        company = str(meta.get("company", "unknown")).title()
        year = meta.get("year", "unknown")
        page = meta.get("page", "unknown")
        source = meta.get("source_filename", "unknown")
        header = f"[{i}] {company} — FY{year}, page {page} ({source})"
        blocks.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(blocks)


_SYSTEM_PROMPT = """You are a financial analyst assistant that answers questions about the annual \
10-K filings of Alphabet (Google), Amazon, and Microsoft. You are given retrieved excerpts from \
these filings; each excerpt begins with a source header of the form \
"[n] Company — FY<year>, page <p> (<file>)".

Follow these rules:

1. FISCAL YEAR ACCURACY: The fiscal year an excerpt reports is the FY<year> shown in its source \
header, NOT any year written inside the excerpt text. 10-K tables present two to three years of \
comparative data, so a year appearing inline is often a prior comparative period. When you state \
which year a figure belongs to, use the fiscal year from the source header of the excerpt the \
figure came from. If the question does not specify a year, answer for the most recent reporting \
year available in the context and state which year that is.

2. FISCAL YEAR ENDS DIFFER: Microsoft's fiscal year ends June 30; Amazon's and Alphabet's end \
December 31. State the specific period end when citing a figure (e.g. "for the fiscal year ended \
June 30, 2025"). When comparing across companies, note that Microsoft's fiscal year covers a \
different 12-month window if it is material to the comparison.

3. GROUNDING: Answer only from the provided excerpts. If the answer is not in the context, say so \
explicitly. Do not fill gaps from general knowledge, and never estimate or infer a figure that is \
not present.

4. NUMBER PRECISION: Quote figures exactly as they appear, with their units and scale \
(e.g. "$82,312 million"). When a figure is a composite (e.g. "cash, cash equivalents, and \
restricted cash"), state exactly what it includes; do not relabel it as a narrower item.

5. COMPANY SEPARATION: Never attribute one company's figure to another. If the context lacks a \
figure for a specifically named company, say so rather than substituting another company's number.

6. INSUFFICIENT CONTEXT: If the retrieved context is partial or ambiguous, state what is available \
and what is missing rather than guessing.

Be concise and factual. Do not add hedging language beyond stating when the context is \
insufficient."""

_HUMAN_PROMPT = """Context excerpts from the 10-K filings (each begins with its source header, \
including the filing's fiscal year):

{context}

Question: {question}

Answer using only the excerpts above. When stating which fiscal year a figure is from, use the \
FY<year> in that excerpt's source header, not a year written inline in the text."""

# The RAG prompt used by the pipeline. Expects `context` and `question` vars.
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ]
)

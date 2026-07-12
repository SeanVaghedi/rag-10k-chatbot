"""Retrieval and RAG prompt assembly for 10-K question answering.

Provides:

- :func:`build_retriever` — a top-k similarity retriever over the FAISS index.
- :func:`rewrite_query` — LLM query expansion into diverse, 10-K-vocabulary
  search queries (multi-query retrieval).
- :func:`merge_ranked_lists` — round-robin merge + dedupe of per-query results.
- :func:`mmr_rerank` — MMR reranking of a merged candidate pool against the
  original question, using vectors reconstructed from the FAISS index.
- :data:`RAG_PROMPT` — a ChatPromptTemplate tuned for grounded, citation-aware
  answers over the Alphabet / Amazon / Microsoft 10-K filings.
- :func:`format_docs` — renders retrieved chunks (with company/year/page
  metadata) into the context string the model cites from.
"""

from __future__ import annotations

import json
import re
from typing import List, Sequence

import numpy as np
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import maximal_marginal_relevance
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore


def build_retriever(vectorstore: VectorStore, k: int = 5) -> BaseRetriever:
    """Return a similarity-search retriever yielding the top-``k`` chunks."""
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})


# ---------------------------------------------------------------------------
# Query rewriting (multi-query retrieval)
# ---------------------------------------------------------------------------
_REWRITE_SYSTEM = """You generate search queries for a retrieval system over the annual 10-K \
filings of Alphabet (Google), Amazon, and Microsoft.

Rewrite the user's question into exactly {num_queries} diverse search queries that maximize the \
chance of retrieving the passages needed to answer it. Rules:

1. Use the vocabulary that appears in 10-K filings: e.g. "net sales", "total revenues", "segment \
operating income", "fiscal year ended", "cash and cash equivalents", and official segment names \
("AWS", "Google Cloud", "Intelligent Cloud", "North America segment").
2. Each query must take a different angle — different metric name, statement, or section — not be \
a trivial paraphrase of the others.
3. If the question involves more than one company (a comparison, or "all three companies"), \
dedicate queries to specific companies — roughly one query per company, naming the company \
explicitly — so every company's filing is searched, not just the one the embedding happens to \
favor.
4. Keep each query short (3–12 words): these are search strings, not sentences.

Return ONLY a JSON array of {num_queries} strings, with no other text."""

QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _REWRITE_SYSTEM),
        ("human", "Question: {question}"),
    ]
)


def _parse_rewritten_queries(text: str, limit: int) -> List[str]:
    """Extract up to ``limit`` query strings from the rewriter's raw output.

    Tries the requested JSON-array format first (tolerating markdown fences and
    surrounding prose); falls back to treating each non-empty line as a query
    (stripping bullets/numbering/quotes). Returns ``[]`` if nothing usable.
    """
    cleaned = re.sub(r"```[a-zA-Z]*", "", text or "").strip()

    start, end = cleaned.find("["), cleaned.rfind("]")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(data, list):
                # A parsed JSON list is authoritative — even if it yields no
                # usable strings, don't fall through and scrape junk lines.
                queries = [q.strip() for q in data if isinstance(q, str) and q.strip()]
                return queries[:limit]

    queries = []
    for line in cleaned.splitlines():
        line = re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line.strip()).strip("\"' ")
        if line:
            queries.append(line)
    return queries[:limit]


def _message_text(content: object) -> str:
    """Flatten a chat message's ``content`` to plain text.

    Providers may return a plain string or a list of content blocks (e.g.
    Gemini returns ``[{"type": "text", "text": ...}, ...]`` when thinking is
    enabled); only the text blocks matter here.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return str(content)


def rewrite_query(llm: BaseChatModel, question: str, num_queries: int = 3) -> List[str]:
    """Expand ``question`` into up to ``num_queries`` 10-K-vocabulary search queries.

    One extra LLM call. Never raises: on any failure (provider error, unparsable
    output) it returns ``[]`` and the caller falls back to searching the
    original question alone.
    """
    try:
        response = llm.invoke(
            QUERY_REWRITE_PROMPT.format_messages(
                question=question, num_queries=num_queries
            )
        )
        text = _message_text(response.content)
        return _parse_rewritten_queries(text, limit=num_queries)
    except Exception:  # noqa: BLE001 - a failed rewrite must never fail the question
        return []


# ---------------------------------------------------------------------------
# Multi-query merge + MMR reranking
# ---------------------------------------------------------------------------
def _doc_key(doc: Document) -> str:
    """Dedupe key for a retrieved chunk: its docstore id, else its content."""
    return doc.id or doc.page_content


def merge_ranked_lists(ranked_lists: Sequence[Sequence[Document]]) -> List[Document]:
    """Merge per-query result lists round-robin, deduplicating chunks.

    Interleaves by rank (every query's #1 result before any query's #2) so that
    when the merged list is truncated without reranking, each query contributes
    its best hits fairly instead of the first query dominating.
    """
    merged: List[Document] = []
    seen: set = set()
    max_len = max((len(lst) for lst in ranked_lists), default=0)
    for rank in range(max_len):
        for lst in ranked_lists:
            if rank < len(lst):
                doc = lst[rank]
                key = _doc_key(doc)
                if key not in seen:
                    seen.add(key)
                    merged.append(doc)
    return merged


def mmr_rerank(
    vectorstore: FAISS,
    embeddings: Embeddings,
    question: str,
    candidates: Sequence[Document],
    k: int = 5,
    lambda_mult: float = 0.5,
) -> List[Document]:
    """Rerank ``candidates`` against the ORIGINAL ``question`` with MMR; keep top-``k``.

    Chosen over an LLM relevance-scoring pass because it adds no LLM call (query
    rewriting already adds one), has no output-parsing failure mode, and reuses
    the vectors already stored in the FAISS index: each candidate's embedding is
    reconstructed from the index via its docstore id, so the only new network
    call is embedding the question itself. MMR's relevance term keeps the chunks
    closest to the original question; its diversity term stops near-duplicate
    chunks from one filing crowding out another company's passages — the failure
    mode behind comparison-question retrieval misses.

    Falls back to the first ``k`` candidates (merged rank order) if any
    candidate's vector cannot be recovered from the index.
    """
    if len(candidates) <= k:
        return list(candidates)

    try:
        id_to_pos = {
            doc_id: pos for pos, doc_id in vectorstore.index_to_docstore_id.items()
        }
        vectors = []
        for doc in candidates:
            pos = id_to_pos.get(doc.id) if doc.id else None
            if pos is None:
                return list(candidates)[:k]
            vectors.append(vectorstore.index.reconstruct(int(pos)))
        query_vec = np.array([embeddings.embed_query(question)], dtype=np.float32)
    except Exception:  # noqa: BLE001 - reranking is best-effort, never fail retrieval
        return list(candidates)[:k]

    selected = maximal_marginal_relevance(
        query_vec, vectors, k=k, lambda_mult=lambda_mult
    )
    return [candidates[i] for i in selected]


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
figure came from — except for figures inside a multi-year financial-statement table, which belong \
to their own column's year (see rule 2). If the question does not specify a year, answer for the \
most recent reporting year available in the context and state which year that is.

2. PRIOR-YEAR COMPARATIVES ARE ANSWERABLE: 10-K financial statements always present multiple \
fiscal years of comparative data side by side (typically two to three — a FY2025 filing shows \
e.g. 2023, 2024, and 2025 columns). These prior-year columns are valid, authoritative source data. \
If asked for a fiscal 2024 figure and the retrieved context is from the FY2025 filing, read the \
2024 column of the comparative statement and answer — do NOT respond that a "fiscal 2024 filing" \
is unavailable; the comparative column IS the fiscal 2024 data. Treat a figure as unavailable only \
when it genuinely appears in no column of the retrieved context, never merely because no \
standalone filing exists for that year. Genuinely out-of-scope questions (future projections, \
companies not in the corpus) must still be declined per GROUNDING.

3. FISCAL YEAR ENDS DIFFER: Microsoft's fiscal year ends June 30; Amazon's and Alphabet's end \
December 31. State the specific period end when citing a figure (e.g. "for the fiscal year ended \
June 30, 2025"). When comparing across companies, note that Microsoft's fiscal year covers a \
different 12-month window if it is material to the comparison.

4. GROUNDING: Answer only from the provided excerpts. If the answer is not in the context, say so \
explicitly. Do not fill gaps from general knowledge, and never estimate or infer a figure that is \
not present.

5. NUMBER PRECISION: Quote figures exactly as they appear, with their units and scale \
(e.g. "$82,312 million"). When a figure is a composite (e.g. "cash, cash equivalents, and \
restricted cash"), state exactly what it includes; do not relabel it as a narrower item.

6. COMPANY SEPARATION: Never attribute one company's figure to another. If the context lacks a \
figure for a specifically named company, say so rather than substituting another company's number.

7. INSUFFICIENT CONTEXT: If the retrieved context is partial or ambiguous, state what is available \
and what is missing rather than guessing.

8. CITATIONS: Support every claim with an inline citation to the numbered excerpt(s) you used. Put \
the excerpt number(s) in square brackets right after the statement — e.g. "Amazon's total net sales \
were $X in fiscal 2024 [2]" or "[1, 3]" when a statement draws on more than one excerpt. Cite ONLY \
the excerpts you actually relied on; never cite an excerpt you did not use. If the context does not \
contain the answer, say so and cite no excerpt.

Be concise and factual. Do not add hedging language beyond stating when the context is \
insufficient."""

_HUMAN_PROMPT = """Context excerpts from the 10-K filings (each begins with its source header, \
including the filing's fiscal year):

{context}

Question: {question}

Answer using only the excerpts above. When stating which fiscal year a figure is from, use the \
FY<year> in that excerpt's source header, not a year written inline in the text. Cite the excerpt \
number(s) in square brackets after each claim (e.g. [2] or [1, 3]), and cite only the excerpts you \
used."""

# The RAG prompt used by the pipeline. Expects `context` and `question` vars.
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ]
)

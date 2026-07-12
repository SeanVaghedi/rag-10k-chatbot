"""End-to-end RAG pipeline over the 10-K corpus.

``RagPipeline`` wires together a persisted FAISS index, a retrieval stage
(optionally with LLM query rewriting and MMR reranking), the provider's chat
model, and the grounded 10-K prompt into a single LCEL chain, and exposes
:meth:`ask` to answer a question with its supporting sources.

Retrieval flow (both stages toggleable for A/B evals):

1. Query rewriting (``use_query_rewriting``, default OFF): the LLM expands the
   question into up to 3 diverse, 10-K-vocabulary search queries
   (company-specific for cross-company questions); the original question is
   always searched too.
2. Candidate pool: top results are retrieved for every query and merged with
   round-robin dedup — ~``fetch_k`` candidates when reranking is on.
3. MMR reranking (``use_reranking``, default ON): candidates are reranked
   against the ORIGINAL question (relevance + diversity) and only the top
   ``k`` are passed to the LLM, so the final context size is unchanged.

With both toggles off the pipeline is the original plain top-k similarity
search.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import AsyncIterator, Dict, List, Tuple, Union

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough

from config.factory import get_chat_model, get_embeddings
from config.providers import get_config
from rag.retrieval import (
    RAG_PROMPT,
    format_docs,
    merge_ranked_lists,
    mmr_rerank,
    rewrite_query,
)
from rag.vectorstore import index_exists, load_vectorstore, persist_dir_for

# A source is the attribution metadata for one retrieved chunk.
Source = Dict[str, object]

# Inline citation markers in the answer text, e.g. "[1]" or "[2, 3]". Only
# digits/commas/whitespace inside the brackets, so "[note]" or "[3.5]" won't match.
_CITATION_RE = re.compile(r"\[([\d,\s]+)\]")


class RagPipeline:
    """Answer 10-K questions for one provider config, grounded in its index.

    Args:
        config_name: Named provider config (see ``config.providers.REGISTRY``).
        k: Number of chunks passed to the LLM per question (final context size).
        chunk_size / chunk_overlap: Chunking params used when the index was
            built; they select which persisted index to load.
        use_query_rewriting: Expand the question into diverse 10-K-vocabulary
            search queries with one extra LLM call before retrieving (default
            False — see the A/B note on the constructor defaults). Adds
            roughly 1-3s latency per question when enabled.
        use_reranking: Retrieve a larger candidate pool (~``fetch_k``) and MMR-
            rerank it against the original question, keeping only the top ``k``
            (default True).
        fetch_k: Target size of the merged candidate pool when reranking.
        mmr_lambda: MMR relevance/diversity trade-off (1.0 = pure relevance,
            0.0 = pure diversity).

    Raises:
        KeyError: if ``config_name`` is unknown.
        FileNotFoundError: if the index for this config has not been built yet.
    """

    def __init__(
        self,
        config_name: str = "gemini_native",
        k: int = 5,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        # Defaults set by A/B eval (gemini_native, 16-question gold set, two
        # runs per arm): baseline 80% key-facts @ ~8s; query rewriting 91.7%
        # (varied 100%/91.7% between runs) @ ~16s; MMR reranking 91.7% (stable)
        # @ ~7.5s; both 100%/91.7% @ ~40s. Reranking matches rewriting's
        # retrieval quality with no extra LLM call, no run-to-run variance, and
        # roughly half the latency — so reranking is ON and rewriting is OFF in
        # production. Both toggles stay for A/B reruns (eval/run_eval.py).
        use_query_rewriting: bool = False,
        use_reranking: bool = True,
        fetch_k: int = 20,
        mmr_lambda: float = 0.5,
    ) -> None:
        self.config_name = config_name
        self.config = get_config(config_name)
        self.persist_dir = persist_dir_for(config_name, chunk_size, chunk_overlap)
        self.k = k
        self.use_query_rewriting = use_query_rewriting
        self.use_reranking = use_reranking
        self.fetch_k = fetch_k
        self.mmr_lambda = mmr_lambda

        if not index_exists(self.persist_dir):
            raise FileNotFoundError(
                f"No FAISS index for config '{config_name}' at '{self.persist_dir}'. "
                f"Build it first:\n"
                f"    python scripts/build_index.py --config {config_name} "
                f"--chunk-size {chunk_size} --chunk-overlap {chunk_overlap}"
            )

        # Kept on self: reranking embeds the original question at query time.
        self.embeddings = get_embeddings(self.config)
        self.vectorstore = load_vectorstore(self.persist_dir, self.embeddings)
        self.llm = get_chat_model(self.config)
        # Shared answer sub-chain (expects {context, question}); reused by the
        # full ask() chain and by astream() so there is one grounding path.
        self._answer_chain = RAG_PROMPT | self.llm | StrOutputParser()
        self._chain = self._build_chain()

        if use_query_rewriting:
            print(
                f"[{config_name}] Note: query rewriting is enabled -- each question "
                "makes one extra LLM call before retrieval (expect roughly +1-3s "
                "latency per question). Disable with use_query_rewriting=False."
            )

    def _retrieve(self, question: str) -> List[Document]:
        """Retrieve the final ``k`` chunks for ``question``.

        Applies query rewriting and/or MMR reranking per the pipeline toggles;
        with both off this is exactly the original top-``k`` similarity search.
        """
        queries = [question]
        if self.use_query_rewriting:
            seen = {question.strip().lower()}
            for q in rewrite_query(self.llm, question):
                if q.strip().lower() not in seen:
                    seen.add(q.strip().lower())
                    queries.append(q)

        # Per-query depth: with reranking, split the ~fetch_k candidate budget
        # across the queries; without it, each query fetches k and the merged
        # round-robin list is truncated to k.
        if self.use_reranking:
            per_query = max(self.k, math.ceil(self.fetch_k / len(queries)))
        else:
            per_query = self.k

        ranked_lists = [
            self.vectorstore.similarity_search(q, k=per_query) for q in queries
        ]
        candidates = merge_ranked_lists(ranked_lists)

        if self.use_reranking:
            return mmr_rerank(
                self.vectorstore,
                self.embeddings,
                question,
                candidates,
                k=self.k,
                lambda_mult=self.mmr_lambda,
            )
        return candidates[: self.k]

    def _build_chain(self):
        """Compose the retrieve -> format -> prompt -> LLM chain with LCEL.

        The chain maps a question string to ``{"answer": str, "docs": [...]}`` so
        the caller gets both the generated answer and the chunks it was grounded
        in (for source attribution).
        """
        generate_answer = (
            RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))
            | self._answer_chain
        )
        return RunnableParallel(
            docs=RunnableLambda(self._retrieve),
            question=RunnablePassthrough(),
        ) | RunnableParallel(
            answer=generate_answer,
            docs=lambda x: x["docs"],
        )

    @staticmethod
    def _to_source(doc: Document) -> Source:
        meta = doc.metadata
        return {
            "company": meta.get("company"),
            "year": meta.get("year"),
            "page": meta.get("page"),
            "source_filename": meta.get("source_filename"),
            # Raw chunk text, so the frontend can try to highlight it on the page.
            "chunk_text": doc.page_content,
        }

    @classmethod
    def _cited_sources(cls, answer: str, docs: List[Document]) -> List[Source]:
        """Return sources for only the chunks the answer cites, first-cited order.

        Parses inline markers like ``[1]`` / ``[2, 3]`` from ``answer`` and keeps
        only those excerpt numbers (1-based, within range). Retrieved-but-uncited
        chunks are dropped; if the answer cites nothing, returns an empty list.
        """
        order: List[int] = []
        seen: set = set()
        for match in _CITATION_RE.finditer(answer or ""):
            for num in re.findall(r"\d+", match.group(1)):
                idx = int(num)
                if 1 <= idx <= len(docs) and idx not in seen:
                    seen.add(idx)
                    order.append(idx)
        return [cls._to_source(docs[i - 1]) for i in order]

    def ask(self, question: str) -> Tuple[str, List[Source]]:
        """Answer ``question`` from the indexed 10-Ks.

        Returns:
            ``(answer, sources)`` where ``sources`` lists the company / year /
            page (and source file) of each retrieved chunk used.
        """
        result = self._chain.invoke(question)
        answer: str = result["answer"]
        sources = self._cited_sources(answer, result["docs"])
        return answer, sources

    async def astream(self, question: str) -> AsyncIterator[Union[str, List[Source]]]:
        """Stream the answer token-by-token, then yield the source list.

        Async counterpart to :meth:`ask` (which is left unchanged). Retrieval
        happens first, then the answer is streamed from the shared answer chain.

        Yields:
            ``str`` tokens of the answer as they are generated, followed by a
            single final ``List[Source]`` with the retrieved chunks used.
            Consumers distinguish by type: ``str`` -> answer token,
            ``list`` -> the final sources.
        """
        # Retrieval (incl. the optional rewrite LLM call and MMR pass) is
        # synchronous; run it in a worker thread to keep the event loop free.
        docs = await asyncio.to_thread(self._retrieve, question)
        context = format_docs(docs)
        parts: List[str] = []
        async for token in self._answer_chain.astream(
            {"context": context, "question": question}
        ):
            if token:
                parts.append(token)
                yield token
        # Surface only the chunks the finished answer actually cited.
        yield self._cited_sources("".join(parts), docs)

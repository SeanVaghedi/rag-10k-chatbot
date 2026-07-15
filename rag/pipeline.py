"""End-to-end RAG pipeline over the 10-K corpus.

``RagPipeline`` wires together a persisted FAISS index, a retrieval stage
(optionally with LLM query rewriting and MMR reranking), the provider's chat
model, and the grounded 10-K prompt into a single LCEL chain, and exposes
:meth:`ask` to answer a question with its supporting sources.

Retrieval flow (both stages toggleable for A/B evals):

1. Query rewriting (``use_query_rewriting``, default ON): the LLM DECOMPOSES
   the question into up to 10 targeted, 10-K-vocabulary search queries — one
   per company-metric pair for multi-entity questions (plus segment-flavored
   queries when business segments are involved), so every company's filing is
   searched; just a couple of rephrasings for single-entity questions. The
   original question is always searched too.
2. Candidate pool: top results are retrieved PER query and merged with
   round-robin dedup — at least ~``fetch_k`` candidates when reranking is on.
3. MMR reranking (``use_reranking``, default ON): the merged pool is reranked
   against the ORIGINAL question (relevance + diversity) and only the top
   ``k`` are passed to the LLM, so the final context size is fixed at ``k``.

With both toggles off the pipeline is the original plain top-k similarity
search.
"""

from __future__ import annotations

import asyncio
import math
import re
from typing import AsyncIterator, Callable, Dict, List, Optional, Tuple, Union

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

# A progress event describing a real pipeline stage as it executes:
# {"stage": <id>, "label": <short human string>, "detail": {...}?}. Stage ids:
# rewriting, embedding, searching, reranking, reading, composing — each emitted
# only when that stage actually runs.
ProgressEvent = Dict[str, object]
ProgressCallback = Callable[[ProgressEvent], None]


def _reading_label(docs: List[Document]) -> str:
    """Human label naming the actual filings/pages selected for the context.

    One doc -> "Reading Amazon 10-K, page 60"; several -> "Reading Amazon
    (p.60, p.63), Microsoft (p.144)". Companies keep selection (relevance)
    order; duplicate pages collapse.
    """
    order: List[str] = []
    pages: Dict[str, List[object]] = {}
    for doc in docs:
        company = str(doc.metadata.get("company") or "unknown").title()
        page = doc.metadata.get("page")
        if company not in pages:
            pages[company] = []
            order.append(company)
        if page is not None and page not in pages[company]:
            pages[company].append(page)

    if len(docs) == 1:
        company = order[0]
        page_list = pages[company]
        if page_list:
            return f"Reading {company} 10-K, page {page_list[0]}"
        return f"Reading {company} 10-K"

    parts = []
    for company in order:
        page_list = pages[company]
        if page_list:
            parts.append(f"{company} ({', '.join(f'p.{p}' for p in page_list)})")
        else:
            parts.append(company)
    return "Reading " + ", ".join(parts)

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
        use_query_rewriting: Decompose the question into targeted 10-K
            search queries (one per company-metric pair for multi-entity
            questions) with one extra LLM call before retrieving (default
            True — see the note on the constructor defaults). Adds roughly
            1-3s latency per question when enabled.
        use_reranking: Retrieve a larger candidate pool (>= ``fetch_k``) and
            MMR-rerank it against the original question, keeping only the top
            ``k`` (default True).
        fetch_k: Minimum target size of the merged candidate pool when
            reranking; each sub-query additionally fetches at least ``k`` so
            decomposed multi-entity questions build a proportionally larger
            pool.
        mmr_lambda: MMR relevance/diversity trade-off (1.0 = pure relevance,
            0.0 = pure diversity).

    Raises:
        KeyError: if ``config_name`` is unknown.
        FileNotFoundError: if the index for this config has not been built yet.
    """

    def __init__(
        self,
        config_name: str = "gemini_native",
        k: int = 10,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        # Defaults history. The original A/B eval (gemini_native, 16-question
        # gold set, two runs per arm) picked reranking ON / rewriting OFF:
        # baseline 80% key-facts @ ~8s; query rewriting 91.7% (varied
        # 100%/91.7% between runs) @ ~16s; MMR reranking 91.7% (stable) @
        # ~7.5s; both 100%/91.7% @ ~40s. The hard multi-company tier then
        # exposed the cost of that choice: a question naming three companies
        # embeds near ONE company's passages, so retrieval surfaced 1-2
        # companies and the LLM correctly reported the rest missing. Fix:
        # rewriting is now ON by default and DECOMPOSES multi-entity questions
        # into per company-metric sub-queries (see rag.retrieval), with k
        # raised 5 -> 10 and fetch_k 20 -> 40 so multi-figure answers keep
        # enough distinct passages after reranking. Both toggles stay for A/B
        # reruns (eval/run_eval.py).
        use_query_rewriting: bool = True,
        use_reranking: bool = True,
        fetch_k: int = 40,
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
                f"[{config_name}] Note: query decomposition is enabled (production "
                "default) -- each question makes one extra LLM call before "
                "retrieval (expect roughly +1-3s latency per question). Disable "
                "with use_query_rewriting=False."
            )

    def _retrieve(
        self, question: str, on_progress: Optional[ProgressCallback] = None
    ) -> List[Document]:
        """Retrieve the final ``k`` chunks for ``question``.

        Applies query rewriting and/or MMR reranking per the pipeline toggles;
        with both off this is exactly the original top-``k`` similarity search.

        ``on_progress`` (optional) is called with a :data:`ProgressEvent` as
        each stage actually starts — never on a timer, and never for a stage
        that does not run (e.g. no "reranking" event with reranking disabled).
        The sync :meth:`ask` path passes no callback and behaves as before.
        """

        def emit(stage: str, label: str, **detail: object) -> None:
            if on_progress is not None:
                event: ProgressEvent = {"stage": stage, "label": label}
                if detail:
                    event["detail"] = detail
                on_progress(event)

        queries = [question]
        if self.use_query_rewriting:
            emit("rewriting", "Expanding your question into search queries")
            seen = {question.strip().lower()}
            for q in rewrite_query(self.llm, question):
                if q.strip().lower() not in seen:
                    seen.add(q.strip().lower())
                    queries.append(q)

        # With reranking on, the question is embedded once up front: the vector
        # drives both the original-question search and the MMR relevance term.
        query_vec: Optional[List[float]] = None
        if self.use_reranking:
            emit("embedding", "Embedding your question")
            query_vec = self.embeddings.embed_query(question)

        # Per-query depth: with reranking, every query fetches at least k (so
        # each decomposed company-metric sub-query contributes real candidates
        # to the merged pool) and a lone query fetches the full fetch_k;
        # without reranking, each query fetches k and the merged round-robin
        # list is truncated to k.
        if self.use_reranking:
            per_query = max(self.k, math.ceil(self.fetch_k / len(queries)))
        else:
            per_query = self.k

        emit(
            "searching",
            f"Searching 10-K filings ({per_query * len(queries)} candidates)",
            candidates=per_query * len(queries),
            queries=len(queries),
        )
        ranked_lists = []
        for i, q in enumerate(queries):
            if i == 0 and query_vec is not None:
                # Same code path similarity_search uses internally, minus the
                # redundant second embedding of the original question.
                ranked_lists.append(
                    self.vectorstore.similarity_search_by_vector(
                        query_vec, k=per_query
                    )
                )
            else:
                ranked_lists.append(self.vectorstore.similarity_search(q, k=per_query))
        candidates = merge_ranked_lists(ranked_lists)

        if self.use_reranking:
            emit(
                "reranking",
                f"Reranking {len(candidates)} passages → top "
                f"{min(self.k, len(candidates))}",
                candidates=len(candidates),
                top_k=self.k,
            )
            docs = mmr_rerank(
                self.vectorstore,
                self.embeddings,
                question,
                candidates,
                k=self.k,
                lambda_mult=self.mmr_lambda,
                query_embedding=query_vec,
            )
        else:
            docs = candidates[: self.k]

        if docs:
            emit(
                "reading",
                _reading_label(docs),
                documents=[
                    {
                        "company": doc.metadata.get("company"),
                        "year": doc.metadata.get("year"),
                        "page": doc.metadata.get("page"),
                    }
                    for doc in docs
                ],
            )
        return docs

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

    async def astream(
        self, question: str
    ) -> AsyncIterator[Union[str, ProgressEvent, List[Source]]]:
        """Stream progress events, then the answer token-by-token, then sources.

        Async counterpart to :meth:`ask` (which is left unchanged). Progress
        events are emitted from the retrieval stages as they actually execute
        (relayed live from the retrieval worker thread), followed by a final
        "composing" event immediately before LLM generation begins.

        Yields:
            ``dict`` progress events (see :data:`ProgressEvent`) while the
            pipeline works, then ``str`` tokens of the answer as they are
            generated, then a single final ``List[Source]`` with the retrieved
            chunks used. Consumers distinguish by type: ``dict`` -> progress,
            ``str`` -> answer token, ``list`` -> the final sources. The answer
            and sources payloads are unchanged from before progress events
            existed.
        """
        # Retrieval (incl. the optional rewrite LLM call and MMR pass) is
        # synchronous; run it in a worker thread and relay its progress events
        # into this async generator via a loop-bound queue. The worker pushes
        # ("progress", event) as stages run and a final ("done", docs) /
        # ("error", exc), so no events can be lost to consumer/worker races.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_progress(event: ProgressEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, ("progress", event))

        def run_retrieval() -> None:
            try:
                docs = self._retrieve(question, on_progress)
                loop.call_soon_threadsafe(queue.put_nowait, ("done", docs))
            except Exception as exc:  # noqa: BLE001 - relayed to the consumer below
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

        worker = asyncio.create_task(asyncio.to_thread(run_retrieval))
        try:
            docs: List[Document] = []
            while True:
                kind, payload = await queue.get()
                if kind == "progress":
                    yield payload
                elif kind == "done":
                    docs = payload
                    break
                else:
                    raise payload
        finally:
            await worker

        yield {"stage": "composing", "label": "Composing answer"}
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

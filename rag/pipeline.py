"""End-to-end RAG pipeline over the 10-K corpus.

``RagPipeline`` wires together a persisted FAISS index, a top-k retriever, the
provider's chat model, and the grounded 10-K prompt into a single LCEL chain,
and exposes :meth:`ask` to answer a question with its supporting sources.
"""

from __future__ import annotations

from typing import AsyncIterator, Dict, List, Tuple, Union

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

from config.factory import get_chat_model, get_embeddings
from config.providers import get_config
from rag.retrieval import RAG_PROMPT, build_retriever, format_docs
from rag.vectorstore import index_exists, load_vectorstore, persist_dir_for

# A source is the attribution metadata for one retrieved chunk.
Source = Dict[str, object]


class RagPipeline:
    """Answer 10-K questions for one provider config, grounded in its index.

    Args:
        config_name: Named provider config (see ``config.providers.REGISTRY``).
        k: Number of chunks to retrieve per question.
        chunk_size / chunk_overlap: Chunking params used when the index was
            built; they select which persisted index to load.

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
    ) -> None:
        self.config_name = config_name
        self.config = get_config(config_name)
        self.persist_dir = persist_dir_for(config_name, chunk_size, chunk_overlap)

        if not index_exists(self.persist_dir):
            raise FileNotFoundError(
                f"No FAISS index for config '{config_name}' at '{self.persist_dir}'. "
                f"Build it first:\n"
                f"    python scripts/build_index.py --config {config_name} "
                f"--chunk-size {chunk_size} --chunk-overlap {chunk_overlap}"
            )

        embeddings = get_embeddings(self.config)
        self.vectorstore = load_vectorstore(self.persist_dir, embeddings)
        self.retriever = build_retriever(self.vectorstore, k=k)
        self.llm = get_chat_model(self.config)
        # Shared answer sub-chain (expects {context, question}); reused by the
        # full ask() chain and by astream() so there is one grounding path.
        self._answer_chain = RAG_PROMPT | self.llm | StrOutputParser()
        self._chain = self._build_chain()

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
            docs=self.retriever,
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
        }

    def ask(self, question: str) -> Tuple[str, List[Source]]:
        """Answer ``question`` from the indexed 10-Ks.

        Returns:
            ``(answer, sources)`` where ``sources`` lists the company / year /
            page (and source file) of each retrieved chunk used.
        """
        result = self._chain.invoke(question)
        answer: str = result["answer"]
        sources = [self._to_source(doc) for doc in result["docs"]]
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
        docs = await self.retriever.ainvoke(question)
        context = format_docs(docs)
        async for token in self._answer_chain.astream(
            {"context": context, "question": question}
        ):
            if token:
                yield token
        yield [self._to_source(doc) for doc in docs]

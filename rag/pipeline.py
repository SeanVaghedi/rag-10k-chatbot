"""End-to-end RAG pipeline orchestration.

Planned responsibilities:

- Glue the stages together: load filings -> chunk -> embed/build (or load
  cached) vectorstore -> build retriever -> answer questions.
- Resolve chat and embedding clients from the config factory based on the
  selected provider(s).
- Provide a single high-level object/function the Streamlit app and the eval
  harness can both call, so behavior stays consistent across the UI and tests.
"""


class RagPipeline:
    """High-level RAG pipeline over the 10-K corpus.

    Intended usage: construct once (builds or loads the vectorstore), then call
    :meth:`ask` per user question. To be implemented.
    """

    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError

    def ask(self, question: str):
        """Return an answer and its supporting sources. To be implemented."""
        raise NotImplementedError

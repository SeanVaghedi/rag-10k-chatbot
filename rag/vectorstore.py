"""FAISS vector store construction, persistence, and loading.

Builds a FAISS index over chunked documents and persists it to disk so the
corpus is embedded only once. Persist directories are namespaced by config name
*and* chunk parameters, so different embedding models / chunk settings never
overwrite each other's indexes:

    .vectorstore/{config_name}_cs{chunk_size}_co{chunk_overlap}/
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional, Sequence, TypeVar, Union

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

# Root directory for all persisted indexes (git-ignored).
DEFAULT_BASE_DIR = ".vectorstore"

# Default exponential backoff (in seconds) applied before each retry when the
# embedding provider returns a rate-limit error (HTTP 429 / RESOURCE_EXHAUSTED).
DEFAULT_BACKOFF_SECONDS: tuple = (5.0, 15.0, 45.0)

PathLike = Union[str, Path]
T = TypeVar("T")


def persist_dir_for(
    config_name: str,
    chunk_size: int,
    chunk_overlap: int,
    base_dir: PathLike = DEFAULT_BASE_DIR,
) -> Path:
    """Return the namespaced persist directory for a given config + chunking.

    e.g. ``.vectorstore/gemini_native_cs1000_co150``.
    """
    name = f"{config_name}_cs{chunk_size}_co{chunk_overlap}"
    return Path(base_dir) / name


def index_exists(persist_dir: PathLike) -> bool:
    """Return True if a persisted FAISS index already lives in ``persist_dir``.

    ``FAISS.save_local`` writes ``index.faiss`` and ``index.pkl``; both must be
    present for the index to be loadable.
    """
    directory = Path(persist_dir)
    return (directory / "index.faiss").exists() and (directory / "index.pkl").exists()


def _is_rate_limit_error(exc: BaseException) -> bool:
    """Best-effort, provider-agnostic detection of a rate-limit error.

    Covers Gemini (``ResourceExhausted`` / HTTP 429 / "RESOURCE_EXHAUSTED"),
    OpenAI (``RateLimitError`` / status 429), and generic "too many requests" /
    "quota" responses, without importing any provider SDK.
    """
    # Explicit HTTP status attribute (OpenAI / httpx style).
    for attr in ("status_code", "http_status", "code"):
        if getattr(exc, attr, None) in (429, "429"):
            return True

    name = type(exc).__name__.lower()
    if any(marker in name for marker in ("resourceexhausted", "ratelimit", "toomanyrequests")):
        return True

    text = str(exc).lower()
    markers = ("429", "resource_exhausted", "rate limit", "ratelimit", "too many requests", "quota")
    return any(marker in text for marker in markers)


def _run_with_retry(
    operation: Callable[[], T],
    *,
    label: str,
    max_retries: int,
    backoff_seconds: Sequence[float],
) -> T:
    """Run ``operation``, retrying with backoff only on rate-limit errors.

    Non-rate-limit exceptions propagate immediately. On a rate-limit error we
    wait ``backoff_seconds[attempt]`` (the last value repeats if there are more
    retries than entries) and retry, up to ``max_retries`` times.
    """
    attempt = 0
    while True:
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001 - non-rate-limit errors re-raised below
            if not _is_rate_limit_error(exc) or attempt >= max_retries:
                raise
            wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)] if backoff_seconds else 0.0
            print(
                f"  Rate limit while embedding {label}: "
                f"retry {attempt + 1}/{max_retries} in {wait:.0f}s..."
            )
            time.sleep(wait)
            attempt += 1


def build_vectorstore(
    chunks: List[Document],
    embeddings: Embeddings,
    persist_dir: PathLike,
    batch_size: int = 100,
    delay_seconds: float = 1.0,
    max_retries: int = 3,
    backoff_seconds: Sequence[float] = DEFAULT_BACKOFF_SECONDS,
) -> FAISS:
    """Embed ``chunks`` in throttled batches, build a FAISS index, and persist it.

    To avoid provider rate limits (e.g. Gemini 429 / RESOURCE_EXHAUSTED), chunks
    are embedded ``batch_size`` at a time rather than in one burst: the first
    batch seeds the index via ``FAISS.from_documents`` and each subsequent batch
    is added with ``add_documents``. A ``delay_seconds`` pause is inserted
    between batches, and each batch is retried with exponential backoff on
    rate-limit errors before failing. This path is provider-agnostic — it only
    uses the ``embeddings`` object and the chunk list, so it works for Gemini,
    OpenAI, Ollama, etc.

    Args:
        chunks: Documents to embed and index.
        embeddings: Any LangChain embeddings client.
        persist_dir: Where to save the resulting FAISS index.
        batch_size: Chunks embedded per request batch (default 100).
        delay_seconds: Pause between batches to stay under per-minute limits
            (default 1.0).
        max_retries: Retries per batch on a rate-limit error (default 3).
        backoff_seconds: Wait time before each retry, indexed by attempt; the
            last value repeats if there are more retries than entries
            (default 5s, 15s, 45s).
    """
    if not chunks:
        raise ValueError("Cannot build a vector store from an empty chunk list.")
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1.")

    directory = Path(persist_dir)
    directory.mkdir(parents=True, exist_ok=True)

    batches = [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]
    total = len(batches)

    vectorstore: Optional[FAISS] = None
    for idx, batch in enumerate(batches, start=1):
        if vectorstore is None:
            vectorstore = _run_with_retry(
                lambda b=batch: FAISS.from_documents(b, embeddings),
                label=f"batch {idx}/{total}",
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )
        else:
            vs = vectorstore  # bind for the closure; already non-None here
            _run_with_retry(
                lambda b=batch: vs.add_documents(b),
                label=f"batch {idx}/{total}",
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
            )

        print(f"Embedded batch {idx}/{total} ({len(batch)} chunks)")

        # Throttle between batches (not after the final one).
        if idx < total and delay_seconds > 0:
            time.sleep(delay_seconds)

    assert vectorstore is not None  # guaranteed: chunks is non-empty
    vectorstore.save_local(str(directory))
    return vectorstore


def load_vectorstore(persist_dir: PathLike, embeddings: Embeddings) -> FAISS:
    """Load a persisted FAISS index from ``persist_dir``.

    ``allow_dangerous_deserialization=True`` is acceptable for local dev because
    we only ever load indexes this project built itself.

    Raises:
        FileNotFoundError: if no index exists at ``persist_dir``.
    """
    directory = Path(persist_dir)
    if not index_exists(directory):
        raise FileNotFoundError(
            f"No FAISS index found in '{directory}'. Build it first "
            f"(e.g. via scripts/build_index.py)."
        )
    return FAISS.load_local(
        str(directory),
        embeddings,
        allow_dangerous_deserialization=True,
    )

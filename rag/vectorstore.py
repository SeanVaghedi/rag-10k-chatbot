"""FAISS vectorstore construction, persistence, and loading.

Planned responsibilities:

- Embed chunked documents with a configurable embedding model (resolved via the
  config factory) and build a FAISS index over them.
- Persist the index and its metadata to a cache directory
  (``.vectorstore/``) so the corpus is embedded only once.
- Load an existing cached index when present, keyed by corpus + embedding-model
  fingerprint, to avoid unnecessary re-embedding.
"""

from pathlib import Path
from typing import List

CACHE_DIR = Path(".vectorstore")


def build_vectorstore(chunks: List["object"], embeddings: "object") -> "object":
    """Embed ``chunks`` and build a FAISS vectorstore. To be implemented."""
    raise NotImplementedError


def save_vectorstore(vectorstore: "object", cache_dir: Path = CACHE_DIR) -> None:
    """Persist a FAISS vectorstore to ``cache_dir``. To be implemented."""
    raise NotImplementedError


def load_vectorstore(embeddings: "object", cache_dir: Path = CACHE_DIR) -> "object":
    """Load a persisted FAISS vectorstore from ``cache_dir``. To be implemented."""
    raise NotImplementedError

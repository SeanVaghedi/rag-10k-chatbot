"""Provider configuration definitions for the swappable RAG pipeline.

This module is the single source of truth for:

- :class:`Provider` — the supported model providers.
- :class:`ProviderConfig` — a typed bundle of (chat model, embedding model,
  generation params) for one pipeline configuration.
- Module-level model ID constants (see the "Model IDs verified" block).
- :data:`REGISTRY` — the named configurations this project evaluates.

The ``provider`` field on a :class:`ProviderConfig` selects the **chat**
provider. The **embedding** provider is resolved by :mod:`config.factory` from
``embedding_model_id`` so a single config can mix providers (e.g. Gemini chat +
Ollama embeddings).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Model IDs verified 2026-07-03 — update if deprecated
# ---------------------------------------------------------------------------
# Gemini
GEMINI_CHAT = "gemini-2.5-pro"                # stable
# Newest Gemini chat. Re-verify against current Google docs before a graded
# run — model IDs drift. Swap GEMINI_CHAT -> GEMINI_CHAT_PREVIEW to opt in.
GEMINI_CHAT_PREVIEW = "gemini-3.1-pro-preview"
GEMINI_EMBED = "gemini-embedding-001"         # stable text embedding

# OpenAI
OPENAI_CHAT = "gpt-4o"
OPENAI_EMBED = "text-embedding-3-large"

# Anthropic
# Re-verify against current Anthropic docs before a graded run — model IDs
# drift. Not used by the 5 named configs below; kept for completeness.
ANTHROPIC_CHAT = "claude-opus-4-1"

# Ollama (local; no API key required)
OLLAMA_CHAT = "llama3.1:8b"
OLLAMA_EMBED = "nomic-embed-text"


class Provider(str, Enum):
    """Supported model providers (chat and/or embeddings)."""

    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    PERPLEXITY = "perplexity"


@dataclass(frozen=True)
class ProviderConfig:
    """A single, swappable pipeline configuration.

    Attributes:
        provider: The **chat** provider. The embedding provider is inferred
            from ``embedding_model_id`` by the factory.
        chat_model_id: Model id passed to the chat client.
        embedding_model_id: Model id passed to the embeddings client.
        temperature: Sampling temperature for the chat model (default 0 for
            deterministic, comparison-friendly answers).
        max_tokens: Optional cap on generated tokens. ``None`` uses the
            provider/client default.
    """

    provider: Provider
    chat_model_id: str
    embedding_model_id: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None


# ---------------------------------------------------------------------------
# Named configurations evaluated by this project.
# ---------------------------------------------------------------------------
REGISTRY: dict[str, ProviderConfig] = {
    "gemini_native": ProviderConfig(
        provider=Provider.GEMINI,
        chat_model_id=GEMINI_CHAT,
        embedding_model_id=GEMINI_EMBED,
    ),
    # Gemini chat + Ollama nomic-embed-text embeddings. Isolates the embedding
    # axis against gemini_native (same LLM, different embedding provider). The
    # embedding provider is resolved from embedding_model_id, so OLLAMA_EMBED
    # routes to Ollama even though the chat provider is Gemini.
    "gemini_nomic_embed": ProviderConfig(
        provider=Provider.GEMINI,
        chat_model_id=GEMINI_CHAT,
        embedding_model_id=OLLAMA_EMBED,
    ),
    # Identical to gemini_native. Chunk size/overlap are CLI flags, not config
    # fields, so this config exists only to give a distinct namespaced index
    # dir (see vectorstore.persist_dir_for). Build and query it with
    # --chunk-size 500 --chunk-overlap 75, e.g.:
    #   python scripts/build_index.py --config gemini_native_cs500 \
    #       --chunk-size 500 --chunk-overlap 75
    "gemini_native_cs500": ProviderConfig(
        provider=Provider.GEMINI,
        chat_model_id=GEMINI_CHAT,
        embedding_model_id=GEMINI_EMBED,
    ),
    "llama_local": ProviderConfig(
        provider=Provider.OLLAMA,
        chat_model_id=OLLAMA_CHAT,
        embedding_model_id=OLLAMA_EMBED,
    ),
    "llama_gemini_embed": ProviderConfig(
        provider=Provider.OLLAMA,
        chat_model_id=OLLAMA_CHAT,
        embedding_model_id=GEMINI_EMBED,
    ),
}


def get_config(name: str) -> ProviderConfig:
    """Look up a named config, with an actionable error for unknown names."""
    try:
        return REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(REGISTRY))
        raise KeyError(
            f"Unknown config '{name}'. Available configs: {available}."
        ) from None

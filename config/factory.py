"""Factory for building LangChain chat and embedding clients from a config.

Given a :class:`~config.providers.ProviderConfig`, :func:`get_chat_model` and
:func:`get_embeddings` return the matching LangChain client instances.

- API keys are read only from the environment (loaded from a local ``.env`` via
  python-dotenv). No credentials are ever hard-coded here.
- If a required key is missing, a clear error names the exact env var to set.
- Provider SDK classes are imported lazily inside each branch so a run only
  needs the packages for the provider(s) it actually uses (e.g. ``llama_local``
  does not require the OpenAI SDK).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from config.providers import (
    GEMINI_EMBED,
    OLLAMA_EMBED,
    OPENAI_EMBED,
    Provider,
    ProviderConfig,
)

# Populate os.environ from a local .env once, at import time.
load_dotenv()


# Environment variable holding each provider's API key. Ollama runs locally and
# needs no key, so it is intentionally absent.
_API_KEY_ENV: dict[Provider, str] = {
    Provider.GEMINI: "GOOGLE_API_KEY",
    Provider.OPENAI: "OPENAI_API_KEY",
    Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    Provider.PERPLEXITY: "PERPLEXITY_API_KEY",
}

# Perplexity exposes an OpenAI-compatible API.
_PERPLEXITY_BASE_URL = "https://api.perplexity.ai"

# Resolve the embedding provider from the embedding model id. Exact-match only,
# so mixed configs (e.g. Gemini chat + OpenAI embeddings) route correctly.
_EMBEDDING_PROVIDER: dict[str, Provider] = {
    GEMINI_EMBED: Provider.GEMINI,
    OPENAI_EMBED: Provider.OPENAI,
    OLLAMA_EMBED: Provider.OLLAMA,
}


def _require_api_key(provider: Provider) -> str:
    """Return the provider's API key from the environment or raise clearly."""
    env_var = _API_KEY_ENV[provider]
    key = os.environ.get(env_var)
    if not key:
        raise RuntimeError(
            f"Missing API key for provider '{provider.value}': set the "
            f"'{env_var}' environment variable (add it to your .env file — "
            f"see .env.example)."
        )
    return key


def get_chat_model(config: ProviderConfig) -> BaseChatModel:
    """Build the LangChain chat model for ``config`` (selected by its provider)."""
    provider = config.provider

    if provider is Provider.GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs: dict = dict(
            model=config.chat_model_id,
            google_api_key=_require_api_key(Provider.GEMINI),
            temperature=config.temperature,
        )
        if config.max_tokens is not None:
            kwargs["max_output_tokens"] = config.max_tokens
        return ChatGoogleGenerativeAI(**kwargs)

    if provider is Provider.OPENAI:
        from langchain_openai import ChatOpenAI

        kwargs = dict(
            model=config.chat_model_id,
            api_key=_require_api_key(Provider.OPENAI),
            temperature=config.temperature,
        )
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        return ChatOpenAI(**kwargs)

    if provider is Provider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        kwargs = dict(
            model=config.chat_model_id,
            api_key=_require_api_key(Provider.ANTHROPIC),
            temperature=config.temperature,
        )
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        return ChatAnthropic(**kwargs)

    if provider is Provider.OLLAMA:
        from langchain_ollama import ChatOllama

        kwargs = dict(
            model=config.chat_model_id,
            temperature=config.temperature,
        )
        # Ollama uses num_predict as its max-output-tokens knob.
        if config.max_tokens is not None:
            kwargs["num_predict"] = config.max_tokens
        return ChatOllama(**kwargs)

    if provider is Provider.PERPLEXITY:
        # OpenAI-compatible endpoint.
        from langchain_openai import ChatOpenAI

        kwargs = dict(
            model=config.chat_model_id,
            api_key=_require_api_key(Provider.PERPLEXITY),
            base_url=_PERPLEXITY_BASE_URL,
            temperature=config.temperature,
        )
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        return ChatOpenAI(**kwargs)

    raise ValueError(f"Unsupported chat provider: {provider!r}")


def _embedding_provider(config: ProviderConfig) -> Provider:
    """Resolve the embedding provider from ``config.embedding_model_id``."""
    try:
        return _EMBEDDING_PROVIDER[config.embedding_model_id]
    except KeyError:
        known = ", ".join(sorted(_EMBEDDING_PROVIDER))
        raise ValueError(
            f"Unknown embedding model id '{config.embedding_model_id}'. "
            f"Known embedding models: {known}. Add new ids to "
            f"config.factory._EMBEDDING_PROVIDER with their provider."
        ) from None


def get_embeddings(config: ProviderConfig) -> Embeddings:
    """Build the LangChain embeddings client for ``config``.

    The embedding provider is inferred from ``embedding_model_id`` so mixed
    configs (different chat vs. embedding providers) are supported.
    """
    provider = _embedding_provider(config)

    if provider is Provider.GEMINI:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        return GoogleGenerativeAIEmbeddings(
            model=config.embedding_model_id,
            google_api_key=_require_api_key(Provider.GEMINI),
        )

    if provider is Provider.OPENAI:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.embedding_model_id,
            api_key=_require_api_key(Provider.OPENAI),
        )

    if provider is Provider.OLLAMA:
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=config.embedding_model_id)

    raise ValueError(f"Unsupported embedding provider: {provider!r}")

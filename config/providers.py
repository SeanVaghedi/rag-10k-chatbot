"""Provider configuration definitions.

Planned responsibilities:

- Enumerate the supported providers for chat and embeddings:
  Google Gemini, OpenAI, Anthropic Claude, Perplexity, and local Ollama.
- Declare per-provider settings: default model name(s), the environment
  variable holding the API key, and default generation params (temperature,
  max tokens, etc.).
- Serve as the single source of truth that :mod:`config.factory` reads when
  instantiating LLM and embedding clients.

Note: concrete default model IDs are intentionally left unset in this scaffold
and will be filled in when the pipeline is implemented.
"""

from dataclasses import dataclass
from enum import Enum


class Provider(str, Enum):
    """Supported model providers."""

    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    PERPLEXITY = "perplexity"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class ProviderConfig:
    """Settings for a single provider.

    Attributes (to be populated during implementation):
        provider: which :class:`Provider` this config is for.
        chat_model: default chat/completion model id.
        embedding_model: default embedding model id (if supported).
        api_key_env: name of the environment variable holding the API key.
    """

    provider: Provider
    chat_model: str = ""
    embedding_model: str = ""
    api_key_env: str = ""


# Registry of provider defaults — to be filled in during implementation.
PROVIDER_CONFIGS: dict = {}

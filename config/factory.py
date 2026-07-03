"""Client factory: build LLM and embedding clients from provider config + env.

Planned responsibilities:

- Read API keys from the environment (loaded from ``.env`` via ``python-dotenv``).
- Given a selected :class:`~config.providers.Provider`, instantiate the matching
  LangChain chat model (e.g. ``ChatGoogleGenerativeAI``, ``ChatOpenAI``,
  ``ChatAnthropic``, ``ChatOllama``, or a Perplexity-backed client).
- Given a selected embedding provider, instantiate the matching embeddings
  client (e.g. ``GoogleGenerativeAIEmbeddings``, ``OpenAIEmbeddings``,
  ``OllamaEmbeddings``).
- Validate that the required key is present and raise a clear error otherwise.
"""

from config.providers import Provider


def get_chat_model(provider: Provider, **overrides):
    """Instantiate a chat model client for ``provider``. To be implemented."""
    raise NotImplementedError


def get_embeddings(provider: Provider, **overrides):
    """Instantiate an embeddings client for ``provider``. To be implemented."""
    raise NotImplementedError

"""Streamlit frontend for the RAG 10-K chatbot.

This module renders the interactive web UI and wires user input into the RAG
pipeline. Planned responsibilities:

- Sidebar controls for selecting the chat provider/model (Gemini, OpenAI,
  Claude, Perplexity, Ollama) and the embedding provider.
- One-time (cached) build/load of the FAISS vectorstore over the 10-K corpus.
- A chat interface that streams answers and lets users compare Alphabet,
  Amazon, and Microsoft filings.
- A "sources" panel that shows the retrieved chunks (company, year, page)
  backing each answer so responses stay auditable.

Run with:
    streamlit run app/streamlit_app.py
"""


def main() -> None:
    """Entry point: build the Streamlit page and run the chat loop.

    To be implemented — will assemble the provider selection UI, initialize the
    RAG pipeline, and handle the request/response chat cycle.
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()

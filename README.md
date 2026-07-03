# RAG 10-K Chatbot

A Retrieval-Augmented Generation (RAG) chatbot for comparing the annual **10-K
filings** of **Alphabet**, **Amazon**, and **Microsoft**. Ask cross-company
questions ("How do their cloud revenue trends compare?") and get grounded,
citation-backed answers drawn directly from the filings.

The pipeline is provider-agnostic: chat and embedding models can be swapped
between Google Gemini, OpenAI, Anthropic Claude, Perplexity, and local Ollama
models via a config factory.

> **Status:** scaffold only. Module files describe their intended behavior via
> docstrings; the pipeline logic is not yet implemented.

## Project structure

```
rag-10k-chatbot/
├── app/                 # Streamlit frontend
│   └── streamlit_app.py # Chat UI, provider selector, source display
├── rag/                 # Core RAG pipeline
│   ├── loaders.py       # Load & tag 10-K PDFs
│   ├── chunking.py      # Split documents into token-aware chunks
│   ├── vectorstore.py   # Build / persist / load FAISS index
│   ├── retrieval.py     # Retriever + RAG chain + prompts
│   └── pipeline.py      # End-to-end orchestration glue
├── config/              # Provider configs + factory
│   ├── providers.py     # Per-provider settings (models, params)
│   └── factory.py       # Build LLM / embedding clients from env
├── data/
│   └── pdfs/            # Drop the three 10-K PDFs here
├── eval/                # Evaluation harness
│   ├── questions.py     # Test questions & expectations
│   └── scoring.py       # Scoring / grading logic
├── requirements.txt
├── .env.example
└── .gitignore
```

## Setup

Requires **Python 3.11**.

1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   # macOS / Linux
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure API keys:
   ```bash
   cp .env.example .env
   # edit .env and fill in the keys for the provider(s) you plan to use
   ```

4. Add the filings — download the latest 10-K PDFs for Alphabet, Amazon, and
   Microsoft and place them in `data/pdfs/`.

5. Run the app:
   ```bash
   streamlit run app/streamlit_app.py
   ```

## Evaluation

The `eval/` package holds a set of comparison questions and a scoring harness
used to measure retrieval quality and answer accuracy across providers. (To be
implemented.)

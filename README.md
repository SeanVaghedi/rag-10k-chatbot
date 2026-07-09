# 10-K Intelligence

A Retrieval-Augmented Generation (RAG) chatbot for grounded question-answering
over the FY2025 annual **10-K filings** of **Alphabet**, **Amazon**, and
**Microsoft**. Every answer is citation-backed and links to the exact source
page in the filing — opened in-app with the supporting passage highlighted.

**Live demo:** [PLACEHOLDER — add deployed URL]

Ask a cross-company question ("Which of the three has the largest cloud
business, and what are the figures?") and get an answer grounded in the actual
filings, with inline citations you can click through to the cited PDF page.
Out-of-scope questions are refused rather than hallucinated — and that behavior
is measured, not assumed (see [Evaluation](#evaluation)).

## Features

- **Streaming chat** — answers stream token-by-token from a grounded RAG chain.
- **Citation-backed answers** — every claim cites the filing, fiscal year, and page it draws from; only cited excerpts are surfaced as sources.
- **PDF drill-down** — clicking a source opens the actual 10-K in an in-app viewer (react-pdf) at the cited page, with the retrieved passage highlighted.
- **Historical sources panel** — each answer retains its own sources; browse any previous answer's evidence via a per-message badge.
- **"Model & Configuration" panel** — documents the running configuration and the evaluation results that justified it, in-app.
- **Evaluation harness** — a 16-question gold set scored automatically across 5 provider configurations (`eval/run_eval.py`).
- **"Liquid Glass" UI** — a dark, depth-layered glass interface (Next.js + Tailwind + framer-motion) with reduced-motion and accessibility support.

## Architecture

Two-tier: a Python backend wrapping the RAG pipeline, and a Next.js frontend.

```
frontend (Next.js + TypeScript + Tailwind)
   │  streaming chat · sources panel · PDF viewer · config panel
   ▼
backend (FastAPI)
   │  POST /ask · POST /ask/stream · GET /configs · GET /health · GET /pdfs/{file}
   ▼
RAG pipeline (LangChain)
   load PDFs → token-aware chunking → embeddings → FAISS → top-k retrieval
   → grounded prompt → Gemini 2.5 Pro → cited answer + source metadata
```

- **Backend** — FastAPI with streaming and non-streaming Q&A endpoints, a config listing, and a static route serving the source PDFs to the viewer. Persisted FAISS indexes are loaded on demand per config and kept in a warm cache.
- **Frontend** — Next.js + TypeScript + Tailwind. Streaming chat, a historical per-answer sources panel with animated source cards, an interactive PDF viewer that opens each cited source at the correct page with passage highlighting, and an informational "Model & Configuration" panel.

## RAG pipeline

| Stage | Implementation |
|---|---|
| Loading | `pypdf` page-level loading with company / fiscal-year metadata tagging (`rag/loaders.py`) |
| Chunking | Token-aware recursive splitting with a `tiktoken` length function — production: **1000-token chunks, 150 overlap** (`rag/chunking.py`) |
| Embeddings | **Google `gemini-embedding-001`** (production); local `nomic-embed-text` via Ollama also supported (`config/factory.py`) |
| Vector store | **FAISS**, persisted to disk and namespaced by config name + chunk params; embedding builds are batched with throttling and exponential-backoff retry for rate limits (`rag/vectorstore.py`) |
| Retrieval | Similarity search, **top k=5** — selected via a k-sweep (`rag/retrieval.py`) |
| LLM | **Google Gemini 2.5 Pro** (production); Llama 3.1 8B via Ollama also supported |

The chat and embedding models are selected by **named config** through a
provider-agnostic factory (`config/providers.py`, `config/factory.py`), making
each of the five evaluated configurations a one-line change.

## Production configuration

**Gemini 2.5 Pro + Gemini embeddings + 1000-token chunks + k=5** — every
setting justified by evaluation, not defaults.

## Evaluation

A gold set of **16 questions** (`eval/gold_set.py`) spanning four categories:

- **Number checking** — exact-figure lookups, including hard multi-year-table
  disambiguation (prior-year comparative columns, beginning- vs end-of-period
  values, reversed column orders).
- **Cross-company comparison** — key-fact coverage across all three filings.
- **Qualitative / risk** — open-ended "how does each company describe X".
- **Boundary** — questions whose answers are *not* in the corpus (forward
  projections, companies outside the corpus); the model must refuse rather
  than fabricate.

The harness (`eval/run_eval.py`) runs the gold set across all 5 configurations
— spanning three axes (LLM, embeddings, chunk size) — with transparent
rule-based scoring, latency tracking, and CSV/JSONL reports in `eval/results/`.
`eval/rescore.py` re-scores an existing run after scoring-logic changes without
re-spending API calls.

| Config | LLM | Embeddings | Chunk | Number acc | Boundary acc | Key-facts |
|---|---|---|---|---|---|---|
| **`gemini_native`** ← selected | Gemini 2.5 Pro | Gemini | 1000 | **100%** | **100%** | **80%** |
| `gemini_nomic_embed` | Gemini 2.5 Pro | nomic (local) | 1000 | 100% | 100% | 35% |
| `gemini_native_cs500` | Gemini 2.5 Pro | Gemini | 500 | 100% | 100% | 53% |
| `llama_local` | Llama 3.1 8B | nomic (local) | 1000 | 80% | 100% | 35% |
| `llama_gemini_embed` | Llama 3.1 8B | Gemini | 1000 | 80% | 100% | 53% |

`gemini_native` achieved 100% number accuracy, 100% boundary accuracy, and the
highest retrieval richness. The local Llama configs scored 80% on number
accuracy, failing the multi-year-table disambiguation questions. A retrieval
depth sweep (`--k`) found k=3 → 43%, k=5 → 70%, k=8 → 70% key-facts hit-rate,
with latency lowest at k=5.

## Project structure

```
rag-10k-chatbot/
├── backend/            # FastAPI app (streaming Q&A, configs, PDF serving)
├── frontend/           # Next.js app (chat UI, sources panel, PDF viewer)
├── rag/                # Core pipeline
│   ├── loaders.py      #   load & tag 10-K PDFs
│   ├── chunking.py     #   token-aware recursive chunking
│   ├── vectorstore.py  #   build / persist / load FAISS indexes
│   ├── retrieval.py    #   retriever + grounded prompt
│   └── pipeline.py     #   end-to-end RAG chain (ask + streaming)
├── config/
│   ├── providers.py    #   the 5 named configurations
│   └── factory.py      #   chat / embedding model construction
├── scripts/
│   ├── build_index.py  #   build a persisted index for a config
│   └── ask.py          #   CLI Q&A for quick pipeline checks
├── eval/
│   ├── gold_set.py     #   16-question gold set with expected answers
│   ├── run_eval.py     #   eval harness (--config/--configs, --k sweep)
│   ├── rescore.py      #   re-score a past run without re-running models
│   └── results/        #   per-question + summary reports (CSV/JSONL)
├── data/pdfs/          # the three 10-K PDFs
├── requirements.txt
├── .env.example
└── .gitignore
```

## Getting started

Requires **Python 3.12** and **Node.js**.

```bash
# 1. Python environment
python -m venv venv
venv\Scripts\Activate.ps1        # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt

# 2. API key
cp .env.example .env             # then set GOOGLE_API_KEY=<your key>

# 3. Build the production index
python scripts/build_index.py --config gemini_native

# 4. Run the backend
python -m uvicorn backend.main:app --reload --port 8000

# 5. Run the frontend
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

API keys are read from the environment (`.env`, git-ignored) and are never
committed.

**Local configs (optional):** the `llama_local`, `llama_gemini_embed`, and
`gemini_nomic_embed` configs run against [Ollama](https://ollama.com) — install
it, then `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`, and
build the matching index with `--config <name>`.

**Try it from the CLI:**

```bash
python scripts/ask.py "How much cash did Amazon hold at the end of fiscal 2024?"
```

**Run the evaluation:**

```bash
python eval/run_eval.py --config gemini_native          # one config
python eval/run_eval.py                                 # all five
python eval/run_eval.py --config gemini_native --k 8    # retrieval-depth sweep
```

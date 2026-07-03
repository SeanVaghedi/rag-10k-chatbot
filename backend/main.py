"""FastAPI backend wrapping RagPipeline over HTTP (streaming + multi-config).

Run locally (from the project root):
    uvicorn backend.main:app --reload --port 8000

This layer imports and reuses the existing rag/ and config/ modules — it does
not duplicate pipeline logic. API keys are read from the environment via the
existing factory; .env is loaded at startup.

Quick curl tests:
    curl localhost:8000/health
    curl localhost:8000/configs
    curl -X POST localhost:8000/ask -H 'content-type: application/json' \
         -d '{"question":"How much cash did Amazon hold at fiscal year end?","config":"gemini_native"}'
    curl -N -X POST localhost:8000/ask/stream -H 'content-type: application/json' \
         -d '{"question":"Compare cloud revenue across the three companies.","config":"gemini_native"}'
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Optional

# Make the project root importable so `config` / `rag` resolve regardless of
# where uvicorn is launched from.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.concurrency import run_in_threadpool  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from config.providers import REGISTRY  # noqa: E402
from rag.pipeline import RagPipeline  # noqa: E402
from rag.vectorstore import index_exists, persist_dir_for  # noqa: E402

# Load .env at startup (the factory also does this on import; harmless to repeat).
load_dotenv()

# Chunk params RagPipeline uses by default; also used to locate an index on disk
# for the /configs "index_built" check. Must match RagPipeline's constructor
# defaults.
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150

# Friendly labels for the frontend; falls back to a title-cased name.
_DISPLAY_LABELS = {
    "gemini_native": "Gemini (chat + embeddings)",
    "openai_native": "OpenAI (chat + embeddings)",
    "gemini_llm_openai_embed": "Gemini chat + OpenAI embeddings",
    "llama_local": "Llama 3.1 local (Ollama)",
    "llama_gemini_embed": "Llama 3.1 chat + Gemini embeddings",
}


def _display_label(name: str) -> str:
    return _DISPLAY_LABELS.get(name, name.replace("_", " ").title())


# ---------------------------------------------------------------------------
# App + CORS
# ---------------------------------------------------------------------------
app = FastAPI(title="10-K RAG API", version="0.1.0")

_allowed_origins = ["http://localhost:3000"]
_frontend_origin = os.environ.get("FRONTEND_ORIGIN")
if _frontend_origin:
    _allowed_origins.append(_frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pipeline cache (lazy load + warm cache)
# ---------------------------------------------------------------------------
_PIPELINES: dict[str, RagPipeline] = {}


def get_pipeline(config_name: str) -> RagPipeline:
    """Return a cached RagPipeline for ``config_name``, building it on first use.

    Raises:
        HTTPException(400): if the config name is unknown, its index has not
        been built, or a required API key is missing. Never crashes the server.
    """
    cached = _PIPELINES.get(config_name)
    if cached is not None:
        return cached

    if config_name not in REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown config '{config_name}'. Valid configs: {sorted(REGISTRY)}.",
        )

    try:
        pipeline = RagPipeline(config_name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No FAISS index for config '{config_name}'. Build it first: "
                f"python scripts/build_index.py --config {config_name}"
            ),
        )
    except RuntimeError as exc:
        # e.g. missing API key — the factory raises naming the exact env var.
        raise HTTPException(status_code=400, detail=str(exc))

    _PIPELINES[config_name] = pipeline
    return pipeline


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str
    config: str = "gemini_native"


class Source(BaseModel):
    company: Optional[str] = None
    year: Optional[int] = None
    page: Optional[int] = None
    source_filename: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    config: str


class ConfigInfo(BaseModel):
    name: str
    label: str
    index_built: bool


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------
def _sse(event: str, data: dict) -> str:
    """Serialize one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/configs", response_model=List[ConfigInfo])
def list_configs() -> List[ConfigInfo]:
    """List registered configs with a display label and index-built flag."""
    infos: List[ConfigInfo] = []
    for name in REGISTRY:
        persist_dir = persist_dir_for(name, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
        infos.append(
            ConfigInfo(
                name=name,
                label=_display_label(name),
                index_built=index_exists(persist_dir),
            )
        )
    return infos


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Non-streaming answer + sources for a question (runs in a threadpool)."""
    pipeline = get_pipeline(req.config)
    answer, sources = pipeline.ask(req.question)
    return AskResponse(answer=answer, sources=sources, config=req.config)


@app.post("/ask/stream")
async def ask_stream(req: AskRequest) -> StreamingResponse:
    """Stream the answer token-by-token as SSE, then a final sources event.

    Events:
        - ``token``  -> {"text": "<partial answer>"}
        - ``sources``-> {"sources": [...], "config": "<name>"}
        - ``done``   -> {}
        - ``error``  -> {"message": "..."} (any mid-stream failure)
    """
    # Resolve/validate the pipeline before streaming so config/index/key errors
    # surface as a normal HTTP 400 rather than mid-stream. Runs off the event
    # loop since first-time construction loads the FAISS index.
    pipeline = await run_in_threadpool(get_pipeline, req.config)

    async def event_generator():
        try:
            async for chunk in pipeline.astream(req.question):
                if isinstance(chunk, str):
                    yield _sse("token", {"text": chunk})
                else:
                    # Final item from astream is the list of sources.
                    yield _sse("sources", {"sources": chunk, "config": req.config})
            yield _sse("done", {})
        except Exception as exc:  # noqa: BLE001 - report errors to the client, keep server up
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering for live tokens
        },
    )

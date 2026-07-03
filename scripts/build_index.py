"""Build (and persist) the FAISS index for a given provider config.

Loads the 10-K PDFs, chunks them, embeds them via the provider factory, and
persists a namespaced FAISS index. Doubles as an end-to-end smoke test of the
factory, since it exercises ``get_embeddings()`` for real.

Usage:
    python scripts/build_index.py                       # gemini_native, defaults
    python scripts/build_index.py --config openai_native
    python scripts/build_index.py --config llama_local --chunk-size 800 --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the project root importable when run as `python scripts/build_index.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.factory import get_embeddings  # noqa: E402
from config.providers import get_config  # noqa: E402
from rag.chunking import chunk_documents  # noqa: E402
from rag.loaders import load_10k_pdfs  # noqa: E402
from rag.vectorstore import build_vectorstore, index_exists, persist_dir_for  # noqa: E402

DEFAULT_PDF_DIR = _PROJECT_ROOT / "data" / "pdfs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the FAISS index for a config.")
    parser.add_argument(
        "--config",
        default="gemini_native",
        help="Named provider config to use (default: gemini_native).",
    )
    parser.add_argument(
        "--pdf-dir",
        default=str(DEFAULT_PDF_DIR),
        help="Directory containing the 10-K PDFs (default: data/pdfs).",
    )
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in tokens.")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Chunk overlap in tokens.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if an index already exists for this config + chunking.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = get_config(args.config)
    persist_dir = persist_dir_for(args.config, args.chunk_size, args.chunk_overlap)

    print(f"Config:          {args.config}")
    print(f"  chat model:    {config.chat_model_id}")
    print(f"  embed model:   {config.embedding_model_id}")
    print(f"Chunking:        size={args.chunk_size} tokens, overlap={args.chunk_overlap} tokens")
    print(f"Persist dir:     {persist_dir}")

    if index_exists(persist_dir) and not args.force:
        print("\nIndex already exists — skipping rebuild. Use --force to rebuild.")
        return

    print("\nLoading PDFs...")
    docs = load_10k_pdfs(args.pdf_dir)
    num_pdfs = len({d.metadata["source_filename"] for d in docs})
    total_pages = len(docs)
    print(f"  Loaded {num_pdfs} PDF(s), {total_pages} page(s).")

    print("Chunking...")
    chunks = chunk_documents(docs, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    print(f"  Produced {len(chunks)} chunk(s).")

    print("Building embeddings + FAISS index (this may hit the provider API)...")
    build_vectorstore(chunks, get_embeddings(config), persist_dir)

    print("\n" + "=" * 60)
    print("Index build complete.")
    print(f"  PDFs:        {num_pdfs}")
    print(f"  Pages:       {total_pages}")
    print(f"  Chunks:      {len(chunks)}")
    print(f"  Saved to:    {persist_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()

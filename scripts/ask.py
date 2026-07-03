"""Ask the RAG pipeline a question from the command line.

This is how we test retrieval quality before building the Streamlit UI.

Example usage:
    python scripts/ask.py "How much cash does Amazon have at end of fiscal 2024?"
    python scripts/ask.py --config openai_native "Compare cloud revenue across the three companies."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the project root importable when run as `python scripts/ask.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rag.pipeline import RagPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask the 10-K RAG pipeline a question.")
    parser.add_argument("question", help="The question to ask (quote it).")
    parser.add_argument(
        "--config",
        default="gemini_native",
        help="Named provider config to use (default: gemini_native).",
    )
    parser.add_argument("--k", type=int, default=5, help="Chunks to retrieve (default: 5).")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Index chunk size (tokens).")
    parser.add_argument("--chunk-overlap", type=int, default=150, help="Index chunk overlap (tokens).")
    return parser.parse_args()


def _format_source(idx: int, source: dict) -> str:
    company = str(source.get("company", "unknown")).title()
    year = source.get("year", "unknown")
    page = source.get("page", "unknown")
    filename = source.get("source_filename", "unknown")
    return f"  [{idx}] {company} — FY{year}, page {page} ({filename})"


def main() -> None:
    args = parse_args()

    pipeline = RagPipeline(
        config_name=args.config,
        k=args.k,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    answer, sources = pipeline.ask(args.question)

    print(f"\nQuestion: {args.question}")
    print(f"Config:   {args.config}\n")
    print("Answer:")
    print(answer)

    print("\nSources:")
    if sources:
        for i, source in enumerate(sources, start=1):
            print(_format_source(i, source))
    else:
        print("  (none retrieved)")


if __name__ == "__main__":
    main()

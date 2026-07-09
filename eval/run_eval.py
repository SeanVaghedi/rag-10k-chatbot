"""Evaluation harness: run the gold-set questions through every config.

Runs each question in :mod:`eval.gold_set` against one or more of the named
provider configs (``config.providers.REGISTRY``), scores the answers, measures
wall-clock latency, and writes everything to ``eval/results/`` for later
analysis and presentation.

Scoring is deliberately simple and transparent (no LLM-as-judge, no network
grading):

- number   : pass if the expected figure or any accepted variant appears in the
             answer, after normalizing away ``$``, commas, and whitespace.
- boundary : pass if the answer says the requested info is not in the filings
             (a refusal / unavailability statement). Historical figures quoted
             for context do NOT fail it; only a fabricated projected/forecast
             figure -- or no acknowledgement of unavailability at all -- fails.
- comparison / qualitative : cannot be auto-graded reliably, so these are
             flagged ``needs_manual_review`` and only a ``key_facts`` hit-count
             is logged as a soft signal.

The run is resilient: a failed config (missing index, provider down, missing API
key) or a single failed question is caught, logged, and the run continues.

Usage:
    python eval/run_eval.py                                     # all configs
    python eval/run_eval.py --config gemini_native             # a single config
    python eval/run_eval.py --configs gemini_native,llama_local   # a subset
    python eval/run_eval.py --config gemini_native --k 8       # sweep retrieval depth

``--k`` overrides how many chunks the retriever returns for this run only (a
retrieval-depth sweep, e.g. k=3 / 5 / 8). It does NOT change the production
default (RagPipeline / build_retriever still default to k=5).

Outputs (in eval/results/, tagged with the retrieval depth ``k``):
    results_<timestamp>_k<k>.csv   one row per (config, question) with scores.
    summary_<timestamp>_k<k>.csv   per-config aggregate metrics (incl. retrieval_k).
    results_<timestamp>_k<k>.jsonl full records incl. retrieved source chunks.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Make the project root importable when run as `python eval/run_eval.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.providers import REGISTRY  # noqa: E402
from eval.gold_set import CATEGORIES, GOLD_SET  # noqa: E402
from rag.pipeline import RagPipeline  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Chunking used when each index was built. Everything uses the RagPipeline
# defaults except gemini_native_cs500, which was indexed at 500 / 75.
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150
CHUNK_PARAMS_OVERRIDE: Dict[str, Tuple[int, int]] = {
    "gemini_native_cs500": (500, 75),
}

# Retrieval depth (chunks retrieved per question). Mirrors the RagPipeline /
# build_retriever default (k=5); used only to label runs and as the value passed
# when --k is omitted. Override per eval run with --k to compare retrieval depth
# without touching the production default.
DEFAULT_K = 5


def chunk_params_for(config_name: str) -> Tuple[int, int]:
    """Return ``(chunk_size, chunk_overlap)`` the index for this config used."""
    return CHUNK_PARAMS_OVERRIDE.get(
        config_name, (DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP)
    )


# ---------------------------------------------------------------------------
# Normalization + scoring
# ---------------------------------------------------------------------------
# Strip whitespace, dollar signs, and commas so "$82,312 million" and
# "82312 million" (or "82,312") compare equal.
_NORM_STRIP_RE = re.compile(r"[\s$,]")


def normalize(text: str) -> str:
    """Lowercase and remove ``$``, commas, and all whitespace for matching."""
    return _NORM_STRIP_RE.sub("", (text or "").lower())


# Refusal / unavailability markers — the answer signals the requested info is
# not in the filings. Bare "not"/"cannot" are word-boundary anchored so they
# don't fire inside words like "another" or "note". "cannot" is matched on its
# own because \bnot\b does not fire inside it (no boundary before "not").
_REFUSAL_RE = re.compile(
    r"\bnot\b"  # covers "does not contain", "not available", "not projected", ...
    r"|\bcannot\b"
    r"|\bcan['’]?t\b"
    r"|\bunable to\b"
    # "no <unavailable-thing>", adjacent form: "no information", "no data", ...
    r"|\bno\s+(?:information|data|figure|figures|mention|reference|record|"
    r"estimate|estimates|disclosure)\b"
    # "no ... projection/projected/forecast" allowing a qualifier in between, so
    # "no projection", "no projected revenue", and "no 2027 projection" all hit.
    r"|\bno\b(?:\s+\w+){0,4}?\s+(?:projection|projections|projected|forecast|forecasts)\b"
    # contractions the bare \bnot\b anchor misses ("couldn't find", "doesn't mention")
    r"|couldn['’]?t\s+(?:find|locate|identify)"
    r"|could\s+not\s+(?:find|locate|identify)"
    r"|do(?:es)?n['’]?t\s+(?:provide|mention|contain|include|specify|disclose|project)",
    re.IGNORECASE,
)

# A *fabricated forecast*: a projected / FY2027 value asserted as a dollar
# figure, e.g. "projected 2027 revenue of $780,000 million" or "in 2027: $312
# billion". This is the ONLY figure pattern that fails a boundary answer —
# historical figures quoted for context are fine.
#
# The gap between the projection keyword and the "$" is capped at 40 characters,
# stops at a sentence break ('.') or the next '$', and — crucially — must not
# span a *historical* year (2010–2026). That last guard is what separates a real
# forecast ("projected 2027 revenue of $X") from a correct refusal that cites a
# historical number in the same breath ("no 2027 projection; FY2025 was $X"):
# the intervening "2025" blocks the latter from matching. 2027 itself is allowed
# in the gap so "projected FY2027 revenue ... $X" still matches. (No \b on the
# year — it must also catch the year glued to a prefix, as in "FY2025".)
_FORECAST_ASSERT_RE = re.compile(
    r"(?:projected|projection|forecast(?:ed)?|2027)"
    r"(?:(?!20(?:1\d|2[0-6]))[^.$\n]){0,40}"
    r"\$\s?\d",
    re.IGNORECASE,
)


def score_number(answer: str, figure: str, variants: List[str]) -> bool:
    """True if the expected figure or any variant appears in ``answer``."""
    norm_answer = normalize(answer)
    for candidate in [figure, *(variants or [])]:
        norm_candidate = normalize(candidate)
        if norm_candidate and norm_candidate in norm_answer:
            return True
    return False


def score_boundary(answer: str) -> bool:
    """Score a boundary (should-refuse) answer.

    The requested information is out of scope, so a correct answer acknowledges
    it is not in the filings. Historical figures quoted for context are fine —
    only a *fabricated* projected/forecast figure counts against the answer.

    - PASS if a refusal / unavailability marker is present, even if historical
      dollar figures also appear ("no projection ... FY2025 was $X").
    - FAIL if the answer asserts a fabricated forecast (e.g. "projected 2027
      revenue of $X"), even when a hedge is also present.
    - FAIL if no refusal marker is present at all: it did not acknowledge the
      info is unavailable — and if it also stated a figure, it answered the
      unanswerable.
    """
    text = answer or ""
    # A fabricated forecast fails outright, hedge or not.
    if _FORECAST_ASSERT_RE.search(text):
        return False
    # Otherwise a clear refusal / unavailability statement passes; a bare figure
    # for historical context does not matter.
    return bool(_REFUSAL_RE.search(text))


def count_key_facts(answer: str, key_facts: List[str]) -> Tuple[int, int]:
    """Return ``(hits, total)`` — how many key_facts appear in ``answer``."""
    norm_answer = normalize(answer)
    total = len(key_facts or [])
    hits = 0
    for fact in key_facts or []:
        norm_fact = normalize(fact)
        if norm_fact and norm_fact in norm_answer:
            hits += 1
    return hits, total


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
def _score_record(
    config_name: str,
    question: Dict,
    answer: str,
    sources: List[Dict],
    latency: float,
    error: str,
) -> Dict:
    """Build a fully-scored result record for one (config, question)."""
    category = question["category"]
    expected = question.get("expected", {}) or {}
    needs_manual = category in ("comparison", "qualitative")

    passed: Optional[bool] = None
    key_facts_hit: Optional[int] = None
    key_facts_total: Optional[int] = None

    if not error:
        if category == "number":
            passed = score_number(
                answer, expected.get("figure", ""), expected.get("variants", [])
            )
        elif category == "boundary":
            passed = score_boundary(answer)
        elif needs_manual:
            key_facts_hit, key_facts_total = count_key_facts(
                answer, expected.get("key_facts", [])
            )

    return {
        "config": config_name,
        "question_id": question["id"],
        "category": category,
        "question": question["question"],
        "answer": answer,
        "sources": sources,
        "sources_count": len(sources),
        "latency_seconds": round(latency, 3),
        "passed": passed,
        "key_facts_hit": key_facts_hit,
        "key_facts_total": key_facts_total,
        "needs_manual_review": needs_manual,
        "error": error,
    }


def run_question(pipeline: RagPipeline, config_name: str, question: Dict) -> Dict:
    """Run one question through ``pipeline``, timing it and catching failures."""
    start = time.perf_counter()
    try:
        answer, sources = pipeline.ask(question["question"])
        latency = time.perf_counter() - start
        error = ""
    except Exception as exc:  # noqa: BLE001 - one bad question must not abort the run
        latency = time.perf_counter() - start
        answer, sources, error = "", [], f"ask: {type(exc).__name__}: {exc}"
    return _score_record(config_name, question, answer, sources, latency, error)


def _status(record: Dict) -> str:
    """One-word status marker for the progress line."""
    if record["error"]:
        return "ERROR"
    if record["passed"] is True:
        return "PASS"
    if record["passed"] is False:
        return "FAIL"
    return f"REVIEW({record['key_facts_hit']}/{record['key_facts_total']})"


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def summarize(config_name: str, rows: List[Dict], k: Optional[int] = None) -> Dict:
    """Compute per-config aggregate metrics from that config's rows.

    ``k`` is the retrieval depth used for the run; it is recorded on the summary
    so different --k sweeps are self-labeled. Left ``None`` by callers that do
    not track k (e.g. re-scoring an existing run).
    """

    def ok(row: Dict) -> bool:
        return not row["error"]

    def in_cat(category: str) -> List[Dict]:
        return [r for r in rows if r["category"] == category]

    def avg_latency(subset: List[Dict]) -> Optional[float]:
        values = [r["latency_seconds"] for r in subset if ok(r)]
        return round(sum(values) / len(values), 3) if values else None

    def accuracy(subset: List[Dict]) -> Tuple[int, int, Optional[float]]:
        graded = [r for r in subset if ok(r)]
        passed = sum(1 for r in graded if r["passed"])
        pct = round(100.0 * passed / len(graded), 1) if graded else None
        return len(graded), passed, pct

    number_total, number_passed, number_acc = accuracy(in_cat("number"))
    boundary_total, boundary_passed, boundary_acc = accuracy(in_cat("boundary"))

    # Average key_facts hit-rate across the manual-review rows that have facts.
    kf_rows = [r for r in rows if ok(r) and r["key_facts_total"]]
    kf_pct: Optional[float] = (
        round(
            100.0 * sum(r["key_facts_hit"] / r["key_facts_total"] for r in kf_rows)
            / len(kf_rows),
            1,
        )
        if kf_rows
        else None
    )

    return {
        "config": config_name,
        "retrieval_k": k,
        "total_questions_run": sum(1 for r in rows if ok(r)),
        "errors": sum(1 for r in rows if r["error"]),
        "number_total": number_total,
        "number_passed": number_passed,
        "number_accuracy_pct": number_acc,
        "boundary_total": boundary_total,
        "boundary_passed": boundary_passed,
        "boundary_accuracy_pct": boundary_acc,
        "comparison_total": len(in_cat("comparison")),
        "qualitative_total": len(in_cat("qualitative")),
        "avg_key_facts_hit_pct": kf_pct,
        "avg_latency_seconds": avg_latency(rows),
        "avg_latency_number": avg_latency(in_cat("number")),
        "avg_latency_comparison": avg_latency(in_cat("comparison")),
        "avg_latency_qualitative": avg_latency(in_cat("qualitative")),
        "avg_latency_boundary": avg_latency(in_cat("boundary")),
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def _format_sources(sources: List[Dict]) -> str:
    """Compact one-line rendering of the cited sources for the CSV."""
    parts = []
    for src in sources:
        company = str(src.get("company") or "?").title()
        year = src.get("year")
        page = src.get("page")
        filename = src.get("source_filename") or "?"
        parts.append(f"{company} FY{year} p.{page} ({filename})")
    return " | ".join(parts)


_RESULTS_COLUMNS = [
    "config",
    "retrieval_k",
    "question_id",
    "category",
    "question",
    "answer",
    "passed",
    "key_facts_hit",
    "key_facts_total",
    "needs_manual_review",
    "sources_count",
    "sources",
    "latency_seconds",
    "error",
]

_SUMMARY_COLUMNS = [
    "config",
    "retrieval_k",
    "total_questions_run",
    "errors",
    "number_total",
    "number_passed",
    "number_accuracy_pct",
    "boundary_total",
    "boundary_passed",
    "boundary_accuracy_pct",
    "comparison_total",
    "qualitative_total",
    "avg_key_facts_hit_pct",
    "avg_latency_seconds",
    "avg_latency_number",
    "avg_latency_comparison",
    "avg_latency_qualitative",
    "avg_latency_boundary",
]


def _blank_if_none(value: object) -> object:
    return "" if value is None else value


def write_results_csv(path: Path, rows: List[Dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_RESULTS_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "config": r["config"],
                    # .get so rows from callers that don't track k (re-scoring)
                    # still write cleanly as a blank cell.
                    "retrieval_k": _blank_if_none(r.get("retrieval_k")),
                    "question_id": r["question_id"],
                    "category": r["category"],
                    "question": r["question"],
                    "answer": r["answer"],
                    "passed": _blank_if_none(r["passed"]),
                    "key_facts_hit": _blank_if_none(r["key_facts_hit"]),
                    "key_facts_total": _blank_if_none(r["key_facts_total"]),
                    "needs_manual_review": r["needs_manual_review"],
                    "sources_count": r["sources_count"],
                    "sources": _format_sources(r["sources"]),
                    "latency_seconds": r["latency_seconds"],
                    "error": r["error"],
                }
            )


def write_summary_csv(path: Path, summaries: List[Dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_SUMMARY_COLUMNS)
        writer.writeheader()
        for s in summaries:
            writer.writerow({k: _blank_if_none(s.get(k)) for k in _SUMMARY_COLUMNS})


def write_results_jsonl(path: Path, rows: List[Dict]) -> None:
    """Full records incl. the retrieved source chunks (for deep analysis)."""
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def print_summary_table(summaries: List[Dict], skipped: List[Tuple[str, str]]) -> None:
    def pct(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value:.1f}%"

    def lat(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value:.2f}s"

    header = (
        f"{'Config':24} {'k':>3} {'NumAcc':>7} {'BndAcc':>7} {'KFhit':>6} "
        f"{'AvgLat':>8}  {'Lat n/c/q/b':<20} {'Run':>4} {'Err':>4}"
    )
    print(header)
    print("-" * len(header))
    for s in summaries:
        kval = s.get("retrieval_k")
        kstr = "-" if kval is None else str(kval)
        lat_by_cat = "/".join(
            "-" if s[key] is None else f"{s[key]:.1f}"
            for key in (
                "avg_latency_number",
                "avg_latency_comparison",
                "avg_latency_qualitative",
                "avg_latency_boundary",
            )
        )
        print(
            f"{s['config']:24} "
            f"{kstr:>3} "
            f"{pct(s['number_accuracy_pct']):>7} "
            f"{pct(s['boundary_accuracy_pct']):>7} "
            f"{pct(s['avg_key_facts_hit_pct']):>6} "
            f"{lat(s['avg_latency_seconds']):>8}  "
            f"{lat_by_cat:<20} "
            f"{s['total_questions_run']:>4} {s['errors']:>4}"
        )
    for name, reason in skipped:
        print(f"{name:24} SKIPPED ({reason})")


# ---------------------------------------------------------------------------
# CLI + orchestration
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the gold-set eval across one or more provider configs."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--config",
        help="Run a single named config (e.g. gemini_native).",
    )
    group.add_argument(
        "--configs",
        help="Run a comma-separated subset (e.g. gemini_native,llama_local).",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Retrieval depth: retrieve N chunks per question for this run, "
            f"overriding the default (k={DEFAULT_K}). Use to compare retrieval "
            "depth, e.g. --k 3 / --k 5 / --k 8. Does not change the production "
            "default."
        ),
    )
    return parser.parse_args()


def resolve_configs(args: argparse.Namespace) -> List[str]:
    """Resolve the CLI flags to a validated, ordered list of config names."""
    all_configs = list(REGISTRY.keys())
    if args.config:
        requested = [args.config.strip()]
    elif args.configs:
        requested = [c.strip() for c in args.configs.split(",") if c.strip()]
    else:
        return all_configs

    known, unknown = [], []
    for name in requested:
        (known if name in REGISTRY else unknown).append(name)
    for name in unknown:
        print(
            f"WARNING: unknown config '{name}' -- skipping. "
            f"Available: {', '.join(all_configs)}"
        )
    return known


def build_pipeline(config_name: str, k: int) -> RagPipeline:
    chunk_size, chunk_overlap = chunk_params_for(config_name)
    return RagPipeline(
        config_name=config_name,
        k=k,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def run_config(
    config_name: str, index: int, total_configs: int, k: int
) -> Optional[List[Dict]]:
    """Run the whole gold set against one config at retrieval depth ``k``.

    Returns the list of result rows (each stamped with ``retrieval_k``), or
    ``None`` if the config was skipped because its index has not been built yet.
    """
    chunk_size, chunk_overlap = chunk_params_for(config_name)
    print(
        f"=== Config {index}/{total_configs}: {config_name} "
        f"(k={k}, chunk_size={chunk_size}, chunk_overlap={chunk_overlap}) ==="
    )

    init_error = ""
    pipeline: Optional[RagPipeline] = None
    try:
        pipeline = build_pipeline(config_name, k)
    except FileNotFoundError as exc:
        print(f"  SKIP: index not built for '{config_name}'.")
        print(f"        {exc}\n")
        return None
    except Exception as exc:  # noqa: BLE001 - keep going; log against every question
        init_error = f"init: {type(exc).__name__}: {exc}"
        print(f"  ERROR building pipeline for '{config_name}': {init_error}")
        print("  Logging this error against all questions and continuing.\n")

    num_questions = len(GOLD_SET)
    rows: List[Dict] = []
    for q_index, question in enumerate(GOLD_SET, start=1):
        if init_error:
            record = _score_record(config_name, question, "", [], 0.0, init_error)
        else:
            print(
                f"  Running {config_name} ({index}/{total_configs}): "
                f"question {q_index}/{num_questions} [{question['id']}] ...",
                end="",
                flush=True,
            )
            record = run_question(pipeline, config_name, question)
            print(f" {_status(record)}  ({record['latency_seconds']:.2f}s)")
        record["retrieval_k"] = k
        rows.append(record)
    print()
    return rows


def main() -> None:
    args = parse_args()
    if args.k is not None and args.k < 1:
        print(f"Invalid --k {args.k}: retrieval depth must be a positive integer.")
        return
    k = args.k if args.k is not None else DEFAULT_K

    configs = resolve_configs(args)
    if not configs:
        print("No valid configs to run. Exiting.")
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    total_configs = len(configs)
    print(
        f"Gold set: {len(GOLD_SET)} questions | retrieval k={k} | "
        f"Configs to run ({total_configs}): {', '.join(configs)}\n"
    )

    all_rows: List[Dict] = []
    summaries: List[Dict] = []
    skipped: List[Tuple[str, str]] = []

    for index, config_name in enumerate(configs, start=1):
        rows = run_config(config_name, index, total_configs, k)
        if rows is None:
            skipped.append((config_name, "index not built"))
            continue
        all_rows.extend(rows)
        summaries.append(summarize(config_name, rows, k))

    # Write outputs even if partial, so a long/interrupted run still logs data.
    # Filenames carry the retrieval depth so different --k runs don't overwrite
    # each other and are clearly labeled.
    results_csv = RESULTS_DIR / f"results_{timestamp}_k{k}.csv"
    summary_csv = RESULTS_DIR / f"summary_{timestamp}_k{k}.csv"
    results_jsonl = RESULTS_DIR / f"results_{timestamp}_k{k}.jsonl"

    if all_rows:
        write_results_csv(results_csv, all_rows)
        write_results_jsonl(results_jsonl, all_rows)
    if summaries:
        write_summary_csv(summary_csv, summaries)

    print("=" * 78)
    print(f"EVAL SUMMARY  ({timestamp}, retrieval k={k})")
    print("=" * 78)
    if summaries or skipped:
        print_summary_table(summaries, skipped)
    else:
        print("No configs produced results.")
    print()
    print(
        "Legend: NumAcc/BndAcc = number & boundary accuracy; KFhit = avg "
        "key_facts hit-rate\n"
        "        (comparison/qualitative are flagged needs_manual_review -- "
        "KFhit is a soft signal only).\n"
        "        Lat n/c/q/b = avg latency (s) per category: "
        "number/comparison/qualitative/boundary."
    )
    print()
    if all_rows:
        print(f"Wrote per-question results : {results_csv}")
        print(f"Wrote full records (jsonl) : {results_jsonl}")
    if summaries:
        print(f"Wrote per-config summary   : {summary_csv}")
    if not all_rows and not summaries:
        print("Nothing was written (all configs skipped).")


if __name__ == "__main__":
    main()

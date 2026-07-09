"""Re-score the most recent eval run with the current scoring logic.

Reads the newest ``eval/results/results_*.jsonl`` (which stores the full model
answers alongside the retrieved sources) and re-applies ALL scoring — number,
boundary, and key-facts — using the current rules in :mod:`eval.run_eval`,
*without* re-running any model. This is the cheap way to pick up a scoring fix
(e.g. the corrected boundary rule) across an existing run: no API calls, no slow
local Llama re-inference.

Scoring is the single source of truth in :mod:`eval.run_eval` — this module just
feeds the recorded answers back through :func:`eval.run_eval._score_record`, so
run and re-score always agree. The expected figures / key-facts are looked up
from :mod:`eval.gold_set` by ``question_id`` (they are not stored in the jsonl).

Outputs are written next to the source file with a ``_rescored`` suffix:
    results_<timestamp>_rescored.csv     one row per (config, question).
    summary_<timestamp>_rescored.csv     per-config aggregate metrics.
    results_<timestamp>_rescored.jsonl   full re-scored records.

Usage:
    python eval/rescore.py                    # newest results_*.jsonl
    python eval/rescore.py path/to/run.jsonl  # a specific run
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Make the project root importable when run as `python eval/rescore.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from eval.gold_set import by_id  # noqa: E402
from eval.run_eval import (  # noqa: E402
    RESULTS_DIR,
    _score_record,
    print_summary_table,
    summarize,
    write_results_csv,
    write_results_jsonl,
    write_summary_csv,
)


def find_latest_jsonl() -> Optional[Path]:
    """Return the newest ``results_*.jsonl`` that is not itself a re-score."""
    candidates = [
        p
        for p in RESULTS_DIR.glob("results_*.jsonl")
        if "_rescored" not in p.name
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _timestamp_of(source: Path) -> str:
    """Extract the ``<timestamp>`` from a ``results_<timestamp>.jsonl`` name."""
    stem = source.stem  # e.g. "results_20260709_124227"
    return stem[len("results_"):] if stem.startswith("results_") else stem


def load_records(path: Path) -> List[Dict]:
    """Read one JSON record per line from a results jsonl file."""
    records: List[Dict] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"  WARNING: skipping malformed line {line_no}: {exc}")
    return records


def rescore_record(record: Dict) -> Dict:
    """Re-score one recorded answer with the current scoring rules.

    Reuses :func:`eval.run_eval._score_record` so the number / boundary /
    key-facts logic is identical to a fresh run. The gold-set entry (which holds
    the expected figure and key-facts) is looked up by ``question_id``; if it is
    no longer in the gold set, the original record is returned unchanged.
    """
    question_id = record.get("question_id", "")
    try:
        question = by_id(question_id)
    except KeyError:
        print(
            f"  WARNING: '{question_id}' is not in the current gold set; "
            f"keeping its original score."
        )
        return record

    return _score_record(
        config_name=record.get("config", ""),
        question=question,
        answer=record.get("answer", "") or "",
        sources=record.get("sources", []) or [],
        latency=record.get("latency_seconds", 0.0) or 0.0,
        error=record.get("error", "") or "",
    )


def _passed_str(value: object) -> str:
    """Render a ``passed`` value (True / False / None) for the change report."""
    return "-" if value is None else str(value)


def report_changes(originals: List[Dict], rescored: List[Dict]) -> None:
    """Print the rows whose pass/fail verdict changed under the new scoring."""
    changed = [
        (o, n)
        for o, n in zip(originals, rescored)
        if o.get("passed") != n.get("passed")
    ]
    if not changed:
        print("No scores changed under the corrected rules.")
        return
    print(f"{len(changed)} score(s) changed under the corrected rules:")
    for old, new in changed:
        print(
            f"  {old.get('config', '?'):20} {old.get('question_id', '?'):24} "
            f"[{old.get('category', '?')}]  "
            f"{_passed_str(old.get('passed'))} -> {_passed_str(new.get('passed'))}"
        )
    print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Re-score the most recent eval run (or a given results_*.jsonl) "
            "with the current scoring logic, without re-running any model."
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to a results_*.jsonl to re-score (default: the newest one).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source = Path(args.source) if args.source else find_latest_jsonl()
    if source is None:
        print(f"No results_*.jsonl found in {RESULTS_DIR}. Run eval first.")
        return
    if not source.exists():
        print(f"Results file not found: {source}")
        return

    print(f"Re-scoring: {source}")
    originals = load_records(source)
    if not originals:
        print("No records to re-score.")
        return

    rescored = [rescore_record(r) for r in originals]

    # Group by config, preserving first-seen order, and summarize each.
    by_config: "OrderedDict[str, List[Dict]]" = OrderedDict()
    for rec in rescored:
        by_config.setdefault(rec["config"], []).append(rec)
    summaries = [summarize(cfg, rows) for cfg, rows in by_config.items()]

    # Write outputs alongside the source with a _rescored suffix.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _timestamp_of(source)
    results_csv = RESULTS_DIR / f"results_{timestamp}_rescored.csv"
    summary_csv = RESULTS_DIR / f"summary_{timestamp}_rescored.csv"
    results_jsonl = RESULTS_DIR / f"results_{timestamp}_rescored.jsonl"

    write_results_csv(results_csv, rescored)
    write_results_jsonl(results_jsonl, rescored)
    write_summary_csv(summary_csv, summaries)

    print()
    print("=" * 78)
    print(f"RESCORED SUMMARY  ({timestamp})")
    print("=" * 78)
    report_changes(originals, rescored)
    print_summary_table(summaries, skipped=[])
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
    print(f"Wrote per-question results : {results_csv}")
    print(f"Wrote full records (jsonl) : {results_jsonl}")
    print(f"Wrote per-config summary   : {summary_csv}")


if __name__ == "__main__":
    main()

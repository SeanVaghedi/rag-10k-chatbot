"""Gold-set of evaluation questions for the 10-K comparison chatbot.

This is the ground-truth used by :mod:`eval.run_eval`. It spans four categories,
each scored differently by the harness:

- ``number``      — a single figure lookup. ``expected`` carries the exact figure
                    string plus a list of accepted ``variants`` (alternate ways
                    of writing the same value). Auto-graded: pass if the figure
                    or any variant appears in the answer.
- ``comparison``  — a cross-company comparison. ``expected`` carries a
                    ``reference_answer`` (what a correct answer should say) and a
                    list of ``key_facts`` (short strings that should appear).
                    Not reliably auto-gradable — flagged for manual review; the
                    harness logs a ``key_facts`` hit-count as a soft signal.
- ``qualitative`` — an open-ended "how does each company describe X" question.
                    Same shape as ``comparison`` (reference + key_facts). Also
                    manual-review.
- ``boundary``    — the answer is NOT in the corpus and the model must refuse
                    rather than fabricate. ``expected`` carries
                    ``expected_behavior="refuse"``. Auto-graded: pass if the
                    answer refuses and states no fabricated figure.

The figures below are drawn from the Amazon, Alphabet, and Microsoft filings that
make up the corpus. Tesla (Q11) is intentionally absent from the corpus.

Each entry is a plain ``dict`` with keys: ``id``, ``question``, ``category``,
``expected``. The shape of ``expected`` varies by category as described above.
"""

from __future__ import annotations

from typing import Dict, List

# Valid category values (kept in sync with eval.run_eval).
CATEGORIES = ("number", "comparison", "qualitative", "boundary")


GOLD_SET: List[Dict] = [
    # ---------------------------------------------------------------- NUMBER
    {
        "id": "num-amazon-cash-fy2024",
        "question": (
            "How much cash, cash equivalents, and restricted cash did Amazon "
            "have at the end of fiscal 2024?"
        ),
        "category": "number",
        "expected": {
            "figure": "$82,312 million",
            "variants": ["82,312", "82.3 billion"],
        },
    },
    {
        "id": "num-amazon-netsales-fy2025",
        "question": "What was Amazon's total net sales for fiscal 2025?",
        "category": "number",
        "expected": {
            "figure": "$716,924 million",
            "variants": ["716,924", "716.9 billion"],
        },
    },
    {
        "id": "num-alphabet-revenue-fy2025",
        "question": "What was Alphabet's total revenue for fiscal 2025?",
        "category": "number",
        "expected": {
            "figure": "$402,836 million",
            "variants": ["402,836", "402.8 billion"],
        },
    },
    {
        "id": "num-microsoft-revenue-fy2025",
        "question": "What was Microsoft's total revenue for fiscal 2025?",
        "category": "number",
        "expected": {
            "figure": "$281,724 million",
            "variants": ["281,724", "281.7 billion"],
        },
    },
    {
        "id": "num-amazon-aws-fy2025",
        "question": "What was Amazon's AWS segment revenue for fiscal 2025?",
        "category": "number",
        "expected": {
            "figure": "$128,725 million",
            "variants": ["128,725", "128.7 billion"],
        },
    },
    # ------------------------------------ NUMBER — table disambiguation (HARD)
    # The five questions below stress-test multi-year financial-table reading:
    # each answer lives in one specific column/row of a table where an
    # adjacent-year value, or a beginning-vs-end value, is an easy wrong pick.
    # This is a known weak spot for RAG -- a single retrieved chunk often carries
    # several years side by side, so the model must pin the right column.
    #
    # VERIFIED: every figure below was read by hand from the filings in
    # data/pdfs/ and has since been human-verified against the cited
    # statement/page, so each entry now carries "needs_verification": False and
    # is a trusted scored question. The cited column/row is noted per entry.
    {
        "id": "num-amazon-cash-beginning-fy2024",
        "question": (
            "What was Amazon's cash, cash equivalents, and restricted cash at "
            "the BEGINNING of fiscal 2024?"
        ),
        "category": "number",
        "expected": {
            # Amazon Consolidated Statements of Cash Flows. Beginning-of-period
            # row, FY2024 column: $54,253 / $73,890 / $82,312 for 2023/2024/2025.
            # FY2024 beginning-of-period equals FY2023 end-of-period ($73,890M).
            "figure": "$73,890 million",
            "variants": ["73,890", "73890", "73.9 billion"],
            "trap": (
                "Beginning-of-period is easily confused with the FY2024 "
                "end-of-period value ($82,312 million). The correct figure also "
                "equals FY2023 end-of-period, so the same number appears twice "
                "in the statement (as 2023 END and as 2024 BEGINNING)."
            ),
            "needs_verification": False,
        },
    },
    {
        "id": "num-amazon-cash-end-fy2025",
        "question": (
            "What was Amazon's cash, cash equivalents, and restricted cash at "
            "the END of fiscal 2025?"
        ),
        "category": "number",
        "expected": {
            # Amazon Consolidated Statements of Cash Flows. End-of-period row,
            # FY2025 column: $73,890 / $82,312 / $90,106 for 2023/2024/2025.
            "figure": "$90,106 million",
            "variants": ["90,106", "90106", "90.1 billion"],
            "trap": (
                "Must distinguish FY2025 end-of-period ($90,106 million) from "
                "FY2024 end-of-period ($82,312 million) -- adjacent columns in "
                "the same end-of-period row."
            ),
            "needs_verification": False,
        },
    },
    {
        "id": "num-amazon-opex-fy2024",
        "question": "What was Amazon's total operating expenses for fiscal 2024?",
        "category": "number",
        "expected": {
            # Amazon Consolidated Statements of Operations. Total operating
            # expenses row: 537,933 / 569,366 / 636,949 for 2023/2024/2025. The
            # FY2024 value is the middle column.
            "figure": "$569,366 million",
            "variants": ["569,366", "569366", "569.4 billion"],
            "trap": (
                "Three-year income statement -- FY2024 is the middle column "
                "($569,366 million); easy to grab FY2025 ($636,949 million) or "
                "FY2023 ($537,933 million) instead."
            ),
            "needs_verification": False,
        },
    },
    {
        "id": "num-alphabet-netincome-fy2024",
        "question": (
            "What was Alphabet's net income for fiscal 2024 (the prior-year "
            "comparative shown in the FY2025 filing)?"
        ),
        "category": "number",
        "expected": {
            # Alphabet Consolidated Statements of Income. Net income row:
            # 73,795 / 100,118 / 132,170 for 2023/2024/2025. FY2024 is the
            # middle column.
            "figure": "$100,118 million",
            "variants": ["100,118", "100118", "100.1 billion"],
            "trap": (
                "Requires reading the FY2024 comparative column ($100,118 "
                "million), not the headline current-year FY2025 net income "
                "($132,170 million) nor FY2023 ($73,795 million)."
            ),
            "needs_verification": False,
        },
    },
    {
        "id": "num-microsoft-opincome-fy2024",
        "question": (
            "What was Microsoft's operating income for fiscal 2024 (the "
            "prior-year comparative in the FY2025 filing)?"
        ),
        "category": "number",
        "expected": {
            # Microsoft Income Statements. NOTE the column order is REVERSED
            # vs Amazon/Alphabet: "Year Ended June 30, 2025 2024 2023". Operating
            # income row: 128,528 / 109,433 / 88,523 for 2025/2024/2023. FY2024
            # is the middle column.
            "figure": "$109,433 million",
            "variants": ["109,433", "109433", "109.4 billion"],
            "trap": (
                "Double trap: FY2024 is the middle column AND Microsoft lists "
                "years most-recent-first (2025/2024/2023), so the leftmost "
                "column is FY2025 ($128,528 million), not FY2024. FY2023 is "
                "$88,523 million."
            ),
            "needs_verification": False,
        },
    },
    # ------------------------------------------------------------ COMPARISON
    {
        "id": "cmp-revenue-sources",
        "question": "Compare the main revenue sources for Amazon, Alphabet, and Microsoft.",
        "category": "comparison",
        "expected": {
            "reference_answer": (
                "Amazon's revenue comes mainly from online stores (retail) and "
                "third-party seller services, with AWS as the key cloud/profit "
                "engine. Alphabet's revenue is dominated by Google advertising, "
                "driven by Google Search (plus YouTube ads and Google Network). "
                "Microsoft's revenue is led by server products and cloud services "
                "(including Azure) and Microsoft 365 / productivity and business "
                "processes."
            ),
            "key_facts": [
                "online stores",
                "AWS",
                "advertising",
                "Search",
                "server products",
                "Microsoft 365",
            ],
        },
    },
    {
        "id": "cmp-largest-cloud",
        "question": (
            "Which of the three companies has the largest cloud business by "
            "revenue, and what are the figures?"
        ),
        "category": "comparison",
        "expected": {
            "reference_answer": (
                "Amazon's AWS is the largest cloud business by revenue at about "
                "$128,725 million (FY2025), ahead of Google Cloud at about "
                "$58,705 million. Microsoft reports its cloud within 'Server "
                "products and cloud services' / 'Microsoft Cloud' rather than a "
                "single directly comparable pure-cloud segment figure."
            ),
            "key_facts": [
                "AWS",
                "128,725",
                "Google Cloud",
                "58,705",
                "Microsoft Cloud",
            ],
        },
    },
    # ----------------------------------------------------------- QUALITATIVE
    {
        "id": "qual-cloud-competition",
        "question": "How does each company describe competition in cloud services?",
        "category": "qualitative",
        "expected": {
            "reference_answer": (
                "Each company characterizes the cloud / enterprise market as "
                "intensely competitive and rapidly evolving, naming large-scale "
                "competitors (each other — Amazon, Microsoft, Google — plus "
                "others such as Oracle, IBM, and Alibaba) and citing competition "
                "on price, performance, features, security, and scale."
            ),
            # No fixed key_facts were specified for this open-ended question;
            # scoring falls back to manual review of the reference_answer.
            "key_facts": [],
        },
    },
    {
        "id": "qual-china-risk",
        "question": "What risks related to operations in China do these companies mention?",
        "category": "qualitative",
        "expected": {
            "reference_answer": (
                "The filings note China-related risks such as geopolitical and "
                "regulatory tension, trade restrictions / tariffs and export "
                "controls, data / cybersecurity and localization requirements, "
                "reliance on China-based manufacturing or suppliers, and "
                "currency and market-access risk."
            ),
            "key_facts": [],
        },
    },
    # -------------------------------------------------------------- BOUNDARY
    {
        "id": "bnd-projected-fy2027",
        "question": "What is each company's projected revenue for fiscal 2027?",
        "category": "boundary",
        "expected": {
            "expected_behavior": "refuse",
            "note": (
                "Forward-looking FY2027 projections are not in the historical "
                "10-K filings; the model must decline rather than guess."
            ),
        },
    },
    {
        "id": "bnd-tesla-revenue",
        "question": "What was Tesla's total revenue according to these filings?",
        "category": "boundary",
        "expected": {
            "expected_behavior": "refuse",
            "note": (
                "Tesla is not part of the corpus (only Amazon, Alphabet, and "
                "Microsoft). The model must not fabricate a figure."
            ),
        },
    },
]


def by_category(category: str) -> List[Dict]:
    """Return the gold-set questions in ``category``."""
    return [q for q in GOLD_SET if q["category"] == category]


def by_id(question_id: str) -> Dict:
    """Return the single gold-set question with ``question_id`` (or raise)."""
    for q in GOLD_SET:
        if q["id"] == question_id:
            return q
    raise KeyError(f"No gold-set question with id '{question_id}'.")


def needs_verification(question: Dict) -> bool:
    """True if this question's expected answer still awaits human verification.

    Set on the harder table-disambiguation questions whose figures were read by
    hand from the filings and have not yet been confirmed against the source.
    """
    return bool((question.get("expected") or {}).get("needs_verification"))


if __name__ == "__main__":
    # Quick sanity view: `python eval/gold_set.py`
    pending = [q for q in GOLD_SET if needs_verification(q)]
    print(
        f"Gold set: {len(GOLD_SET)} questions "
        f"({len(pending)} awaiting human verification)"
    )
    for cat in CATEGORIES:
        qs = by_category(cat)
        n_pending = sum(1 for q in qs if needs_verification(q))
        suffix = f"  [{n_pending} need verification]" if n_pending else ""
        print(f"  {cat:12} {len(qs)}{suffix}")
    print()

    # Full set, grouped by category, flagging the unverified questions.
    for cat in CATEGORIES:
        qs = by_category(cat)
        if not qs:
            continue
        print(f"== {cat.upper()} ({len(qs)}) ==")
        for q in qs:
            flag = "  <-- NEEDS VERIFICATION" if needs_verification(q) else ""
            print(f"  {q['id']:34} {q['question']}{flag}")
        print()

    if pending:
        print("Awaiting human verification against the source filing:")
        for q in pending:
            exp = q.get("expected") or {}
            print(f"  - {q['id']:34} expected {exp.get('figure', '?')}")

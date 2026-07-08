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


if __name__ == "__main__":
    # Quick sanity view: `python eval/gold_set.py`
    print(f"Gold set: {len(GOLD_SET)} questions")
    for cat in CATEGORIES:
        qs = by_category(cat)
        print(f"  {cat:12} {len(qs)}")
    print()
    for q in GOLD_SET:
        print(f"  [{q['category']:11}] {q['id']:26} {q['question']}")

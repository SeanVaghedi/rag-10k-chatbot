"""Gold-set of evaluation questions for the 10-K comparison chatbot.

This is the ground-truth used by :mod:`eval.run_eval`. It spans five categories,
each scored differently by the harness:

- ``number``      — a single figure lookup. ``expected`` carries the exact figure
                    string plus a list of accepted ``variants`` (alternate ways
                    of writing the same value). Auto-graded: pass if the figure
                    or any variant appears in the answer.
- ``calculation`` — a derived figure (growth rate, margin, dollar change) the
                    model must compute from statement figures. ``expected``
                    carries the computed ``value`` and an ``answer_type``
                    (``"percent"`` or ``"dollars_millions"``). Auto-graded with
                    tolerance: within +/-0.3 percentage points for percents,
                    within +/-1% for dollar amounts (see
                    :func:`eval.run_eval.score_calculation`).
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
- ``hard``        — a multi-company, multi-statement question needing MANY
                    distinct figures from ALL THREE companies in one answer.
                    ``expected`` carries ``components``: a list of
                    ``{label, value, answer_type}`` dicts, one per figure a
                    correct answer must state. Auto-graded (see
                    :func:`eval.run_eval.score_hard`): pass only if EVERY
                    component appears within the calculation tolerances
                    (+/-0.3pp for percents, +/-1% for dollar amounts).
                    Refusal fails — all five are answerable from the corpus —
                    and does so automatically, since a refusal states none of
                    the required figures.

The figures below are drawn from the Amazon, Alphabet, and Microsoft filings that
make up the corpus. Tesla (Q11) is intentionally absent from the corpus.

Each entry is a plain ``dict`` with keys: ``id``, ``question``, ``category``,
``expected``. The shape of ``expected`` varies by category as described above.
"""

from __future__ import annotations

from typing import Dict, List

# Valid category values (kept in sync with eval.run_eval).
CATEGORIES = ("number", "calculation", "comparison", "qualitative", "boundary", "hard")


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
    # ------------------------------------------------------------ CALCULATION
    # Derived-figure questions: the model must COMPUTE growth rates, margins,
    # or dollar changes from statement figures (none of these ratios appear
    # verbatim in the filings). Every input figure below is verified — either
    # by a number question above or directly against the filings. The
    # arithmetic behind each expected value is shown so it can be checked.
    # Scored by eval.run_eval.score_calculation with tolerance: percents pass
    # within +/-0.3 percentage points; dollar amounts within +/-1%.
    {
        # AWS net sales: FY2024 $107,556M -> FY2025 $128,725M.
        # (128,725 - 107,556) / 107,556 = 21,169 / 107,556 = 0.19682 -> 19.7%
        "id": "calc-aws-growth-fy2025",
        "question": (
            "What was Amazon's AWS revenue growth rate from fiscal 2024 to "
            "fiscal 2025?"
        ),
        "category": "calculation",
        "expected": {"value": 19.7, "answer_type": "percent"},
    },
    {
        # Amazon total net sales: FY2024 $637,959M -> FY2025 $716,924M.
        # 716,924 - 637,959 = $78,965M
        "id": "calc-amazon-netsales-change-fy2025",
        "question": (
            "By how much did Amazon's total net sales increase from fiscal "
            "2024 to fiscal 2025, in dollars?"
        ),
        "category": "calculation",
        "expected": {"value": 78965, "answer_type": "dollars_millions"},
    },
    {
        # Alphabet total revenue: FY2024 $350,018M -> FY2025 $402,836M.
        # (402,836 - 350,018) / 350,018 = 52,818 / 350,018 = 0.15090 -> 15.1%
        "id": "calc-alphabet-revenue-growth-fy2025",
        "question": (
            "What was Alphabet's revenue growth rate from fiscal 2024 to "
            "fiscal 2025?"
        ),
        "category": "calculation",
        "expected": {"value": 15.1, "answer_type": "percent"},
    },
    {
        # Microsoft FY2025: operating income $128,528M / total revenue $281,724M.
        # 128,528 / 281,724 = 0.45622 -> 45.6%
        "id": "calc-microsoft-opmargin-fy2025",
        "question": "What was Microsoft's operating margin for fiscal 2025?",
        "category": "calculation",
        "expected": {"value": 45.6, "answer_type": "percent"},
    },
    {
        # Amazon FY2025: operating income $79,975M / total net sales $716,924M.
        # 79,975 / 716,924 = 0.11155 -> 11.2%
        "id": "calc-amazon-opmargin-fy2025",
        "question": "What was Amazon's operating margin for fiscal 2025?",
        "category": "calculation",
        "expected": {"value": 11.2, "answer_type": "percent"},
    },
    {
        # Microsoft operating income: FY2024 $109,433M -> FY2025 $128,528M.
        # 128,528 - 109,433 = $19,095M
        "id": "calc-microsoft-opincome-change-fy2025",
        "question": (
            "How much did Microsoft's operating income increase from fiscal "
            "2024 to fiscal 2025, in dollars?"
        ),
        "category": "calculation",
        "expected": {"value": 19095, "answer_type": "dollars_millions"},
    },
    {
        # Alphabet net income: FY2024 $100,118M -> FY2025 $132,170M.
        # (132,170 - 100,118) / 100,118 = 32,052 / 100,118 = 0.32014 -> 32.0%
        "id": "calc-alphabet-netincome-growth-fy2025",
        "question": (
            "What was Alphabet's net income growth rate from fiscal 2024 to "
            "fiscal 2025?"
        ),
        "category": "calculation",
        "expected": {"value": 32.0, "answer_type": "percent"},
    },
    {
        # Microsoft FY2025: gross margin $193,893M / total revenue $281,724M.
        # 193,893 / 281,724 = 0.68824 -> 68.8%
        "id": "calc-microsoft-grossmargin-fy2025",
        "question": (
            "What was Microsoft's gross margin percentage for fiscal 2025?"
        ),
        "category": "calculation",
        "expected": {"value": 68.8, "answer_type": "percent"},
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
    # ------------------------------------------------------------------ HARD
    # Multi-company, multi-statement stress tier. Each question needs MANY
    # distinct figures from ALL THREE companies, drawn from different parts of
    # the filings (tax reconciliation note, income statement, segment note,
    # cash flow statement), combined in a single answer. This is the retrieval
    # pattern the bot currently fails on; these five establish the baseline
    # failure rate BEFORE any retrieval fix. They deliberately span different
    # question shapes and different filing sections, so passing them
    # demonstrates general capability rather than memorization of a phrasing.
    #
    # Scoring (eval.run_eval.score_hard): PASS only if EVERY component figure
    # appears in the answer within the calculation tolerances (+/-0.3
    # percentage points for percents, +/-1% relative for dollar amounts).
    # Refusal = fail, enforced implicitly: a refusal states none of the
    # required figures, so no component matches.
    #
    # NEEDS VERIFICATION: every figure below was read by hand from the PDFs in
    # data/pdfs/ (source statement/note cited per entry) but has NOT yet been
    # human-verified, so every entry carries "needs_verification": True.
    # Verify each component against the cited source before trusting HardAcc.
    {
        # Effective tax rate reconciliations, FY2025, all three companies:
        #   Amazon   (Income Taxes note): provision $19,087M on pretax income
        #            $97,311M -> effective 19.6% (printed in the table).
        #            Gap: 21.0 - 19.6 = 1.4pp. Largest reconciling item:
        #            state and local income taxes +$2,455M (+2.5pp), in a
        #            near-tie with R&D tax credits -$2,403M (-2.5pp) --
        #            treat either as correct when verifying.
        #   Alphabet (Income Taxes note): provision $26,656M on pretax income
        #            $158,826M -> effective 16.8% (printed). Gap: 21.0 - 16.8
        #            = 4.2pp, the LARGEST of the three. Largest reconciling
        #            item: foreign-derived intangible income deduction
        #            -$3,931M (-2.5pp).
        #   Microsoft (Income Taxes note; percent-only table): effective
        #            17.6% (printed). Gap: 21.0 - 17.6 = 3.4pp. Largest
        #            reconciling item: foreign earnings taxed at lower rates
        #            (Ireland) -1.5pp; state income taxes is +1.5pp of equal
        #            magnitude, but the filing narrative credits lower-taxed
        #            foreign earnings as the primary driver.
        # Computed answer: Alphabet had the largest gap -- 4.2pp below the 21%
        # statutory rate (effective 16.8%), vs Microsoft 3.4pp (17.6%) and
        # Amazon 1.4pp (19.6%).
        "id": "hard-tax-diff",
        "question": (
            "Using the effective tax rate reconciliation in each 10-K, which "
            "of Amazon, Alphabet, and Microsoft had the largest gap between "
            "the 21% U.S. federal statutory tax rate and its effective tax "
            "rate in the most recent fiscal year? Give each company's "
            "effective tax rate, and the largest reconciling item each "
            "company discloses."
        ),
        "category": "hard",
        "expected": {
            "components": [
                {
                    "label": "Amazon effective tax rate FY2025",
                    "value": 19.6,
                    "answer_type": "percent",
                },
                {
                    "label": "Microsoft effective tax rate FY2025",
                    "value": 17.6,
                    "answer_type": "percent",
                },
                {
                    "label": "Alphabet effective tax rate FY2025 (largest gap)",
                    "value": 16.8,
                    "answer_type": "percent",
                },
            ],
            "needs_verification": True,
        },
    },
    {
        # R&D intensity, most recent FY (FY2025), income statement lines:
        #   Alphabet  R&D $61,087M / revenues $402,836M = 15.16% -> 15.2%
        #             (the filing's own table rounds this to "15 %").
        #   Amazon    technology and infrastructure $108,521M / net sales
        #             $716,924M = 15.14% -> 15.1% (the filing's "Percent of
        #             Net Sales" table prints 15.1%). Amazon reports no
        #             standalone R&D line; the question pins it to this line.
        #   Microsoft R&D $32,488M / revenue $281,724M = 11.53% -> 11.5%
        #             (CAUTION: Microsoft's MD&A prints this rounded as
        #             "12%", which is OUTSIDE the +/-0.3pp tolerance of 11.5;
        #             decide at verification time whether that matters).
        # Computed answer: Alphabet 15.2% >= Amazon 15.1% > Microsoft 11.5%
        # (Alphabet and Amazon are nearly tied -- and within grading
        # tolerance of each other, so either figure satisfies both
        # components; Microsoft is clearly lowest).
        "id": "hard-rd-intensity",
        "question": (
            "For the most recent fiscal year, what was research and "
            "development spending as a percentage of total revenue for "
            "Amazon, Alphabet, and Microsoft, ranked from highest to lowest? "
            "For Amazon, use its 'technology and infrastructure' expense "
            "line, which contains its R&D spending."
        ),
        "category": "hard",
        "expected": {
            "components": [
                {
                    "label": "Alphabet R&D as % of revenue FY2025",
                    "value": 15.2,
                    "answer_type": "percent",
                },
                {
                    "label": "Amazon technology and infrastructure as % of net sales FY2025",
                    "value": 15.1,
                    "answer_type": "percent",
                },
                {
                    "label": "Microsoft R&D as % of revenue FY2025",
                    "value": 11.5,
                    "answer_type": "percent",
                },
            ],
            "needs_verification": True,
        },
    },
    {
        # Cloud segment operating margins, FY2025 -- none of these margins is
        # printed in the filings; each must be computed from the segment
        # revenue and operating income disclosures:
        #   Microsoft Intelligent Cloud (MD&A Segment Results table):
        #            op income $44,589M / revenue $106,265M = 41.96% -> 42.0%
        #   Amazon AWS (Segment Information note):
        #            op income $45,606M / net sales $128,725M = 35.43% -> 35.4%
        #   Alphabet Google Cloud (segment note / MD&A segment tables):
        #            op income $13,910M / revenues $58,705M = 23.69% -> 23.7%
        # Computed answer: Microsoft Intelligent Cloud 42.0% > Amazon AWS
        # 35.4% > Google Cloud 23.7%.
        "id": "hard-cloud-margin",
        "question": (
            "What was the operating margin of Amazon's AWS segment, "
            "Alphabet's Google Cloud segment, and Microsoft's Intelligent "
            "Cloud segment in the most recent fiscal year? Rank the three "
            "cloud businesses from highest to lowest operating margin, with "
            "the margin percentages."
        ),
        "category": "hard",
        "expected": {
            "components": [
                {
                    "label": "Microsoft Intelligent Cloud operating margin FY2025",
                    "value": 42.0,
                    "answer_type": "percent",
                },
                {
                    "label": "Amazon AWS operating margin FY2025",
                    "value": 35.4,
                    "answer_type": "percent",
                },
                {
                    "label": "Google Cloud operating margin FY2025",
                    "value": 23.7,
                    "answer_type": "percent",
                },
            ],
            "needs_verification": True,
        },
    },
    {
        # Capex from the consolidated statements of cash flows, FY2024 ->
        # FY2025 (gross purchases line, not net of proceeds):
        #   Amazon    "Purchases of property and equipment":
        #             $82,999M -> $131,819M = +$48,820M = +58.8%  <- largest $
        #   Alphabet  "Purchases of property and equipment":
        #             $52,535M -> $91,447M = +$38,912M (= +74.1%, the largest
        #             PERCENTAGE increase, but not the largest dollar one)
        #   Microsoft "Additions to property and equipment" (its name for
        #             the same line): $44,477M -> $64,551M = +$20,074M
        #             (= +45.1%)
        # Computed answer: Amazon had the largest dollar increase, +$48,820M
        # (+58.8%), from $82,999M to $131,819M.
        # Verification caveat: Amazon also discloses a NET capex line
        # ("Purchases of property and equipment, net of proceeds from sales
        # and incentives": $77,658M -> $128,320M, +$50,662M / +65.2%). An
        # answer built on the net line fails the tolerances here; the
        # question wording targets the gross purchases line.
        "id": "hard-capex-trend",
        "question": (
            "Which of Amazon, Alphabet, and Microsoft had the largest dollar "
            "increase in purchases of property and equipment (capital "
            "expenditures) from fiscal 2024 to fiscal 2025, per their cash "
            "flow statements? Give each company's figure for both years, and "
            "state the largest increase in dollars and as a percentage."
        ),
        "category": "hard",
        "expected": {
            "components": [
                {
                    "label": "Amazon capex FY2024",
                    "value": 82999,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Amazon capex FY2025",
                    "value": 131819,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Alphabet capex FY2024",
                    "value": 52535,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Alphabet capex FY2025",
                    "value": 91447,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Microsoft capex FY2024",
                    "value": 44477,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Microsoft capex FY2025",
                    "value": 64551,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Amazon capex increase FY2024->FY2025 (largest)",
                    "value": 48820,
                    "answer_type": "dollars_millions",
                },
                {
                    "label": "Amazon capex increase percentage",
                    "value": 58.8,
                    "answer_type": "percent",
                },
            ],
            "needs_verification": True,
        },
    },
    {
        # Mixed statement structures, FY2025:
        #   Microsoft prints a gross margin line on its income statement:
        #             $193,893M / revenue $281,724M = 68.82% -> 68.8%
        #   Alphabet  prints no gross profit line; compute revenues
        #             $402,836M - cost of revenues $162,535M = $240,301M
        #             -> 240,301 / 402,836 = 59.65% -> 59.7%
        #   Amazon    reports neither gross profit nor a conventional cost of
        #             revenue structure, so the question pins it to operating
        #             margin: operating income $79,975M / net sales $716,924M
        #             = 11.16% -> 11.2%
        # Computed answer: Microsoft 68.8% (gross) > Alphabet 59.7% (gross) >
        # Amazon 11.2% (operating).
        # Verification caveat: an answer that instead computes an Amazon
        # gross-style margin from cost of sales ((716,924 - 356,414) /
        # 716,924 = 50.3%) fails the 11.2 component; the question wording
        # pins Amazon to operating margin to avoid that ambiguity.
        "id": "hard-margin-compare",
        "question": (
            "Compare profitability margins across the three companies for "
            "the most recent fiscal year: report gross margin for Microsoft "
            "and Alphabet, and operating margin for Amazon (which does not "
            "report gross profit). Rank the three margins from highest to "
            "lowest, with percentages."
        ),
        "category": "hard",
        "expected": {
            "components": [
                {
                    "label": "Microsoft gross margin FY2025",
                    "value": 68.8,
                    "answer_type": "percent",
                },
                {
                    "label": "Alphabet gross margin FY2025",
                    "value": 59.7,
                    "answer_type": "percent",
                },
                {
                    "label": "Amazon operating margin FY2025",
                    "value": 11.2,
                    "answer_type": "percent",
                },
            ],
            "needs_verification": True,
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

    Set on questions whose figures were read by hand from the filings and have
    not yet been confirmed against the source — currently the entire ``hard``
    tier (the table-disambiguation number questions carried this flag until
    their figures were verified).
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
            if "components" in exp:
                expected_str = "; ".join(
                    f"{c['label']}={c['value']}" for c in exp["components"]
                )
            else:
                expected_str = exp.get("figure", "?")
            print(f"  - {q['id']:34} expected {expected_str}")

"""Evaluation questions for the 10-K comparison chatbot.

Planned responsibilities:

- Hold a curated set of test questions spanning single-company lookups and
  cross-company comparisons (Alphabet vs. Amazon vs. Microsoft).
- For each question, capture the companies involved and an expected-answer or
  reference note (e.g. which section/metric the answer should cite) so the
  scoring harness has ground truth to grade against.

The list below is a placeholder to be expanded during implementation.
"""

# Each entry (once implemented) will look like:
#   {
#       "id": "cloud-revenue-compare",
#       "question": "How does cloud segment revenue compare across the three?",
#       "companies": ["Alphabet", "Amazon", "Microsoft"],
#       "reference": "...",   # expected facts / citation targets
#   }
EVAL_QUESTIONS: list = []

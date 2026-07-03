"""PDF loading and document tagging for 10-K filings.

Planned responsibilities:

- Discover 10-K PDFs in ``data/pdfs/`` and load them into LangChain
  ``Document`` objects (via ``pypdf`` / ``PyPDFLoader``).
- Infer and attach metadata to each document/page: company (Alphabet, Amazon,
  Microsoft), fiscal year, source filename, and page number.
- Provide a normalized corpus that downstream chunking can consume, so every
  retrieved chunk can be traced back to a specific company/year/page.
"""

from pathlib import Path
from typing import List


def load_filings(pdf_dir: Path) -> List["object"]:
    """Load all 10-K PDFs from ``pdf_dir`` into tagged ``Document`` objects.

    Each returned document carries metadata (company, year, source, page) so
    retrieval results remain attributable. To be implemented.
    """
    raise NotImplementedError

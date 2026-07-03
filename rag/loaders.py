"""PDF loading and metadata tagging for 10-K filings.

Loads every 10-K PDF in a directory via LangChain's ``PyPDFLoader`` (one
``Document`` per page) and tags each page with structured metadata so retrieved
chunks stay attributable to a specific company / year / page.

Expected filename pattern: ``{company}_10k_{year}.pdf``
(e.g. ``amazon_10k_2024.pdf``, ``alphabet_10k_2024.pdf``,
``microsoft_10k_2024.pdf``). Filenames that don't match raise a clear error.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

# {company}_10k_{4-digit-year}.pdf — case-insensitive, company may contain
# letters, digits and hyphens (e.g. "alphabet", "berkshire-hathaway").
_FILENAME_RE = re.compile(r"^(?P<company>[a-z0-9-]+)_10k_(?P<year>\d{4})\.pdf$", re.IGNORECASE)


def _parse_filename(filename: str) -> Tuple[str, int]:
    """Infer ``(company, year)`` from a 10-K filename.

    Raises:
        ValueError: if ``filename`` does not match ``{company}_10k_{year}.pdf``.
    """
    match = _FILENAME_RE.match(filename)
    if not match:
        raise ValueError(
            f"Filename '{filename}' does not match the expected 10-K pattern "
            f"'{{company}}_10k_{{year}}.pdf' (e.g. 'amazon_10k_2024.pdf'). "
            f"Rename the file and try again."
        )
    return match.group("company").lower(), int(match.group("year"))


def load_10k_pdfs(pdf_dir: str) -> List[Document]:
    """Load and tag every 10-K PDF in ``pdf_dir``.

    Each page becomes a LangChain ``Document`` with metadata:
    ``company``, ``year``, ``source_filename``, and ``page`` (1-indexed).

    Raises:
        FileNotFoundError: if ``pdf_dir`` does not exist.
        ValueError: if no PDFs are found, or a filename is malformed.
    """
    directory = Path(pdf_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"PDF directory does not exist: {directory}")

    pdf_paths = sorted(directory.glob("*.pdf"))
    if not pdf_paths:
        raise ValueError(
            f"No PDF files found in '{directory}'. Place the 10-K filings there "
            f"(e.g. 'amazon_10k_2024.pdf')."
        )

    documents: List[Document] = []
    for pdf_path in pdf_paths:
        company, year = _parse_filename(pdf_path.name)
        # PyPDFLoader returns one Document per page, in page order.
        pages = PyPDFLoader(str(pdf_path)).load()
        for page_number, page in enumerate(pages, start=1):
            page.metadata.update(
                {
                    "company": company,
                    "year": year,
                    "source_filename": pdf_path.name,
                    "page": page_number,
                }
            )
            documents.append(page)

    return documents

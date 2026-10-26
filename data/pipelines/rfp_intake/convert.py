"""PDF → Markdown conversion via MarkItDown (before any agent reads the RFP)."""

from __future__ import annotations

from pathlib import Path


def pdf_to_markdown(pdf_path: Path, markdown_path: Path) -> str:
    """Convert a PDF to Markdown and write ``markdown_path``. Returns the text."""
    from markitdown import MarkItDown

    if not pdf_path.is_file():
        raise FileNotFoundError(f"RFP PDF not found: {pdf_path}")

    md = MarkItDown()
    result = md.convert(str(pdf_path))
    text = (result.text_content or "").strip()
    if not text:
        raise ValueError("MarkItDown produced empty Markdown for the uploaded PDF")

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(text, encoding="utf-8")
    return text

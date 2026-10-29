"""Turn files a person uploads into plain text the agents can use.

No Streamlit import, so it can be tested on its own.
"""

from __future__ import annotations

import io
import re

SUPPORTED = ["pdf", "docx", "txt", "md", "csv"]

DEFAULT_BUDGET = 6000   # characters of uploaded text sent to the writer, across all files
MAX_BUDGET = 20000      # upper limit offered in the UI (free model tiers have per-minute token limits)


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _read_plain(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _read_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Reading PDFs needs the pypdf package. Run: python -m pip install pypdf") from exc
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001
            raise ValueError("This PDF is password-protected.") from exc
    pages = [(page.extract_text() or "") for page in reader.pages]
    text = "\n\n".join(pages)
    if not text.strip():
        raise ValueError("No text found. This looks like a scanned PDF, which needs OCR first.")
    return text


def _read_docx(data: bytes) -> str:
    try:
        import docx
    except ImportError as exc:
        raise RuntimeError("Reading Word files needs the python-docx package. Run: python -m pip install python-docx") from exc
    document = docx.Document(io.BytesIO(data))
    lines = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(lines)


def extract_text(name: str, data: bytes) -> str:
    """Return the cleaned text of one file. Raises ValueError/RuntimeError with a message fit to show the user."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in ("txt", "md", "csv"):
        text = _read_plain(data)
    elif ext == "pdf":
        text = _read_pdf(data)
    elif ext == "docx":
        text = _read_docx(data)
    else:
        raise ValueError(f"Files of type .{ext or '?'} aren't supported. Use PDF, Word, text, Markdown or CSV.")
    text = _clean(text)
    if not text:
        raise ValueError("The file is empty.")
    return text


def build_material(files: list[tuple[str, bytes]], budget: int = DEFAULT_BUDGET) -> tuple[str, list[dict]]:
    """Read every file and share `budget` characters between them.

    Returns (text for the writer, one report row per file). A file that can't be read gets an
    'error' row and doesn't stop the others.
    """
    rows: list[dict] = []
    texts: list[tuple[str, str]] = []
    for name, data in files:
        try:
            text = extract_text(name, data)
        except (ValueError, RuntimeError) as exc:
            rows.append({"name": name, "error": str(exc)})
            continue
        except Exception as exc:  # noqa: BLE001 - a corrupt file shouldn't crash the app
            rows.append({"name": name, "error": f"Couldn't read this file ({type(exc).__name__})."})
            continue
        texts.append((name, text))
        rows.append({"name": name, "chars": len(text), "used": 0, "truncated": False})

    if not texts:
        return "", rows

    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        raise ValueError("budget must be a positive integer")

    parts = []
    by_name = {r["name"]: r for r in rows if "error" not in r}
    remaining = budget
    for index, (name, text) in enumerate(texts):
        files_left = len(texts) - index
        # Recalculate the share after each file so short documents do not waste
        # the budget, and the total extracted text never exceeds the requested cap.
        share = remaining // files_left
        used = text[:share]
        row = by_name[name]
        row["used"] = len(used)
        row["truncated"] = len(text) > len(used)
        remaining -= len(used)
        parts.append(f"DOCUMENT: {name}\n{used}")
    return "\n\n".join(parts), rows

"""Advanced options and how they change what the agents are asked to do.

No Streamlit import, so it can be tested on its own.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

STYLES = {
    "Standard report": "",
    "Executive brief": (
        "Make it a concise executive brief of about 300 to 400 words. Lead with the single most important "
        "takeaway, keep each key finding to two sentences, and keep the same section headings."
    ),
    "Deep dive": (
        "Make it a thorough deep dive of about 1,800 to 2,500 words. Give specifics, numbers and context in "
        "each key finding, and point out where sources disagree or the evidence is thin."
    ),
}

AUDIENCES = {
    "General reader": "Write in plain language for a general reader and explain any technical term the first time it appears.",
    "Student": "Write for a student: explain the ideas step by step and define key terms.",
    "Professional": "Write for a working professional: be practical and direct, and focus on what matters for decisions.",
    "Expert": "Write for an expert reader: use precise terminology and skip basic background.",
}

LANGUAGES = ["English", "Urdu", "Arabic", "Spanish", "French", "German", "Hindi"]

SEARCH_DEPTHS = ["Basic", "Advanced"]

MAX_PREFERRED_URLS = 3


def parse_urls(text: str) -> list[str]:
    """Pick out http(s) links, one per line or space-separated. Drops duplicates, keeps the first few."""
    seen: dict[str, None] = {}
    for token in re.split(r"[\s,]+", text or ""):
        token = token.strip().lstrip("(<[\"'").rstrip(".,;)>]\"'")
        parsed = urlparse(token)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            seen.setdefault(token, None)
    return list(seen)[:MAX_PREFERRED_URLS]


def writing_instructions(style: str, audience: str, language: str, has_documents: bool) -> str:
    """Extra instructions appended to the topic the writer receives. Empty string means 'defaults'."""
    lines = []
    if STYLES.get(style):
        lines.append(STYLES[style])
    if audience != "General reader" and AUDIENCES.get(audience):
        lines.append(AUDIENCES[audience])
    if language and language != "English":
        lines.append(f"Write the whole report in {language}, but keep URLs and source titles unchanged.")
    if has_documents:
        lines.append(
            "The research includes documents the user uploaded. Treat them as primary source material "
            "and mention which file each point comes from."
        )
    if not lines:
        return ""
    return "\n\nWriting instructions (follow these as well as the structure above):\n" + "\n".join(f"- {l}" for l in lines)


def reader_prompt(topic: str, search_results: str, urls: list[str]) -> str:
    """What the reader agent is asked. With links from the user it reads those instead of choosing one."""
    if urls:
        listed = "\n".join(f"- {u}" for u in urls)
        return (
            f"Scrape each of these pages for deeper content about '{topic}', one at a time, "
            f"then report what each one says:\n{listed}"
        )
    return (
        f"Based on the following search results about '{topic}', "
        f"pick the most relevant URL and scrape it for deeper content.\n\n"
        f"Search Results:\n{search_results[:800]}"
    )

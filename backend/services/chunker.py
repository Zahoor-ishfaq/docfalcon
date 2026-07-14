"""Semantic chunker. Rough token estimate: 1 token ≈ 4 chars (multilingual approx)."""

import re

CHARS_PER_TOKEN = 4
CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50
CHUNK_CHARS = CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS = OVERLAP_TOKENS * CHARS_PER_TOKEN

# Contract heading heuristic: numbered clauses, ALL-CAPS lines, or "Article N".
HEADING_RE = re.compile(r"^\s*(\d+\.|Article\s+\d+|[A-Z][A-Z\s]{4,}:?)\s*$", re.MULTILINE)


def _split_by_headings(text: str) -> list[str]:
    """Split contract text on heading lines; keep heading with its section."""
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [text]
    sections, prev = [], 0
    for m in matches:
        if m.start() > prev:
            sections.append(text[prev:m.start()].strip())
        prev = m.start()
    sections.append(text[prev:].strip())
    return [s for s in sections if s]


def _window(text: str) -> list[str]:
    """Sliding window with overlap. Splits at whitespace to avoid breaking words."""
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks, i = [], 0
    while i < len(text):
        end = min(i + CHUNK_CHARS, len(text))
        # Snap to nearest whitespace before `end` to keep words intact.
        if end < len(text):
            ws = text.rfind(" ", i, end)
            if ws > i + CHUNK_CHARS // 2:
                end = ws
        chunks.append(text[i:end].strip())
        if end == len(text):
            break
        i = end - OVERLAP_CHARS
    return [c for c in chunks if c]


def chunk(text: str, doc_type: str) -> list[str]:
    """Return list of text chunks. Iqama/visa → single chunk; contracts → section-aware."""
    text = (text or "").strip()
    if not text:
        return []
    if doc_type in ("iqama", "visa"):
        return [text]  # short docs — no benefit from splitting
    sections = _split_by_headings(text)
    out = []
    for s in sections:
        out.extend(_window(s))
    return out
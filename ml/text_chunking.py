"""Structure-aware document chunking for domain positive files."""

from __future__ import annotations

import re
from dataclasses import dataclass

WORD_RE = re.compile(r"\S+")

HEADER_PATTERNS = (
    re.compile(r"^#{1,4}\s+\S"),
    re.compile(r"^\d+(?:\.\d+)*\s+\S"),
    re.compile(r"^(?:Chapter|Section|Part|Appendix)\s+\d", re.IGNORECASE),
    re.compile(r"^[A-Z][A-Z0-9\s\-_/]{4,}$"),
)

BOILERPLATE_RE = re.compile(
    r"^(table of contents|copyright|all rights reserved)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChunkConfig:
    min_words: int = 150
    max_words: int = 500
    overlap_words: int = 50
    whole_file_max_words: int = 500
    stub_min_words: int = 30
    max_file_fraction: float = 0.10


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", text).strip()


def is_header_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 200:
        return False
    return any(p.search(stripped) for p in HEADER_PATTERNS)


def is_boilerplate(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if word_count(stripped) < 3 and BOILERPLATE_RE.search(stripped):
        return True
    return bool(BOILERPLATE_RE.match(stripped))


def split_into_units(text: str) -> list[tuple[str, str]]:
    """Split into (section_title, paragraph_block) units."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    units: list[tuple[str, str]] = []
    section = ""
    para_lines: list[str] = []

    def flush_para() -> None:
        nonlocal para_lines
        if not para_lines:
            return
        block = normalize_whitespace(" ".join(para_lines))
        para_lines = []
        if block and not is_boilerplate(block):
            units.append((section, block))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue
        if is_header_line(stripped):
            flush_para()
            section = re.sub(r"^#+\s*", "", stripped).strip()[:120]
            continue
        para_lines.append(stripped)

    flush_para()
    if units:
        return units
    whole = normalize_whitespace(text)
    return [("", whole)] if whole else []


def merge_units(
    units: list[tuple[str, str]],
    min_words: int,
    max_words: int,
) -> list[tuple[str, str]]:
    """Merge adjacent units upward to min_words; flush before exceeding max_words."""
    if not units:
        return []

    merged: list[tuple[str, str]] = []
    buf_section = ""
    buf_parts: list[str] = []
    buf_words = 0

    def flush() -> None:
        nonlocal buf_section, buf_parts, buf_words
        if not buf_parts:
            return
        body = normalize_whitespace(" ".join(buf_parts))
        if body and word_count(body) >= 1:
            merged.append((buf_section, body))
        buf_section = ""
        buf_parts = []
        buf_words = 0

    for section, unit_text in units:
        uw = word_count(unit_text)
        if uw == 0 or is_boilerplate(unit_text):
            continue

        if buf_words == 0:
            buf_section = section
            buf_parts = [unit_text]
            buf_words = uw
            continue

        if buf_words < min_words or (buf_words + uw <= max_words):
            if section and section != buf_section and buf_words >= min_words:
                buf_section = f"{buf_section}; {section}" if buf_section else section
            buf_parts.append(unit_text)
            buf_words += uw
        else:
            flush()
            buf_section = section
            buf_parts = [unit_text]
            buf_words = uw

    flush()
    return merged


def split_long_text(text: str, max_words: int, overlap_words: int) -> list[str]:
    """Word-window split with overlap for bodies that exceed max_words."""
    words = WORD_RE.findall(text)
    if len(words) <= max_words:
        return [text]

    step = max(max_words - overlap_words, 1)
    parts: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        parts.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += step
    return parts


def format_chunk(doc_name: str, section: str, body: str) -> str:
    section_part = section.strip() if section else "document"
    header = f"[doc: {doc_name} | section: {section_part}]"
    return f"{header}\n\n{body.strip()}"


def chunk_document(
    text: str,
    doc_name: str,
    config: ChunkConfig | None = None,
) -> list[dict[str, str]]:
    """Return chunk dicts: section, body, text (with context header)."""
    cfg = config or ChunkConfig()
    cleaned = text.strip()
    if not cleaned:
        return []

    wc = word_count(cleaned)
    if wc < cfg.stub_min_words:
        return []

    if wc <= cfg.whole_file_max_words:
        body = normalize_whitespace(cleaned)
        return [
            {
                "section": "document",
                "body": body,
                "text": format_chunk(doc_name, "document", body),
            }
        ]

    units = split_into_units(cleaned)
    merged = merge_units(units, cfg.min_words, cfg.max_words)

    chunks: list[dict[str, str]] = []
    for section, body in merged:
        if word_count(body) < cfg.stub_min_words:
            continue
        for part in split_long_text(body, cfg.max_words, cfg.overlap_words):
            if word_count(part) < cfg.stub_min_words and wc > cfg.whole_file_max_words:
                continue
            chunks.append(
                {
                    "section": section,
                    "body": part,
                    "text": format_chunk(doc_name, section, part),
                }
            )

    if not chunks and wc >= cfg.stub_min_words:
        body = normalize_whitespace(cleaned)
        chunks.append(
            {
                "section": "document",
                "body": body,
                "text": format_chunk(doc_name, "document", body),
            }
        )
    return chunks


def file_doc_id(path_stem: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", path_stem).strip("_").lower()
    return f"domain_{slug or 'doc'}"


def apply_proportional_cap(
    rows: list[dict[str, str]],
    max_fraction: float = 0.10,
) -> list[dict[str, str]]:
    """Limit any single source file to max_fraction of all chunk rows."""
    if not rows or max_fraction <= 0:
        return rows

    from collections import defaultdict

    def source_key(doc_id: str) -> str:
        if "_p" in doc_id:
            return doc_id.rsplit("_p", 1)[0]
        return doc_id

    by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_source[source_key(row["doc_id"])].append(row)

    total = len(rows)
    cap = max(1, int(total * max_fraction))
    out: list[dict[str, str]] = []

    for _source, group in by_source.items():
        if len(group) <= cap:
            out.extend(group)
            continue
        step = len(group) / cap
        indices = [min(int(round(i * step)), len(group) - 1) for i in range(cap)]
        seen: set[int] = set()
        for idx in indices:
            if idx not in seen:
                out.append(group[idx])
                seen.add(idx)
    return out

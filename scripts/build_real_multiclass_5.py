#!/usr/bin/env python3
"""Build 5-class real dataset: domain (positive files) + AG News (4 topics).

Output schema (minimum for modeling):
  doc_id, text, topic, split

Topics: domain | world | sports | business | sci_tech

Usage (from repo root):

  # Partial dataset — AG News negatives only
  python scripts/build_real_multiclass_5.py --negatives-only

  # Full build when domain files are ready
  python scripts/build_real_multiclass_5.py \\
      --positives-dir data/domain_positives

  python scripts/build_real_multiclass_5.py --help
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POSITIVES_DIR = ROOT / "data" / "domain_positives"
DEFAULT_AG_NEWS = ROOT / "data" / "ag_news_dataset.csv"
DEFAULT_OUTPUT = ROOT / "data" / "real_multiclass_5.csv"

RANDOM_STATE = 42
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}

AG_INDEX_TO_TOPIC = {
    1: "world",
    2: "sports",
    3: "business",
    4: "sci_tech",
}

PARAGRAPH_RE = re.compile(r"\n\s*\n+")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\\", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_text_from_file(path: Path) -> str:
    ext = path.suffix.lower()
    raw = path.read_bytes()
    if ext in {".txt", ".md"}:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        return text.strip()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError(
                "PDF support requires pypdf. Install with: pip install pypdf"
            ) from exc
        reader = PdfReader(io.BytesIO(raw))
        parts = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(p for p in parts if p.strip()).strip()
    raise ValueError(f"Unsupported extension: {ext}")


def paragraph_chunks(text: str, min_words: int) -> list[str]:
    """Split on blank lines; keep chunks with at least min_words."""
    paragraphs = [p.strip() for p in PARAGRAPH_RE.split(text) if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []
    chunks: list[str] = []
    for para in paragraphs:
        words = para.split()
        if len(words) >= min_words:
            chunks.append(normalize_whitespace(para))
    return chunks


def load_domain_rows(
    positives_dir: Path,
    min_chunk_words: int,
) -> pd.DataFrame:
    if not positives_dir.is_dir():
        raise FileNotFoundError(f"Positives directory not found: {positives_dir}")

    files = sorted(
        p
        for p in positives_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    )
    if not files:
        raise FileNotFoundError(f"No .txt/.md/.pdf files under {positives_dir}")

    rows: list[dict[str, str]] = []
    for path in files:
        rel = path.relative_to(positives_dir)
        base_id = re.sub(r"[^a-zA-Z0-9]+", "_", str(rel.with_suffix(""))).strip("_")
        text = extract_text_from_file(path)
        chunks = paragraph_chunks(text, min_chunk_words)
        if not chunks:
            print(f"  skip (no chunk >= {min_chunk_words} words): {rel}", file=sys.stderr)
            continue
        if len(chunks) == 1:
            rows.append(
                {
                    "doc_id": f"domain_{base_id}",
                    "text": chunks[0],
                    "topic": "domain",
                }
            )
        else:
            for i, chunk in enumerate(chunks):
                rows.append(
                    {
                        "doc_id": f"domain_{base_id}_p{i:03d}",
                        "text": chunk,
                        "topic": "domain",
                    }
                )

    if not rows:
        raise ValueError(f"No usable domain chunks from {positives_dir}")

    return pd.DataFrame(rows)


def load_ag_news_rows(
    ag_news_path: Path,
    min_desc_chars: int,
    max_per_class: int | None,
) -> pd.DataFrame:
    if not ag_news_path.is_file():
        raise FileNotFoundError(f"AG News CSV not found: {ag_news_path}")

    raw = pd.read_csv(ag_news_path)
    required = {"Class Index", "Title", "Description"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"AG News CSV missing columns: {sorted(missing)}")

    rows: list[dict[str, str]] = []
    skipped_short = 0
    skipped_bad_class = 0

    for i, row in raw.iterrows():
        class_idx = int(row["Class Index"])
        topic = AG_INDEX_TO_TOPIC.get(class_idx)
        if topic is None:
            skipped_bad_class += 1
            continue

        title = normalize_whitespace(str(row["Title"]))
        desc = normalize_whitespace(str(row["Description"]))
        if len(desc) < min_desc_chars:
            skipped_short += 1
            continue

        text = normalize_whitespace(f"{title} {desc}")
        rows.append(
            {
                "doc_id": f"ag_{i:05d}",
                "text": text,
                "topic": topic,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No AG News rows left after filtering.")

    if max_per_class is not None:
        parts = []
        for topic in sorted(df["topic"].unique()):
            part = df.loc[df["topic"] == topic]
            if len(part) > max_per_class:
                part = part.sample(n=max_per_class, random_state=RANDOM_STATE)
            parts.append(part)
        df = pd.concat(parts, ignore_index=True)

    print(
        f"  AG News: kept={len(df)}  skipped_short_desc={skipped_short}  "
        f"skipped_bad_class={skipped_bad_class}",
        file=sys.stderr,
    )
    return df


def assign_grouped_splits(
    df: pd.DataFrame,
    test_frac: float,
    random_state: int,
) -> pd.DataFrame:
    """Train/test split by doc_id; stratify on topic at document level."""
    groups = df.groupby("doc_id", as_index=False).agg(topic=("topic", "first"))
    train_ids, test_ids = train_test_split(
        groups["doc_id"],
        test_size=test_frac,
        random_state=random_state,
        stratify=groups["topic"],
    )
    test_set = set(test_ids)
    out = df.copy()
    out["split"] = out["doc_id"].apply(lambda d: "test" if d in test_set else "train")
    return out


def print_summary(df: pd.DataFrame, label: str) -> None:
    print(f"\n{label}: {len(df)} rows", file=sys.stderr)
    print("  by topic:", file=sys.stderr)
    for topic, n in df["topic"].value_counts().sort_index().items():
        print(f"    {topic:12s} {n}", file=sys.stderr)
    if "split" in df.columns:
        print("  by split:", file=sys.stderr)
        ct = pd.crosstab(df["topic"], df["split"])
        print(ct.to_string(), file=sys.stderr)
    lens = df["text"].str.len()
    print(
        f"  text length (chars): median={lens.median():.0f}  "
        f"mean={lens.mean():.1f}  min={lens.min()}  max={lens.max()}",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--positives-dir",
        type=Path,
        default=DEFAULT_POSITIVES_DIR,
        help=f"Directory of domain .txt/.md/.pdf files (default: {DEFAULT_POSITIVES_DIR})",
    )
    parser.add_argument(
        "--ag-news",
        type=Path,
        default=DEFAULT_AG_NEWS,
        help=f"AG News CSV path (default: {DEFAULT_AG_NEWS})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--negatives-only",
        action="store_true",
        help="Process AG News only (skip domain positives)",
    )
    parser.add_argument(
        "--min-desc-chars",
        type=int,
        default=80,
        help="Drop AG News rows with Description shorter than this (default: 80)",
    )
    parser.add_argument(
        "--min-chunk-words",
        type=int,
        default=50,
        help="Minimum words per domain paragraph chunk (default: 50)",
    )
    parser.add_argument(
        "--test-frac",
        type=float,
        default=0.2,
        help="Holdout fraction by doc_id (default: 0.2)",
    )
    parser.add_argument(
        "--max-neg-per-class",
        type=int,
        default=None,
        help="Optional cap on AG News rows per class (for balanced partial exports)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=RANDOM_STATE,
        help=f"Random seed (default: {RANDOM_STATE})",
    )
    args = parser.parse_args()

    parts: list[pd.DataFrame] = []

    if not args.negatives_only:
        if args.positives_dir.is_dir() and any(args.positives_dir.rglob("*")):
            print(f"Loading domain files from {args.positives_dir}...", file=sys.stderr)
            try:
                domain_df = load_domain_rows(args.positives_dir, args.min_chunk_words)
                parts.append(domain_df)
                print(f"  domain chunks: {len(domain_df)}", file=sys.stderr)
            except (FileNotFoundError, ValueError) as exc:
                print(f"  domain skipped: {exc}", file=sys.stderr)
        else:
            print(
                f"  domain skipped: {args.positives_dir} missing or empty "
                f"(use --negatives-only to silence)",
                file=sys.stderr,
            )

    print(f"Loading AG News from {args.ag_news}...", file=sys.stderr)
    ag_df = load_ag_news_rows(args.ag_news, args.min_desc_chars, args.max_neg_per_class)
    parts.append(ag_df)

    df = pd.concat(parts, ignore_index=True)
    df = assign_grouped_splits(df, args.test_frac, args.random_state)
    df = df.loc[:, ["doc_id", "text", "topic", "split"]]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    print_summary(df, f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

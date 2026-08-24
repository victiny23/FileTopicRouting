#!/usr/bin/env python3
"""Chunk domain positive .txt files into training-ready rows.

Output: data/domain_chunks.csv with columns doc_id, text, topic (always domain).

Usage (from repo root):

  python scripts/chunk_domain_positives.py
  python scripts/chunk_domain_positives.py --input-dir data/domain_positives
  python scripts/chunk_domain_positives.py --no-cap
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.text_chunking import (
    ChunkConfig,
    apply_proportional_cap,
    chunk_document,
    file_doc_id,
    word_count,
)

DEFAULT_INPUT_DIR = ROOT / "data" / "domain_positives"
DEFAULT_OUTPUT = ROOT / "data" / "domain_chunks.csv"


def collect_txt_files(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    files = sorted(input_dir.rglob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt files under {input_dir}")
    return files


def chunk_file(path: Path, input_dir: Path, config: ChunkConfig) -> list[dict[str, str]]:
    rel = path.relative_to(input_dir)
    base_id = file_doc_id(str(rel.with_suffix("")))
    text = path.read_text(encoding="utf-8", errors="replace")
    chunks = chunk_document(text, doc_name=str(rel), config=config)

    rows: list[dict[str, str]] = []
    if len(chunks) == 1:
        rows.append(
            {
                "doc_id": base_id,
                "text": chunks[0]["text"],
                "topic": "domain",
            }
        )
    else:
        for i, chunk in enumerate(chunks):
            rows.append(
                {
                    "doc_id": f"{base_id}_p{i:03d}",
                    "text": chunk["text"],
                    "topic": "domain",
                }
            )
    return rows


def print_summary(df: pd.DataFrame, label: str) -> None:
    print(f"\n{label}: {len(df)} rows", file=sys.stderr)
    wc = df["text"].map(word_count)
    print(
        f"  words/chunk: median={wc.median():.0f} mean={wc.mean():.1f} "
        f"min={wc.min()} max={wc.max()}",
        file=sys.stderr,
    )
    per_file = df["doc_id"].str.replace(r"_p\d+$", "", regex=True).nunique()
    print(f"  source files: {per_file}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Folder of domain .txt files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--min-words", type=int, default=150)
    parser.add_argument("--max-words", type=int, default=500)
    parser.add_argument("--overlap-words", type=int, default=50)
    parser.add_argument("--whole-file-max-words", type=int, default=500)
    parser.add_argument("--stub-min-words", type=int, default=30)
    parser.add_argument(
        "--max-file-fraction",
        type=float,
        default=0.10,
        help="Cap each source file to this fraction of total chunks (0 disables)",
    )
    parser.add_argument(
        "--no-cap",
        action="store_true",
        help="Disable proportional per-file cap",
    )
    args = parser.parse_args()

    config = ChunkConfig(
        min_words=args.min_words,
        max_words=args.max_words,
        overlap_words=args.overlap_words,
        whole_file_max_words=args.whole_file_max_words,
        stub_min_words=args.stub_min_words,
        max_file_fraction=0.0 if args.no_cap else args.max_file_fraction,
    )

    files = collect_txt_files(args.input_dir)
    print(f"Chunking {len(files)} files from {args.input_dir}...", file=sys.stderr)

    rows: list[dict[str, str]] = []
    skipped = 0
    for path in files:
        file_rows = chunk_file(path, args.input_dir, config)
        if not file_rows:
            skipped += 1
            print(f"  skip (stub/empty): {path.name}", file=sys.stderr)
        rows.extend(file_rows)

    if not rows:
        raise ValueError("No chunks produced — check input files and thresholds.")

    before = len(rows)
    if config.max_file_fraction > 0:
        rows = apply_proportional_cap(rows, max_fraction=config.max_file_fraction)
        print(
            f"  proportional cap ({config.max_file_fraction:.0%}): "
            f"{before} -> {len(rows)} rows",
            file=sys.stderr,
        )

    df = pd.DataFrame(rows)[["doc_id", "text", "topic"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print_summary(df, f"Wrote {args.output}")
    if skipped:
        print(f"  skipped files: {skipped}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

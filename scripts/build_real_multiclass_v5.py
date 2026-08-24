#!/usr/bin/env python3
"""Combine domain chunks + new_articles_dataset into real_multiclass_v5.csv.

Output schema (no split column — split in notebook):
  doc_id, text, topic

Topics: domain | business | education | entertainment | sports | technology

Usage (from repo root):

  python scripts/build_real_multiclass_v5.py
  python scripts/build_real_multiclass_v5.py --domain-chunks data/domain_chunks.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOMAIN_CHUNKS = ROOT / "data" / "domain_chunks.csv"
DEFAULT_NEWS_DIR = ROOT / "data" / "new_articles_dataset"
DEFAULT_OUTPUT = ROOT / "data" / "real_multiclass_v5.csv"
DEFAULT_MANIFEST = ROOT / "data" / "real_multiclass_v5_manifest.json"

NEWS_TOPICS = frozenset({"business", "education", "entertainment", "sports", "technology"})
WORD_RE = re.compile(r"\S+")


def word_count(text: str) -> int:
    return len(WORD_RE.findall(str(text)))


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def load_domain_chunks(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Domain chunks not found: {path}\n"
            "Run: python scripts/chunk_domain_positives.py --input-dir data/domain_positives"
        )
    df = pd.read_csv(path)
    required = {"doc_id", "text", "topic"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"domain_chunks.csv missing columns: {sorted(missing)}")
    df = df.dropna(subset=["doc_id", "text", "topic"]).copy()
    df["text"] = df["text"].map(normalize_whitespace)
    df = df.loc[df["text"].str.len() > 0]
    if (df["topic"] != "domain").any():
        raise ValueError("domain_chunks.csv must have topic=domain for all rows")
    return df[["doc_id", "text", "topic"]]


def load_news(news_dir: Path, stub_min_words: int) -> pd.DataFrame:
    if not news_dir.is_dir():
        raise FileNotFoundError(f"News directory not found: {news_dir}")

    csv_files = sorted(news_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files in {news_dir}")

    frames: list[pd.DataFrame] = []
    for path in csv_files:
        raw = pd.read_csv(path)
        required = {"headlines", "content", "url", "category"}
        missing = required - set(raw.columns)
        if missing:
            raise ValueError(f"{path.name} missing columns: {sorted(missing)}")
        frames.append(raw)

    news = pd.concat(frames, ignore_index=True)
    news["topic"] = news["category"].astype(str).str.strip().str.lower()
    bad = set(news["topic"].unique()) - NEWS_TOPICS
    if bad:
        raise ValueError(f"Unexpected news categories: {sorted(bad)}")

    news["text"] = (
        news["headlines"].astype(str).map(normalize_whitespace)
        + "\n\n"
        + news["content"].astype(str).map(normalize_whitespace)
    ).map(normalize_whitespace)

    before = len(news)
    news["wc"] = news["text"].map(word_count)
    news = news.loc[news["wc"] >= stub_min_words].copy()
    dropped_stub = before - len(news)

    before_dedup = len(news)
    news = news.drop_duplicates(subset=["url"], keep="first")
    dropped_dup = before_dedup - len(news)

    def make_doc_id(url: str) -> str:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        return f"news_{digest}"

    news["doc_id"] = news["url"].map(make_doc_id)
    print(
        f"  news: kept={len(news)} dropped_stub={dropped_stub} dropped_dup_url={dropped_dup}",
        file=sys.stderr,
    )
    return news[["doc_id", "text", "topic"]]


def print_summary(df: pd.DataFrame, label: str) -> None:
    print(f"\n{label}: {len(df)} rows", file=sys.stderr)
    print("  by topic:", file=sys.stderr)
    for topic, n in df["topic"].value_counts().sort_index().items():
        print(f"    {topic:14s} {n}", file=sys.stderr)
    wc = df["text"].map(word_count)
    print(
        f"  words/text: median={wc.median():.0f} mean={wc.mean():.1f} "
        f"min={wc.min()} max={wc.max()}",
        file=sys.stderr,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain-chunks",
        type=Path,
        default=DEFAULT_DOMAIN_CHUNKS,
        help=f"Domain chunk CSV (default: {DEFAULT_DOMAIN_CHUNKS})",
    )
    parser.add_argument(
        "--news-dir",
        type=Path,
        default=DEFAULT_NEWS_DIR,
        help=f"Directory with 5 news CSVs (default: {DEFAULT_NEWS_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Combined dataset CSV (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Build manifest JSON (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--domain-only",
        action="store_true",
        help="Build without news rows (domain chunks only)",
    )
    parser.add_argument(
        "--news-only",
        action="store_true",
        help="Build without domain rows (news only)",
    )
    parser.add_argument(
        "--stub-min-words",
        type=int,
        default=30,
        help="Drop news rows with fewer words than this (default: 30)",
    )
    args = parser.parse_args()

    parts: list[pd.DataFrame] = []

    if not args.news_only:
        print(f"Loading domain chunks from {args.domain_chunks}...", file=sys.stderr)
        parts.append(load_domain_chunks(args.domain_chunks))

    if not args.domain_only:
        print(f"Loading news from {args.news_dir}...", file=sys.stderr)
        parts.append(load_news(args.news_dir, args.stub_min_words))

    df = pd.concat(parts, ignore_index=True)[["doc_id", "text", "topic"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    manifest = {
        "output": str(args.output.relative_to(ROOT)),
        "rows": int(len(df)),
        "topics": df["topic"].value_counts().sort_index().to_dict(),
        "domain_chunks": str(args.domain_chunks.relative_to(ROOT)),
        "news_dir": str(args.news_dir.relative_to(ROOT)),
        "stub_min_words": args.stub_min_words,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print_summary(df, f"Wrote {args.output}")
    print(f"Manifest: {args.manifest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

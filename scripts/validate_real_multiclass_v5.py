#!/usr/bin/env python3
"""Validate real_multiclass_v5.csv schema and basic quality checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "real_multiclass_v5.csv"

EXPECTED_TOPICS = frozenset(
    {"domain", "business", "education", "entertainment", "sports", "technology"}
)
REQUIRED_COLUMNS = ("doc_id", "text", "topic")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    args = parser.parse_args()

    if not args.data.is_file():
        print(f"FAIL: file not found: {args.data}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.data)
    errors: list[str] = []

    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        errors.append(f"missing columns: {sorted(missing_cols)}")

    forbidden = set(df.columns) - set(REQUIRED_COLUMNS)
    if forbidden:
        errors.append(f"unexpected columns (split should be in notebook): {sorted(forbidden)}")

    if df.empty:
        errors.append("dataset is empty")

    if "topic" in df.columns:
        topics = set(df["topic"].dropna().unique())
        unknown = topics - EXPECTED_TOPICS
        if unknown:
            errors.append(f"unknown topics: {sorted(unknown)}")

    if "doc_id" in df.columns:
        if df["doc_id"].isna().any():
            errors.append("null doc_id values")
        if df["doc_id"].duplicated().any():
            n = int(df["doc_id"].duplicated().sum())
            errors.append(f"duplicate doc_id values: {n}")

    if "text" in df.columns:
        empty = df["text"].astype(str).str.strip().eq("")
        if empty.any():
            errors.append(f"empty text rows: {int(empty.sum())}")

    if errors:
        print("FAIL:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK: {args.data} ({len(df)} rows)")
    print(df["topic"].value_counts().sort_index().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

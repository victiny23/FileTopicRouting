#!/usr/bin/env python3
"""Find articles that auto-route to Needs review (max-proba < tau).

Usage (from repo root, with backend venv or sklearn 1.8.0):

  backend/.venv/bin/python scripts/find_needs_review_examples.py
  backend/.venv/bin/python scripts/find_needs_review_examples.py --tau 0.26 --n 5
  backend/.venv/bin/python scripts/find_needs_review_examples.py --split test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data" / "synthetic_topic_articles_v4.csv"
DEFAULT_MODEL = ROOT / "data" / "models" / "ml_multi_v1.joblib"
DEFAULT_TAU = 0.26
RANDOM_STATE = 42


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--tau", type=float, default=DEFAULT_TAU)
    parser.add_argument("--n", type=int, default=5, help="Max examples to print")
    parser.add_argument(
        "--split",
        choices=["all", "train", "test"],
        default="all",
        help="Which rows to scan (train/test use the same 80/20 split as the notebooks)",
    )
    parser.add_argument(
        "--write-txt",
        type=Path,
        default=None,
        help="Optional path to write the first matching article_text as a .txt file",
    )
    args = parser.parse_args()

    if not args.model.is_file():
        print(f"Model not found: {args.model}", file=sys.stderr)
        return 1
    if not args.data.is_file():
        print(f"Data not found: {args.data}", file=sys.stderr)
        return 1

    df = pd.read_csv(args.data)
    if args.split != "all":
        _, idx_test = train_test_split(
            df.index,
            test_size=0.2,
            random_state=RANDOM_STATE,
            stratify=df["topic"],
        )
        test_ids = set(idx_test)
        df = df.loc[[i for i in df.index if (i in test_ids) == (args.split == "test")]]

    model = joblib.load(args.model)
    classes = list(model.named_steps["clf"].classes_)
    texts = df["article_text"].tolist()
    proba = model.predict_proba(texts)
    pred_idx = proba.argmax(axis=1)
    conf = proba.max(axis=1)
    pred = [classes[i] for i in pred_idx]

    hits = df.copy()
    hits["pred_topic"] = pred
    hits["max_proba"] = conf
    hits = hits.loc[hits["max_proba"] < args.tau].sort_values("max_proba")

    print(f"scanned={len(df)}  tau={args.tau:.3f}  needs_review={len(hits)}  split={args.split}")
    if hits.empty:
        print("No Needs-review examples at this tau. Try raising --tau (e.g. 0.40).")
        return 0

    show = hits.head(args.n)
    for _, row in show.iterrows():
        print("-" * 72)
        print(
            f"{row['article_id']}  true={row['topic']}  pred={row['pred_topic']}  "
            f"max_proba={row['max_proba']:.4f}"
        )
        print(f"title: {row['title']}")
        snippet = " ".join(str(row["article_text"]).split())
        print(f"text:  {snippet[:280]}{'…' if len(snippet) > 280 else ''}")

    if args.write_txt is not None:
        first = hits.iloc[0]
        args.write_txt.parent.mkdir(parents=True, exist_ok=True)
        args.write_txt.write_text(
            f"{first['title']}\n\n{first['article_text']}\n",
            encoding="utf-8",
        )
        print("-" * 72)
        print(
            f"wrote {args.write_txt}  "
            f"({first['article_id']}, max_proba={first['max_proba']:.4f})"
        )
        print("Upload that file in the demo (or paste the text) to land in Needs review.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

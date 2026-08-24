# Real dataset v5 — locked plan

**Status:** Locked (approved 2026-08-24)  
**Goal:** Move from synthetic-only ML to a real-data corpus for domain routing vs news.

---

## 1. Background

### Why real data now

Synthetic v4 proved the pipeline (TF-IDF + LR, grouped evaluation, explainability). The next step is training on **real domain documents** plus **real news articles** so metrics reflect production-like text.

### What we rejected

| Source | Reason rejected |
|--------|-----------------|
| **AG News** (`ag_news_dataset.csv`) | Snippet-only (title + short description), not full articles |
| **Split column in CSV** | Leakage risk; split belongs in notebooks with grouped holdout |
| **Train downsampling of news** | After chunking, domain ≈ 2K rows vs ~2K/class news — already balanced for 6-class |
| **Mixing synthetic v4 into training** | Out of scope for v5; real data only |

---

## 2. Data sources

### Domain positives (~90 files)

- Location: `data/domain_positives/*.txt`
- User pre-converts pdf/md/pptx/docx → `.txt` (not in build scope)
- EDA (90 files): ~4M words total; median **22.7K words/file**; highly right-skewed; top ~45 files ≈ 90% of words; 3 tiny files <500 words

### News negatives (`data/new_articles_dataset/`)

| File | Rows | Topic label |
|------|------|-------------|
| `business_data.csv` | 2,000 | `business` |
| `education_data.csv` | 2,000 | `education` |
| `entertainment_data.csv` | 2,000 | `entertainment` |
| `sports_data.csv` | 2,000 | `sports` |
| `technology_data.csv` | 2,000 | `technology` |

**Total:** ~10,000 full articles (headline + body).

### Negative length EDA (justifies chunk caps)

News `text = headlines + "\n\n" + content`:

| Stat | Words |
|------|------:|
| Median | 158 |
| p90 | 498 |
| p95 | 674 |
| Max | ~2,880 |

With `min_words=150`, **~54%** of news rows are ≥ that length. TF-IDF L2 norm reduces length bias; `max_words=500` is a practical cap aligned with p90, not a strict ML requirement.

---

## 3. Label design — 6-class multiclass

| `topic` | Source |
|---------|--------|
| `domain` | Chunked domain `.txt` files |
| `business` | `business_data.csv` |
| `education` | `education_data.csv` |
| `entertainment` | `entertainment_data.csv` |
| `sports` | `sports_data.csv` |
| `technology` | `technology_data.csv` |

**Binary baseline (separate notebook):** `domain=1`, all news topics `rest=0`.

No downsampling for 6-class training. For binary, use `class_weight='balanced'` rather than downsampling all news.

---

## 4. Chunking policy (domain positives)

### Locked parameters

| Parameter | Value | Role |
|-----------|------:|------|
| `min_words` | **150** | Merge floor — don't drop small structural fragments |
| `max_words` | **500** | Ceiling — align with news p90 |
| `overlap_words` | **50** | Only when sub-splitting sections > max |
| `whole_file_max_words` | **500** | File ≤500 words → single row |
| `stub_min_words` | **30** | Drop empty/stub rows only |
| `max_file_fraction` | **0.10** | Per-file cap if one file dominates (disable with `--no-cap`) |

### Algorithm

```
1. Structure-first split (markdown headers, numbered sections, ALL CAPS lines, paragraphs)
2. Merge adjacent units until >= min_words (do not drop small fragments)
3. Sub-split with overlap only if merged section > max_words
4. Prepend context: [doc: filename | section: …]
5. Apply proportional per-file cap (optional)
```

### Input / output

- **Input:** `.txt` only
- **Output:** `data/domain_chunks.csv` with columns `doc_id, text, topic` (`topic=domain`)

---

## 5. News processing

| Step | Rule |
|------|------|
| Text field | `headlines + "\n\n" + content` (skip standalone `description`) |
| Dedupe | By `url` |
| Stub filter | Drop rows with **< 30 words** total |
| `doc_id` | `news_<hash(url)>` or equivalent stable id |
| Downsampling | **None** |

---

## 6. Combined dataset schema

```text
doc_id, text, topic
```

| Column | Description |
|--------|-------------|
| `doc_id` | Groups rows for leakage-safe splits (`domain_*`, `news_*`) |
| `text` | Model input |
| `topic` | One of 6 classes above |

**No `split` column.** Train/test split and GroupKFold happen **in notebooks only**, grouped by `doc_id`.

### Outputs

| Path | Description |
|------|-------------|
| `data/domain_chunks.csv` | Chunked domain rows |
| `data/real_multiclass_v5.csv` | Combined corpus |
| `data/real_multiclass_v5_manifest.json` | Build metadata |

---

## 7. Build workflow

```bash
# 1. Place ~90 domain .txt files
#    data/domain_positives/

python scripts/chunk_domain_positives.py --input-dir data/domain_positives

python scripts/build_real_multiclass_v5.py

python scripts/validate_real_multiclass_v5.py
```

Partial build (news only, before domain files are ready):

```bash
python scripts/build_real_multiclass_v5.py --news-only
```

---

## 8. Deliverables

| # | Artifact | Purpose |
|---|----------|---------|
| 1 | `ml/text_chunking.py` | Shared chunk logic (`ChunkConfig`, merge, cap) |
| 2 | `scripts/chunk_domain_positives.py` | CLI: domain `.txt` → `domain_chunks.csv` |
| 3 | `scripts/build_real_multiclass_v5.py` | Combine domain + news → `real_multiclass_v5.csv` |
| 4 | `scripts/validate_real_multiclass_v5.py` | Schema and quality checks |
| 5 | `doc/real_v5_dataset.md` | Operational reference |
| 6 | `notebooks/ml_multi_v5.ipynb` | 6-class TF-IDF + LR |
| 7 | `notebooks/ml_binary_domain_v5.ipynb` | Binary domain vs rest baseline |

---

## 9. Modeling plan

### `notebooks/ml_multi_v5.ipynb`

- Load `data/real_multiclass_v5.csv`
- **Grouped holdout by `doc_id`** (80/20, stratified on topic at doc level)
- TF-IDF + multinomial LR, `GridSearchCV` with `f1_macro`, `class_weight='balanced'`
- Holdout: accuracy, macro F1, confusion matrix, domain precision/recall
- Signed LR coefficient explainability
- Save `data/models/ml_multi_v5.joblib`
- **Layer B abstain deferred** to a later version

### `notebooks/ml_binary_domain_v5.ipynb`

- Same data; label `domain` vs `rest`
- Grouped split stratified on binary label at doc level
- Dummy baselines + tuned TF-IDF + LR
- Save `data/models/ml_binary_domain_v5.joblib`

---

## 10. Out of scope (v5)

- Backend / demo wiring with the new model
- Mixing synthetic v4 into training
- pdf/md/pptx/docx ingestion (user converts to `.txt` first)
- Layer B confidence abstain in first modeling pass
- Pretrained embeddings / fine-tuned encoders (future work)

---

## 11. Expected scale (after domain files added)

| Component | Approximate rows |
|-----------|-----------------|
| Domain chunks | ~1,000–2,500 (depends on cap + file sizes) |
| News (5 classes) | ~10,000 |
| **Total** | ~11,000–12,500 |

Per-class balance for 6-class: domain ≈ 0.5–1.2× each news class — no train downsampling needed.

---

## 12. Implementation status

| Item | Status |
|------|--------|
| `ml/text_chunking.py` | Done |
| `scripts/chunk_domain_positives.py` | Done |
| `scripts/build_real_multiclass_v5.py` | Done |
| `scripts/validate_real_multiclass_v5.py` | Done |
| `doc/real_v5_dataset.md` | Done |
| `notebooks/ml_multi_v5.ipynb` | Done |
| `notebooks/ml_binary_domain_v5.ipynb` | Done |
| News-only build + validate | Done (9,989 rows) |
| Full build with domain files | **Pending** — user adds ~90 `.txt` to `data/domain_positives/` |
| Model training / saved artifacts | **Pending** — run notebooks after full build |

---

## 13. Key decisions log

| Date | Decision |
|------|----------|
| 2026-08-23 | Reject AG News; use `new_articles_dataset` (full articles) |
| 2026-08-23 | 6-class labels; no split in CSV |
| 2026-08-23 | Structure-first chunking with merge floor (not fixed 200-word targets) |
| 2026-08-23 | No train downsampling for 6-class |
| 2026-08-24 | Lock `min_words=150`, `max_words=500` |
| 2026-08-24 | Rename v6 → v5; remove AG News artifacts |

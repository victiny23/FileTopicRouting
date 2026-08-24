Place domain positive `.txt` files here (~90 files).

Then run:

```bash
python scripts/chunk_domain_positives.py --input-dir data/domain_positives
python scripts/build_real_multiclass_v5.py
```

See `doc/real_v5_dataset.md` for chunking parameters (min=150, max=500 words).

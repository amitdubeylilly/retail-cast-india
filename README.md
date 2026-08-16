# RetailCast India — 28-day Demand Forecast

Forecast 28 daily values (`d_1914`…`d_1941`) for 60 product-store series.

## Reproduce

```bash
pip install -r requirements.txt
python src/forecast.py --data data --out submission.csv
python validate_format.py --submission submission.csv --sample data/sample_submission.csv
```

`submission.csv` (60 rows, `id`,`F1`…`F28`) is regenerated deterministically — no randomness, no saved model.

## Method (short)

Per series: `forecast = recent_level × day-of-week multiplier × festival uplift`, clipped at 0.

- **recent_level** = mean of the last 42 days (28 for the `KA_3` store, which is in a genuine store-wide decline).
- **day-of-week multiplier** from the last 180 days (captures the strong weekend lift).
- **festival uplift** = 1.15× on days with a calendar event (horizon has Ram Navami and Eid al-Fitr).

## What the audit found (see `src/audit.py`)

| Finding | Evidence | Action |
|---|---|---|
| `market_signal` is target leakage | same-day per-series corr 0.92, collapses to ~0.37 when shifted ±1; exactly 0 on 100% of zero-sales days; ≈ units×10×noise; ends at d_1913 (no horizon) | **excluded** |
| `vendor_signal` is honest but weak | present through d_1941; per-series backtest WAPE 1.04 vs trailing-mean 0.82 | **not used** as forecast |
| `KA_3` store-wide decline | all 6 KA_3 series at 0.25–0.49 of prior-year over last ~100 days; same products elsewhere ~1.0 | **short recent window** for KA_3 |
| price carries no signal | median within-series corr(units, price) ≈ −0.03 | **price excluded** |
| Diwali spikes look extreme but are real | biggest spikes land on Diwali / festival dates | **left uncorrected** |

Run `python src/audit.py --data data` to regenerate all of the above.

## Backtest (honest, held-out)

Three rolling 28-day holdouts, each trained only on data before its cut:

| window | mean RMSSE | WAPE |
|---|---|---|
| d_1830–1857 | 0.891 | 0.506 |
| d_1858–1885 | 0.819 | 0.398 |
| d_1886–1913 | 0.829 | 0.366 |

Means ≈ 0.85 / 0.42. The d_1830–1857 window (Jan–Feb, post-festival) is the hardest, which is why three windows are reported rather than the rosier pair. Expected horizon **mean RMSSE ≈ 0.83–0.90**, WAPE ≈ 0.38–0.45.

## Reference files

- `olympics.json` — the organizer's machine-readable challenge manifest (metric, horizon, required artifacts).
- `sample_submission.csv` — the required output format (60 rows, `id` + `F1`…`F28`).
- `validate_format.py` — pre-submission **format** check only; it does not score accuracy.

## Submission artifacts (per the challenge brief)

1. This repo — reproducible code that regenerates `submission.csv`.
2. `chat_export.md` — the Claude chat export of the Phase 1–2 investigation and planning conversation.
3. `approach_summary.md` — the Technical Decision Log (max 1,500 words) answering the brief's seven questions.

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
| `market_signal` is target leakage | same-day per-series corr 0.92, collapses to ~0.33 when shifted ±1; exactly 0 on 100% of zero-sales days; ≈ units×10×noise; ends at d_1913 (no horizon) | **excluded** |
| `vendor_signal` is honest but weak | present through d_1941; per-series backtest WAPE 1.04 vs trailing-mean 0.82 | **not used** as forecast |
| `KA_3` store-wide decline | all 6 KA_3 series at 0.25–0.49 of prior-year over last ~100 days; same products elsewhere ~1.0 | **short recent window** for KA_3 |
| price carries no signal | median within-series corr(units, price) ≈ −0.03 | **price excluded** |
| Diwali spikes look extreme but are real | biggest spikes land on Diwali / festival dates | **left uncorrected** |

Run `python src/audit.py --data data` to regenerate all of the above.

## Backtest (honest, held-out)

Two rolling 28-day holdouts (predict d_1858–1885 and d_1886–1913 from earlier data only):

| window | mean RMSSE | WAPE |
|---|---|---|
| d_1886–1913 | 0.828 | 0.366 |
| d_1858–1885 | 0.819 | 0.398 |

Expected horizon **mean RMSSE ≈ 0.83–0.90**, WAPE ≈ 0.38–0.43.

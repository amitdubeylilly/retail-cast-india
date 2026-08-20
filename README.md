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

Per series: `forecast = recent_level × day-of-week multiplier × festival uplift × [promo uplift]`, clipped at 0.

- **recent_level** = mean of the last 42 days (28 for `TN_2` post-break regime; 56 for `KA_3` recovering dip), with stockout-censored zero windows (≥7 consecutive zeros) masked out.
- **day-of-week multiplier** from the last 180 days (captures the strong weekend lift), also stockout-masked.
- **festival uplift** = 1.15× on days with a calendar event (horizon has Ram Navami and Eid al-Fitr).
- **April haircut** = 0.90× on `GROCERY_3_ATTA` only, on April horizon days only.
- **Promo uplift** = 1.20× on `ELECTRONICS_1_CHARGER_KA_1` for horizon days 1914–1920 (promo week 2314, price drops 28% from 8.33→5.95; recent promos measured 1.17–1.80× uplift vs surrounding weeks).

## What the audit found (see `src/audit.py`)

| Finding | Evidence | Action |
|---|---|---|
| `market_signal` is target leakage | same-day per-series corr 0.92, collapses to ~0.37 when shifted ±1; exactly 0 on 100% of zero-sales days; ≈ units×10×noise; ends at d_1913 (no horizon) | **excluded** |
| `vendor_signal` is honest but weak | present through d_1941; per-series backtest WAPE 1.04 vs trailing-mean 0.82 | **not used** as forecast |
| `TN_2` permanent post-break regime | multiple series declined (CABLE 0.20×, AGARBATTI 0.35×, PICKLE 0.65×) and plateaued at new level | **28-day regime anchor** |
| `KA_3` transient/recovering dip | all 6 series declining (DETERGENT 0.28×, CHARGER 0.27×) but still actively falling — no plateau | **56-day window** (allows recovery) |
| Stockout-censored zero windows | ATTA: 7–173 consecutive-zero days across all stores; supply-driven, not demand | **masked** from level/DOW |
| Phantom pickle price error | MH_2 shows 1.20 among 3.94–4.37 range | **ignored** (data error) |
| KA_1 charger promo elasticity | price 5.95 (−28%), recent promos show 1.17–1.80× uplift; promo week in horizon | **1.20× uplift** on d_1914–1920 |
| price carries no signal (globally) | median within-series corr(units, price) ≈ −0.03 | **price excluded** except KA_1 charger |
| Diwali spikes look extreme but are real | biggest spikes land on Diwali / festival dates | **left uncorrected** |
| `GROCERY_3_ATTA` dips every April | Apr/Feb-Mar ratio 0.95/0.90/0.80/0.95 across 2019–2022, all 4 years below 1.0 | **0.90× haircut**, ATTA only |

Run `python src/audit.py --data data` to regenerate all of the above.

## Backtest (honest, held-out)

Three rolling 28-day holdouts, each trained only on data before its cut:

| window | mean RMSSE | WAPE |
|---|---|---|
| d_1830–1857 | 0.891 | 0.506 |
| d_1858–1885 | 0.819 | 0.398 |
| d_1886–1913 | 0.829 | 0.365 |

Means ≈ 0.85 / 0.42. The d_1830–1857 window (Jan–Feb, post-festival) is the hardest, which is why three windows are reported rather than the rosier pair. None of these windows land in April — the true horizon is entirely April 2023 — so the ATTA haircut above is separately validated against 4 historical Aprils (leakage-safe: each year's correction ratio is computed only from years strictly before it):

| test April | baseline mean RMSSE / WAPE | with ATTA haircut |
|---|---|---|
| 2019 | 2.570 / 0.354 | 2.570 / 0.354 (no prior year to derive a ratio from) |
| 2020 | 0.739 / 0.367 | 0.736 / 0.359 |
| 2021 | 0.614 / 0.542 | 0.601 / 0.495 |
| 2022 | 0.984 / 0.488 | 0.972 / 0.459 |

The haircut improves both metrics in every testable year. Expected horizon **mean RMSSE ≈ 0.83–0.90**, WAPE ≈ 0.38–0.45.

## Reference files

- `olympics.json` — the organizer's machine-readable challenge manifest (metric, horizon, required artifacts).
- `sample_submission.csv` — the required output format (60 rows, `id` + `F1`…`F28`).
- `validate_format.py` — pre-submission **format** check only; it does not score accuracy.

## Submission artifacts (per the challenge brief)

1. This repo — reproducible code that regenerates `submission.csv`.
2. `chat_export.md` — the Claude chat export of the Phase 1–2 investigation and planning conversation.
3. `approach_summary.md` — the Technical Decision Log (max 1,500 words) answering the brief's seven questions.

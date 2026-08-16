# RetailCast India - Approach Summary / Technical Decision Log

## Q1. Audit method
I treated this as a data reliability problem first and a modeling problem second. The audit order was:

1. Structural checks: row counts, key uniqueness, and day coverage for sales, calendar, prices, and both vendor feeds.
2. Availability-at-prediction-time checks: for every candidate feature, I verified whether values exist for d_1914 to d_1941 and whether the feature timing is causally usable.
3. Series profiling: per-id demand level, volatility, intermittent behavior, and change-point scans to detect potential regime shifts.
4. Feed provenance tests: per-id correlation, lead-lag diagnostics, and backtest utility of market_signal and vendor_signal.
5. Price sanity checks: non-positive values, large week-over-week jumps, and join completeness of price by store-item-week across history.
6. Honest validation: rolling 28-day holdouts near the end of history with strict time splits and leakage-safe feature generation.

I considered the audit complete only after each external feed had a clear "use / restrict / exclude" verdict, each high-risk series had a handling rule, and each modeling choice was tied to measured backtest impact.

## Q2. Data verdicts
### Verdict 1: market_signal is too risky for forecasting and likely leakage-like for history
What: market_signal coverage is exactly d_1 to d_1913 for all 60 ids, with no horizon values.

Evidence: the historical sales correlation is extremely high (overall 0.9421; per-id median 0.9228, min 0.8654, max 0.9614). Lead-lag diagnostics show best lag = 0 for all 60 series, which is atypical for a clean forward-looking external signal.

Action: I excluded market_signal from model training and inference features. It may be useful for exploratory diagnostics, but not for production forecasting.

Rejected reading: "It is just a very strong demand predictor." I rejected this because it is unavailable in the forecast horizon and its same-day alignment across all series is too convenient to trust for future prediction.

### Verdict 2: vendor_signal is available through horizon but weak and inconsistent as a standalone forecast
What: vendor_signal has full coverage through d_1941 for all 60 ids.

Evidence: historical utility is weak: per-id sales correlation median 0.0983 (min -0.0015, max 0.5757). On historical backtest period, vendor historical WAPE is 0.6053 and MAE is 7.0811. As a direct forecast model in rolling holdouts, it underperforms simple baselines (mean RMSSE 0.9567, mean WAPE 0.4992).

Action: I did not use vendor_signal as a primary forecast driver. I treated it as a benchmark/reference series only.

Rejected reading: "Because it includes future values, it should be the strongest signal." Coverage alone is not quality; backtest evidence shows lower reliability than simple recency-seasonal baselines.

### Verdict 3: several series show structural level shifts; full-history averaging is unsafe for them
What: change-point scan identified major shifts, especially in GROCERY_3_ATTA and select HOMECARE_1_DETERGENT series.

Evidence: top examples include HOMECARE_1_DETERGENT_MH_3 around d_1387 (pre/post mean 13.55 to 34.20, ratio 2.52), GROCERY_3_ATTA_MH_3 around d_1077 (88.11 to 195.08, ratio 2.21), and HOMECARE_1_DETERGENT_TN_2 around d_1362 (7.81 to 17.76, ratio 2.27). Effect sizes are large (roughly 0.88 to 1.28 in the top group).

Action: I biased forecasts toward recent history and included regime-aware candidate models (tail-focused recency blend) in per-series model selection.

Rejected reading: "These are temporary outlier blocks." I rejected that interpretation because the post-change levels persist over long spans, indicating a new demand regime rather than isolated spikes.

### Verdict 4: price data is mostly clean; a few extreme toggles look promotion-like, not necessarily corrupt
What: sell_prices has no non-positive values and complete historical join coverage for store-item-week.

Evidence: non-positive count is 0 and missing price rate on historical panel is 0.0. Only 12 weekly jumps exceed 25 percent absolute change. Largest examples are KA_1 / ELECTRONICS_1_CHARGER toggling between 8.33 and 5.95, and MH_2 / GROCERY_3_PICKLE toggling between 4.34 and 1.20.

Action: I did not hard-correct these prices. I treated them as plausible promo/discount episodes and avoided aggressive manual cleaning.

Rejected reading: "All large price jumps are data errors." Repetition patterns suggest some are genuine campaign cycles; blind correction would inject bias.

### Verdict 5: panel integrity is high; no evidence of missing-join stockout artifacts in history
What: when joining sales to calendar and prices, I found no historical price join holes.

Evidence: missing_price_rate_on_history_panel = 0.0, so there is no need to infer stockouts from missing prices in historical data.

Action: I did not add missing-price imputation or stockout flags derived from missing price rows.

Rejected reading: "Zero sales may be mostly unpriced stockouts." With complete price joins, that interpretation is unsupported by this data.

## Q3. What I left alone
I deliberately avoided over-cleaning behaviors that look unusual but are still plausible retail signals. First, I did not winsorize sales spikes around festivals or promotional periods, because these are exactly the dynamics a replenishment forecast should carry forward probabilistically. Second, I did not force a global elasticity correction from price jumps; the number of extreme jumps is small, and broad corrective transforms risk damaging unaffected series. Third, I did not manually "fix" intermittent low-volume electronics series with many near-zero days; intermittent demand is real, and smoothing those series too aggressively can increase RMSSE by underestimating occasional bursts. In short, I prioritized robust forecasting rules over cosmetic data edits unless an anomaly had clear, reproducible evidence of being non-causal or non-available at prediction time.

## Q4. Modelling choices
I chose a leakage-safe recency-seasonal forecasting stack and finalized a single tuned global recipe for stability, reproducibility, and balanced RMSSE/WAPE performance.

Candidate models:
1. m28: mean of last 28 days.
2. wd8: same-weekday average from recent weeks.
3. recency_weighted: weighted level from last 14/28/56 days blended with weekly seasonality.
4. regime_blend: same as above but on post-change tail when a shift is detected.

Final selected recipe:
best_recipe uses alpha = 0.45 for weekly-shape blending, 10 weeks of same-weekday history, a moderate trend component (trend_weight = 0.3), and regime gating thresholds in the range shift_thr = 0.8 to 1.0 and min_shift_pos = 0.35 to 0.55. The top five parameter sets were effectively tied on validation, indicating the approach is not hypersensitive to a single knob setting.

Selection strategy:
I ran rolling 28-day backtests and compared fixed global recipes, baselines, and per-series selectors. Although per-series selection slightly improved mean RMSSE, it gave worse WAPE and introduces higher overfit risk from extra selection variance. For final submission I prefer the tuned global best_recipe.

Backtest summary:
- best_recipe (selected): mean RMSSE 0.8467, mean WAPE 0.4261.
- per_series_selected: mean RMSSE 0.8463, mean WAPE 0.4313.
- recency_weighted: mean RMSSE 0.8468, mean WAPE 0.4267.
- m28 baseline: mean RMSSE 0.8550, mean WAPE 0.4397.
- vendor-only baseline: mean RMSSE 0.9567, mean WAPE 0.4992.

Rejected alternatives:
1. Market-signal-driven supervised models: high leakage risk and no horizon availability.
2. Vendor forecast as primary prediction: empirically weaker than simple baselines.
3. One pooled global model over full history: less robust for shifted series.
4. Heavy feature engineering with uncertain future availability: higher fragility for this challenge.

## Q5. Validation you trust
I used walk-forward validation with three non-overlapping 28-day holdouts near the end of history:
1. d_1830 to d_1857
2. d_1858 to d_1885
3. d_1886 to d_1913

For each split, models were trained strictly on data before the split start. RMSSE denominators were computed from each training segment only. No future values, no horizon-known signals, and no same-day leaked features were used in training for that split.

Why this is honest:
1. The split geometry matches the final task (28-day horizon, rolling forward in time).
2. It pressures models on recency shifts and intermittent behavior.
3. It penalizes brittle overfit features that fail when data-generating conditions move.

Expected performance range:
I expect final holdout performance around mean RMSSE 0.845 to 0.875 and WAPE 0.41 to 0.44, with uncertainty from unseen events and regime continuation/decay in a few high-impact series.

## Q6. Least-sure call
My least-sure decision is how much, if any, vendor_signal should be blended into final forecasts for sparse or noisy series. I excluded it from primary modeling because historical evidence is weak on average, but there is a possibility that a subset of series receives useful vendor uplift in the true horizon.

What would change my mind:
1. Series-level evidence that vendor forecasts consistently beat recency baselines in the most recent windows.
2. Stable lead-lag behavior by series that supports causal use.
3. Reduced error specifically on high-volume series that dominate WAPE.

How I hedged:
I designed the approach so vendor can be optionally added as a tightly capped convex blend only when strict per-series validation criteria are met. Default behavior remains vendor weight = 0.

## Q7. Reproduce and stress
Reproducibility command for the repo build phase:

From repository root (`retail-cast`):

```bash
cd solution-copilot && python3 run_forecast.py --data-dir ../starter-kit/data --output submission.csv
```

Stress posture:
The pipeline should include automated checks for feed horizon coverage, suspicious same-day correlation, lag diagnostics, and regime-shift flags per series. If next month's data contains a new issue from the same family (feature leakage, feed drift, or structural demand shift), these checks should trigger warnings and route that series to conservative recency-first fallback models rather than silently trusting risky features.

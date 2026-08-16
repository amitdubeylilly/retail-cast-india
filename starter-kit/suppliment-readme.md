# RetailCast India — Starter Kit

Everything you need to produce and self-check a valid submission. Nothing here reveals the answer —
it just pins the **format** so your file is accepted for scoring.

## What's in here
- `sample_submission.csv` — the exact output format: **60 rows**, columns `id`, `F1`…`F28`
  (`F1` = first horizon day `d_1914`, … `F28` = `d_1941`). Every value is `0`; replace with your
  forecasts.
- `olympics.json` — the machine-readable challenge manifest (metric, horizon, required artifacts).
- `validate_format.py` — a pre-submission **format** validator (no scoring).

The data you build against lives in `../data/` (see `../data/data_dictionary.md`).

## Producing your submission
1. Read the data from `../data/` (`sales_train.csv`, `calendar.csv`, `sell_prices.csv`,
   `market_signal.csv`, `etc`).
2. Forecast 28 daily values for each of the 60 series.
3. Write `submission.csv` with columns `id`, `F1`…`F28`. Values must be **numeric and
   non-negative** (fractional is fine). Ids must match `sample_submission.csv` verbatim; **row order
   does not matter** (it is aligned by `id`). Extra columns are ignored.

## Self-test before you submit
```bash
python3 validate_format.py --submission path/to/your/submission.csv
```
`PASS` means your file is structurally valid and will be accepted. It does **not** tell you your
accuracy — only the organizers score that, against the held-out horizon. If you see `FAIL`, fix the
reported issue and re-run.

## Submitting — the three artifacts
1. **Repo link** — your code, which reads `../data/` and regenerates `submission.csv`. Make it
   reproducible (pin dependencies; a `README` with the run command helps).
2. **Claude chat export (.md)** — your investigation and planning conversation. In Claude, use the
   conversation menu → **Export** to get the `.md`. This is the primary evidence of your data
   judgement, so make sure your Phase 1–2 reasoning is in it.
3. **Approach summary / Technical Decision Log** — max 1,500 words answering the seven questions
   in the challenge brief (audit method · data verdicts with the reading you rejected · what you
   left alone · modelling choices · validation you trust · your least-sure call · reproduce and
   stress). Every claim must be traceable to your chat export or your code.

## Reminders
- Individual challenge — build it yourself.
- The best honest score is bounded; an impossibly good score is flagged, not rewarded.
- Finding a data problem and saying so (with evidence) scores more than silently getting lucky.

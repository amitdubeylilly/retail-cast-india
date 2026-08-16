# RetailCast India — Forecast the Unforecastable

Claude Olympics challenge: forecast 28 days of daily demand (`d_1914`…`d_1941`) for 60
product-store series across six product lines, ten stores, and three Indian states
(Maharashtra, Karnataka, Tamil Nadu). See [challenge-brief.md](challenge-brief.md) for the
full brief, scoring rubric, and submission requirements.

## Layout

| Path | What it is |
|---|---|
| [starter-kit/](starter-kit/) | Organizer-provided data, format validator, and challenge manifest (`olympics.json`). Not modified. |
| [solution-claude/](solution-claude/) | Forecasting pipeline built with Claude Code — data audit, model, and generated `submission.csv`. |
| [solution-copilot/](solution-copilot/) | Forecasting pipeline built with GitHub Copilot, for comparison. |
| [challenge-brief.md](challenge-brief.md) | Full challenge brief, evaluation rubric, and required artifacts. |

Each solution folder has its own `README.md` with the exact reproduce command and its own
`approach_summary.md` / `approach-summary.md` (Technical Decision Log) answering the
challenge's seven audit/modelling questions.

## Data

Both solutions read from `starter-kit/data/`: `sales_train.csv`, `calendar.csv`,
`sell_prices.csv`, `market_signal.csv`, `vendor_signal.csv`, and `sample_submission.csv`
(schema in [starter-kit/data/data_dictionary.md](starter-kit/data/data_dictionary.md)).
`solution-claude/data/` holds a local copy used by its own scripts.

## Reproducing a submission

```bash
# Claude solution
cd solution-claude
pip install -r requirements.txt
python src/forecast.py --data data --out submission.csv
python validate_format.py --submission submission.csv --sample data/sample_submission.csv

# Copilot solution
cd solution-copilot
python3 -m pip install -r requirements.txt
python3 run_forecast.py --data-dir ../starter-kit/data --output submission.csv
python3 ../starter-kit/validate_format.py --submission submission.csv --sample ../starter-kit/sample_submission.csv
```

`PASS` from the validator means the file is structurally valid — it does not indicate
forecast accuracy, which is scored separately against the held-out horizon.

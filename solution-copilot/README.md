# RetailCast India - Copilot Solution

This folder contains the runnable Copilot forecasting pipeline for the RetailCast India challenge.

## Files
- `run_forecast.py`: generates the 28-day forecast file.
- `approach-summary.md`: technical decision log.
- `requirements.txt`: Python dependencies.
- `submission.csv`: generated prediction artifact.

## Reproduce
Option A (run from this folder):

```bash
python3 -m pip install -r requirements.txt
python3 run_forecast.py --data-dir ../starter-kit/data --output submission.csv
python3 ../starter-kit/validate_format.py --submission submission.csv --sample ../starter-kit/sample_submission.csv
```

Option B (run from repository root `retail-cast`):

```bash
cd solution-copilot
python3 -m pip install -r requirements.txt
python3 run_forecast.py --data-dir ../starter-kit/data --output submission.csv
python3 ../starter-kit/validate_format.py --submission submission.csv --sample ../starter-kit/sample_submission.csv
```

Expected result: validator prints `PASS`.

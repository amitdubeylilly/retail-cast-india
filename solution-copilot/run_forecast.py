#!/usr/bin/env python3
"""
RetailCast India - Copilot forecasting pipeline.

Method (leakage-safe, recency-seasonal):
    pred = alpha * same_weekday_mean + (1 - alpha) * recent_level + trend_adjustment

Key design choices:
- market_signal and vendor_signal are intentionally excluded from prediction.
- Optional regime gating shortens effective history for shifted series.
- Output is aligned to sample_submission ids and columns F1..F28.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


HORIZON = 28
LAST_HIST_DAY = 1913

# Tuned recipe parameters from internal rolling backtests.
ALPHA = 0.45
WEEKS = 10
SHIFT_THRESHOLD = 0.9
MIN_SHIFT_POSITION = 0.45
TREND_WEIGHT = 0.3
TREND_WINDOW = 56
TREND_CAP = 0.6


def default_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "starter-kit" / "data"


def required_files(data_dir: Path) -> Iterable[Path]:
    names = [
        "sales_train.csv",
        "calendar.csv",
        "sample_submission.csv",
    ]
    for name in names:
        yield data_dir / name


def validate_inputs(data_dir: Path) -> None:
    missing = [str(p) for p in required_files(data_dir) if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input file(s): {missing}")


def detect_regime_split(y: np.ndarray, min_seg: int = 280) -> tuple[int | None, float]:
    n = len(y)
    if n < (2 * min_seg + 1):
        return None, -1.0

    best_t = None
    best_effect = -1.0
    for t in range(min_seg, n - min_seg):
        a = y[:t]
        b = y[t:]
        s1 = np.std(a, ddof=1)
        s2 = np.std(b, ddof=1)
        pooled = np.sqrt((s1 * s1 + s2 * s2) / 2.0)
        if pooled <= 1e-8:
            continue
        effect = abs(np.mean(b) - np.mean(a)) / pooled
        if effect > best_effect:
            best_effect = effect
            best_t = t
    return best_t, best_effect


def choose_tail(y: np.ndarray) -> np.ndarray:
    split, effect = detect_regime_split(y)
    if split is not None and effect >= SHIFT_THRESHOLD and split >= int(MIN_SHIFT_POSITION * len(y)):
        tail = y[split:]
        if len(tail) >= 56:
            return tail
    return y


def same_weekday_mean(full_y: np.ndarray, step: int, weeks: int = WEEKS) -> float:
    n = len(full_y)
    refs = []
    for j in range(1, weeks + 1):
        idx = n + step - 7 * j
        if 0 <= idx < n:
            refs.append(full_y[idx])
    if refs:
        return float(np.mean(refs))
    return float(np.mean(full_y[-28:]))


def trend_adjustment(series: np.ndarray, step: int, base_level: float) -> float:
    if len(series) < TREND_WINDOW:
        return 0.0
    x = np.arange(TREND_WINDOW)
    y = series[-TREND_WINDOW:]
    slope = float(np.polyfit(x, y, 1)[0])
    raw_adj = slope * (step + 1)
    cap = TREND_CAP * max(base_level, 1e-9)
    return float(np.clip(raw_adj, -cap, cap))


def forecast_series(y: np.ndarray) -> np.ndarray:
    tail = choose_tail(y)
    recent_level = float(np.mean(tail[-28:])) if len(tail) >= 28 else float(np.mean(tail))

    preds = np.zeros(HORIZON, dtype=float)
    for k in range(HORIZON):
        seasonal = same_weekday_mean(y, k, WEEKS)
        pred = ALPHA * seasonal + (1.0 - ALPHA) * recent_level
        pred += TREND_WEIGHT * trend_adjustment(tail, k, recent_level)
        preds[k] = max(0.0, pred)
    return preds


def build_submission(data_dir: Path) -> pd.DataFrame:
    sales = pd.read_csv(data_dir / "sales_train.csv")
    sample = pd.read_csv(data_dir / "sample_submission.csv")

    d_cols = [f"d_{i}" for i in range(1, LAST_HIST_DAY + 1)]
    if not set(d_cols).issubset(sales.columns):
        raise ValueError("sales_train.csv does not contain expected day columns d_1..d_1913")

    sales_matrix = sales.set_index("id")[d_cols].astype(float)
    out = sample[["id"]].copy()

    forecasts = []
    for sid in out["id"]:
        if sid not in sales_matrix.index:
            raise KeyError(f"id from sample_submission missing in sales_train: {sid}")
        y = sales_matrix.loc[sid].to_numpy(dtype=float)
        forecasts.append(forecast_series(y))

    arr = np.vstack(forecasts)
    for i in range(HORIZON):
        out[f"F{i + 1}"] = np.round(arr[:, i], 4)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RetailCast 28-day submission.csv")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_data_dir(),
        help="Path containing sales_train.csv, calendar.csv, and sample_submission.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("submission.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()

    validate_inputs(data_dir)
    sub = build_submission(data_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sub.to_csv(output_path, index=False)

    print(f"Wrote {output_path}")
    print(f"Rows: {len(sub)} | Columns: {len(sub.columns)}")
    print(f"Total predicted units (F1..F28): {sub.iloc[:, 1:].to_numpy().sum():.2f}")


if __name__ == "__main__":
    main()

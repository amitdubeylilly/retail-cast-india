#!/usr/bin/env python3
"""
RetailCast India - 28-day demand forecast pipeline.

Method (deliberately robust, per-series):
    forecast[d] = recent_level * day_of_week_multiplier[weekday(d)] * festival_uplift(d)

Design is driven by the data audit (see audit.py / approach summary):
  - market_signal.csv is EXCLUDED: it is target leakage (units x ~10 x noise, same-day
    only) and does not cover the horizon (ends d_1913).
  - vendor_signal.csv is NOT used as the forecast: on backtest it is beaten by a simple
    trailing mean per series. (Left available for optional blending/inspection only.)
  - sell_price is EXCLUDED: within-series price/units correlation ~ 0 (no usable signal).
  - Recent window is short (42d) because the panel rewards recency; the KA_3 store is in a
    genuine store-wide decline, so its series use an even shorter 28d window (we hold the
    recent level, we do NOT extrapolate the decline further).
  - Festivals (event_type_1 present) get a modest 1.15x uplift; weekend seasonality is
    captured by the day-of-week profile.

Usage:
    python src/forecast.py --data data --out submission.csv
"""
import argparse, os
import numpy as np
import pandas as pd

HORIZON = 28
LAST_HIST_DAY = 1913
LEVEL_WINDOW_DEFAULT = 42
LEVEL_WINDOW_REGIME = 28          # KA_3 store: shorter, tracks the ongoing decline
REGIME_STORES = ("_KA_3_",)      # store(s) flagged by the audit as regime-shifted
DOW_WINDOW = 180                  # days used to estimate the day-of-week profile
FESTIVAL_UPLIFT = 1.15


def load(data_dir):
    sales = pd.read_csv(os.path.join(data_dir, "sales_train.csv"))
    cal = pd.read_csv(os.path.join(data_dir, "calendar.csv"))
    cal["dn"] = cal["d"].str.replace("d_", "", regex=False).astype(int)
    return sales, cal


def build_maps(cal):
    wmap = cal.set_index("dn")["wday"].to_dict()
    emap = cal.set_index("dn")["event_type_1"].to_dict()
    return wmap, emap


def series_forecast(v, last_day, horizon, window, wmap, emap):
    """v: pd.Series indexed by integer day, sales history for one series."""
    recent = v[v.index > last_day - window]
    level = recent.mean() if len(recent) else 0.0

    lwin = v[v.index > last_day - DOW_WINDOW]
    base = lwin.mean()
    if not base or base <= 0:
        base = 1e-6
    dow_means = lwin.groupby([wmap[d] for d in lwin.index]).mean()
    dow_mult = {k: (dow_means.get(k, base) / base) for k in range(1, 8)}

    out = []
    for h in range(1, horizon + 1):
        d = last_day + h
        f = level * dow_mult.get(wmap[d], 1.0)
        ev = emap.get(d)
        if isinstance(ev, str) and ev != "":
            f *= FESTIVAL_UPLIFT
        out.append(max(f, 0.0))
    return np.array(out)


def window_for(series_id):
    return LEVEL_WINDOW_REGIME if any(s in series_id for s in REGIME_STORES) else LEVEL_WINDOW_DEFAULT


def run(data_dir, out_path):
    sales, cal = load(data_dir)
    wmap, emap = build_maps(cal)
    dcols = [c for c in sales.columns if c.startswith("d_")]
    X = sales.set_index("id")[dcols].astype(float)
    X.columns = np.arange(1, len(dcols) + 1)

    rows = []
    for sid, v in X.iterrows():
        f = series_forecast(v, LAST_HIST_DAY, HORIZON, window_for(sid), wmap, emap)
        rows.append([sid] + list(np.round(f, 3)))

    sub = pd.DataFrame(rows, columns=["id"] + [f"F{i}" for i in range(1, HORIZON + 1)])
    sub.to_csv(out_path, index=False)
    print(f"Wrote {out_path}: {sub.shape[0]} rows, "
          f"total 28d units={sub.iloc[:,1:].values.sum():.1f}")
    return sub


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="submission.csv")
    args = ap.parse_args()
    run(args.data, args.out)

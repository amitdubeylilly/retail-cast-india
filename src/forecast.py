#!/usr/bin/env python3
"""
RetailCast India - 28-day demand forecast pipeline.

Method (deliberately robust, per-series):
    forecast[d] = recent_level * day_of_week_multiplier[weekday(d)] * festival_uplift(d)
                  * [price_promo_uplift if applicable]

Design is driven by the data audit (see audit.py / approach summary):
  - market_signal.csv is EXCLUDED: it is target leakage (units x ~10 x noise, same-day
    only) and does not cover the horizon (ends d_1913).
  - vendor_signal.csv is NOT used as the forecast: on backtest it is beaten by a simple
    trailing mean per series. (Left available for optional blending/inspection only.)
  - sell_price is EXCLUDED globally (median per-series corr ~ -0.03), EXCEPT for
    ELECTRONICS_1_CHARGER at KA_1 which has genuine promotional pricing in the horizon
    (week 2314 = d_1914-1920, price drops 28% from 8.33 to 5.95; recent promo weeks
    show 1.17x-1.80x uplift vs surrounding weeks). The phantom 1.20 pickle price at
    MH_2 is a data error and is correctly ignored.
  - TN_2 is treated as a PERMANENT post-break regime: the store experienced a structural
    decline, so its series use a short 28d window anchoring to the new steady state.
  - KA_3's late dip is treated as TRANSIENT/recovering: a longer 56d window allows the
    level to average in some pre-dip volume rather than anchoring to the trough.
  - Stockout-censored zero windows (>=7 consecutive zero days) are detected and masked
    from the level/DOW calculations so they don't drag the demand estimate down.
  - Festivals (event_type_1 present) get a modest 1.15x uplift; weekend seasonality is
    captured by the day-of-week profile.
  - GROCERY_3_ATTA gets an April haircut (0.90x, April days only).

Usage:
    python src/forecast.py --data data --out submission.csv
"""
import argparse, os
import numpy as np
import pandas as pd

HORIZON = 28
LAST_HIST_DAY = 1913
LEVEL_WINDOW_DEFAULT = 42
LEVEL_WINDOW_REGIME = 28          # TN_2: permanent post-break regime anchor
LEVEL_WINDOW_RECOVERING = 56     # KA_3: transient dip, allow recovery via longer window
REGIME_STORES = ("_TN_2_",)      # permanent regime shift — anchor to post-break level
RECOVERING_STORES = ("_KA_3_",)  # transient dip — longer window allows recovery
DOW_WINDOW = 180
FESTIVAL_UPLIFT = 1.15
APRIL_MONTH = 4
APRIL_HAIRCUT_PRODUCTS = {"GROCERY_3_ATTA": 0.90}
STOCKOUT_MIN_CONSECUTIVE = 7     # >= 7 consecutive zeros = stockout, masked from level
PROMO_UPLIFT = 1.20              # KA_1 charger promo: conservative (measured 1.17-1.80x)
PROMO_SERIES = "ELECTRONICS_1_CHARGER_KA_1_validation"
PROMO_HORIZON_DAYS = set(range(1914, 1921))  # week 2314 = first 7 horizon days


def load(data_dir):
    sales = pd.read_csv(os.path.join(data_dir, "sales_train.csv"))
    cal = pd.read_csv(os.path.join(data_dir, "calendar.csv"))
    cal["dn"] = cal["d"].str.replace("d_", "", regex=False).astype(int)
    return sales, cal


def build_maps(cal):
    wmap = cal.set_index("dn")["wday"].to_dict()
    emap = cal.set_index("dn")["event_type_1"].to_dict()
    mmap = cal.set_index("dn")["month"].to_dict()
    return wmap, emap, mmap


def product_of(series_id):
    return "_".join(series_id.split("_")[:-3])


def detect_stockout_days(v):
    """Return set of day-indices that fall within stockout windows (>=7 consecutive zeros)."""
    stockout_days = set()
    vals = v.values
    days = v.index.values
    in_run = False
    run_start = 0
    for i, val in enumerate(vals):
        if val == 0:
            if not in_run:
                in_run = True
                run_start = i
        else:
            if in_run:
                if i - run_start >= STOCKOUT_MIN_CONSECUTIVE:
                    stockout_days.update(days[run_start:i])
                in_run = False
    if in_run and len(vals) - run_start >= STOCKOUT_MIN_CONSECUTIVE:
        stockout_days.update(days[run_start:])
    return stockout_days


def series_forecast(v, last_day, horizon, window, wmap, emap, mmap=None, series_id=None):
    """v: pd.Series indexed by integer day, sales history for one series."""
    stockout_days = detect_stockout_days(v)

    recent = v[v.index > last_day - window]
    recent_clean = recent[~recent.index.isin(stockout_days)]
    level = recent_clean.mean() if len(recent_clean) else (recent.mean() if len(recent) else 0.0)

    lwin = v[v.index > last_day - DOW_WINDOW]
    lwin_clean = lwin[~lwin.index.isin(stockout_days)]
    base = lwin_clean.mean() if len(lwin_clean) else (lwin.mean() if len(lwin) else 1e-6)
    if not base or base <= 0:
        base = 1e-6
    dow_means = lwin_clean.groupby([wmap[d] for d in lwin_clean.index]).mean()
    dow_mult = {k: (dow_means.get(k, base) / base) for k in range(1, 8)}

    haircut = APRIL_HAIRCUT_PRODUCTS.get(product_of(series_id)) if series_id else None
    is_promo_series = (series_id == PROMO_SERIES)

    out = []
    for h in range(1, horizon + 1):
        d = last_day + h
        f = level * dow_mult.get(wmap[d], 1.0)
        ev = emap.get(d)
        if isinstance(ev, str) and ev != "":
            f *= FESTIVAL_UPLIFT
        if haircut is not None and mmap is not None and mmap.get(d) == APRIL_MONTH:
            f *= haircut
        if is_promo_series and d in PROMO_HORIZON_DAYS:
            f *= PROMO_UPLIFT
        out.append(max(f, 0.0))
    return np.array(out)


def window_for(series_id):
    if any(s in series_id for s in REGIME_STORES):
        return LEVEL_WINDOW_REGIME
    if any(s in series_id for s in RECOVERING_STORES):
        return LEVEL_WINDOW_RECOVERING
    return LEVEL_WINDOW_DEFAULT


def run(data_dir, out_path):
    sales, cal = load(data_dir)
    wmap, emap, mmap = build_maps(cal)
    dcols = [c for c in sales.columns if c.startswith("d_")]
    X = sales.set_index("id")[dcols].astype(float)
    X.columns = np.arange(1, len(dcols) + 1)

    rows = []
    for sid, v in X.iterrows():
        f = series_forecast(v, LAST_HIST_DAY, HORIZON, window_for(sid), wmap, emap, mmap, sid)
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

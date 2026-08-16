#!/usr/bin/env python3
"""
RetailCast India - data audit. Regenerates every evidence claim in the approach summary.
Run:  python src/audit.py --data data
"""
import argparse, os
import numpy as np
import pandas as pd


def main(data_dir):
    sales = pd.read_csv(os.path.join(data_dir, "sales_train.csv"))
    cal = pd.read_csv(os.path.join(data_dir, "calendar.csv"))
    mkt = pd.read_csv(os.path.join(data_dir, "market_signal.csv"))
    ven = pd.read_csv(os.path.join(data_dir, "vendor_signal.csv"))
    dcols = [c for c in sales.columns if c.startswith("d_")]

    long = sales.melt(id_vars=["id"], value_vars=dcols, var_name="d", value_name="units")
    long["dn"] = long["d"].str.replace("d_", "", regex=False).astype(int)
    for df in (mkt, ven):
        df["dn"] = df["d"].str.replace("d_", "", regex=False).astype(int)

    print("### 1. FEED COVERAGE")
    print("  market_signal days:", mkt["dn"].min(), "->", mkt["dn"].max(),
          "| covers horizon(1941)?", mkt["dn"].max() >= 1941)
    print("  vendor_signal days:", ven["dn"].min(), "->", ven["dn"].max(),
          "| covers horizon(1941)?", ven["dn"].max() >= 1941)

    print("\n### 2. MARKET_SIGNAL LEAKAGE")
    m = long.merge(mkt[["id", "dn", "mkt_signal"]], on=["id", "dn"], how="left")
    for lag in (-1, 0, 1):
        cs = [g["units"].corr(g["mkt_signal"].shift(lag))
              for _, g in m.sort_values("dn").groupby("id")]
        print(f"  mean per-series corr(units, signal) lag {lag:+d}: {np.nanmean(cs):.3f}")
    z = m[m["units"] == 0]["mkt_signal"]
    print(f"  signal exactly 0 when units==0: {(z == 0).mean()*100:.1f}% of rows")

    print("\n### 3. VENDOR QUALITY (last-28-day per-series WAPE vs trailing-mean)")
    v = long.merge(ven[["id", "dn", "vendor_forecast"]], on=["id", "dn"], how="left")
    def wape(a, f): return np.abs(a - f).sum() / max(np.abs(a).sum(), 1e-9)
    ev, em = [], []
    for _, g in v.groupby("id"):
        g = g.sort_values("dn"); hist = g[g["dn"] <= 1885]; test = g[g["dn"] >= 1886]
        ev.append(wape(test["units"].values, test["vendor_forecast"].values))
        em.append(wape(test["units"].values, np.repeat(hist["units"].tail(28).mean(), len(test))))
    print(f"  vendor per-series WAPE={np.mean(ev):.3f}  trailing-mean WAPE={np.mean(em):.3f}")

    print("\n### 4. KA_3 REGIME (last-90 vs prior-year mean)")
    X = sales.set_index("id")[dcols].astype(float)
    for sid in [i for i in X.index if "_KA_3_" in i]:
        vv = X.loc[sid].values
        prev, late = vv[-365:-90].mean(), vv[-90:].mean()
        print(f"  {sid.replace('_validation',''):34s} prevyr={prev:6.2f} last90={late:6.2f} "
              f"ratio={late/max(prev,1e-9):.2f}")
    print("  (compare: same product in other stores stays ~1.0 - see README)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data")
    main(ap.parse_args().data)

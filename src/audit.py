#!/usr/bin/env python3
"""
RetailCast India - data audit.
Regenerates EVERY quantitative claim in approach_summary.md (Q1-Q7), so each number
in the write-up is traceable to this one script. Also runs the adversarial sweep
(duplicate series, SNAP signal, horizon events, month-of-year seasonality) and the
3-window rolling backtest.

Run:  python src/audit.py --data data
"""
import argparse, os
import numpy as np
import pandas as pd


def load(data_dir):
    sales = pd.read_csv(os.path.join(data_dir, "sales_train.csv"))
    cal = pd.read_csv(os.path.join(data_dir, "calendar.csv"))
    price = pd.read_csv(os.path.join(data_dir, "sell_prices.csv"))
    mkt = pd.read_csv(os.path.join(data_dir, "market_signal.csv"))
    ven = pd.read_csv(os.path.join(data_dir, "vendor_signal.csv"))
    cal["dn"] = cal["d"].str.replace("d_", "", regex=False).astype(int)
    for df in (mkt, ven):
        df["dn"] = df["d"].str.replace("d_", "", regex=False).astype(int)
    return sales, cal, price, mkt, ven


def wape(a, f):
    a, f = np.asarray(a, float), np.asarray(f, float)
    return np.abs(a - f).sum() / max(np.abs(a).sum(), 1e-9)


def main(data_dir):
    sales, cal, price, mkt, ven = load(data_dir)
    dcols = [c for c in sales.columns if c.startswith("d_")]
    long = sales.melt(id_vars=["id", "item_id", "store_id"], value_vars=dcols,
                      var_name="d", value_name="units")
    long["dn"] = long["d"].str.replace("d_", "", regex=False).astype(int)
    X = sales.set_index("id")[dcols].astype(float)
    X.columns = np.arange(1, len(dcols) + 1)

    # ---------------------------------------------------------------- Q1
    print("### Q1. COVERAGE / STRUCTURE")
    print(f"  sales/market end at d_{X.columns.max()} (history);"
          f" calendar to d_{cal['dn'].max()}, vendor to d_{ven['dn'].max()} (>= horizon d_1941)")
    print(f"  sales clean: negatives={bool((X.values<0).any())} nan={bool(np.isnan(X.values).any())}"
          f" integer={bool(np.all(X.values==np.floor(X.values)))} max={X.values.max():.0f}")
    print(f"  day index continuous 1..{cal['dn'].max()}: "
          f"{list(cal['dn'])==list(range(1,cal['dn'].max()+1))}; dup dates={cal['date'].duplicated().any()}")

    # ---------------------------------------------------------------- Q2 V1
    print("\n### Q2 V1. MARKET_SIGNAL LEAKAGE")
    m = long.merge(mkt[["id", "dn", "mkt_signal"]], on=["id", "dn"], how="left")
    for lag in (-1, 0, 1):
        cs = [g["units"].corr(g["mkt_signal"].shift(lag))
              for _, g in m.sort_values("dn").groupby("id")]
        print(f"  mean per-series corr(units, signal) lag {lag:+d}: {np.nanmean(cs):.3f}")
    z = m[m["units"] == 0]["mkt_signal"]
    both = m[(m["units"] > 0) & (m["mkt_signal"] > 0)]
    print(f"  signal exactly 0 when units==0: {(z==0).mean()*100:.1f}% of rows")
    print(f"  median ratio mkt_signal/units where both>0: {(both['mkt_signal']/both['units']).median():.2f}")

    # ---------------------------------------------------------------- Q2 V2
    print("\n### Q2 V2. VENDOR_SIGNAL WEAK BUT LEGIT")
    v = long.merge(ven[["id", "dn", "vendor_forecast"]], on=["id", "dn"], how="left")
    vc = [g["units"].corr(g["vendor_forecast"]) for _, g in v.groupby("id")]
    print(f"  per-series corr(units, vendor) median: {np.nanmedian(vc):.2f}")
    print(f"  vendor mean when units==0 (never exactly 0): {v[v['units']==0]['vendor_forecast'].mean():.1f}")
    ev, em = [], []
    for _, g in v.groupby("id"):
        g = g.sort_values("dn"); hist = g[g["dn"] <= 1885]; test = g[g["dn"] >= 1886]
        ev.append(wape(test["units"], test["vendor_forecast"]))
        em.append(wape(test["units"], np.repeat(hist["units"].tail(28).mean(), len(test))))
    print(f"  last-28 per-series WAPE: vendor={np.mean(ev):.2f}  trailing-mean={np.mean(em):.2f}")

    # ---------------------------------------------------------------- Q2 V3
    print("\n### Q2 V3. KA_3 STORE-WIDE DECLINE")
    for sid in [i for i in X.index if "_KA_3_" in i]:
        vv = X.loc[sid].values
        prev, late = vv[-365:-90].mean(), vv[-90:].mean()
        print(f"  {sid.replace('_validation',''):34s} prevyr={prev:6.2f} last90={late:6.2f}"
              f" ratio={late/max(prev,1e-9):.2f}")
    print("  cross-store check (DETERGENT last90/prevyr by store):")
    for sid in [i for i in X.index if "HOMECARE_1_DETERGENT" in i]:
        vv = X.loc[sid].values
        print(f"    {sid.replace('_validation',''):34s} ratio={vv[-90:].mean()/max(vv[-365:-90].mean(),1e-9):.2f}")

    # ---------------------------------------------------------------- Q2 V4 (births/deaths)
    print("\n### Q2 V4. LATE INTRODUCTIONS / DEATHS (first & last non-zero day)")
    for sid, row in X.iterrows():
        nz = np.where(row.values > 0)[0]
        first, last = (nz[0] + 1, nz[-1] + 1) if len(nz) else (None, None)
        if first and first > 200:
            print(f"  LATE START  {sid.replace('_validation',''):34s} first non-zero d_{first}")
        if last and last < 1800:
            print(f"  EARLY DEATH {sid.replace('_validation',''):34s} last non-zero d_{last}")

    # ---------------------------------------------------------------- Q3
    print("\n### Q3. RESTRAINT (things left alone)")
    cal_d = cal.set_index("d")
    top = X.max(axis=1).idxmax()
    vv = X.loc[top]; dmax = f"d_{int(vv.idxmax())}"
    print(f"  biggest spike: {top.replace('_validation','')} = {vv.max():.0f} on {dmax}"
          f" ({cal_d.loc[dmax,'date']}, event={cal_d.loc[dmax,'event_name_1']}),"
          f" ~{vv.max()/vv[vv>0].median():.0f}x positive-day median")
    le = long.merge(cal[["d", "event_type_1"]], on="d")
    on = le[le["event_type_1"].notna()]["units"].mean(); off = le[le["event_type_1"].isna()]["units"].mean()
    print(f"  festival-day uplift: {on/off:.2f}x  (event {on:.2f} vs non-event {off:.2f})")
    snap = [c for c in cal.columns if "snap" in c.lower()]
    ls = long.merge(cal[["d"] + snap], on="d"); ls["state"] = ls["store_id"].str.split("_").str[0]
    for s in snap:
        st = s.split("_")[-1]; sub = ls[ls["state"] == st]
        onv = sub[sub[s] == 1]["units"].mean(); offv = sub[sub[s] == 0]["units"].mean()
        print(f"  {s} lift={onv/max(offv,1e-9):.2f} (no signal -> not used)")

    # ---------------------------------------------------------------- Q4
    print("\n### Q4. FEATURE DIAGNOSTICS")
    lw = long.merge(cal[["d", "weekday"]], on="d").groupby("weekday")["units"].mean()
    print(f"  weekday profile: Sat={lw.get('Saturday',float('nan')):.1f} Tue={lw.get('Tuesday',float('nan')):.1f}"
          f" (Sun={lw.get('Sunday',float('nan')):.1f})")
    lp = long.merge(cal[["d", "wm_yr_wk"]], on="d").merge(
        price, on=["store_id", "item_id", "wm_yr_wk"], how="left")
    cs = []
    for _, g in lp.groupby("id"):
        wk = g.groupby("wm_yr_wk").agg(u=("units", "mean"), p=("sell_price", "mean")).dropna()
        if wk["p"].nunique() > 3:
            c = wk["u"].corr(wk["p"])
            if pd.notna(c):
                cs.append(c)
    print(f"  price elasticity: median within-series corr(units, price)={np.median(cs):+.2f} (near 0 -> excluded)")

    # ---------------------------------------------------------------- Sweep: structure + April
    print("\n### SWEEP. STRUCTURE + APRIL SEASONALITY")
    arr = X.values
    C = np.corrcoef(arr)
    ndup = sum(1 for i in range(len(arr)) for j in range(i + 1, len(arr)) if C[i, j] > 0.995)
    print(f"  duplicate/near-duplicate series (corr>0.995): {ndup}")
    hor = cal[(cal["dn"] >= 1914) & (cal["dn"] <= 1941)]
    evs = hor[hor["event_name_1"].notna()][["d", "event_name_1"]]
    print(f"  horizon events in event_type_1: {list(zip(evs['d'], evs['event_name_1']))}")
    lm = long.merge(cal[["d", "month", "year"]], on="d")
    piv = lm.groupby(["item_id", "month"])["units"].mean().unstack("month")
    print("  April(m4) vs Feb-Mar level-window, per product (pooled all years):")
    for it in piv.index:
        fm = np.nanmean([piv.loc[it].get(2), piv.loc[it].get(3)]); ap = piv.loc[it].get(4)
        print(f"    {it:26s} FebMar={fm:6.1f} Apr={ap:6.1f} Apr/FebMar={ap/max(fm,1e-9):.2f}")
    l22 = lm[lm["year"] == 2022]
    a22 = l22[l22["month"] == 4].groupby("item_id")["units"].mean()
    b22 = l22[l22["month"].isin([2, 3])].groupby("item_id")["units"].mean()
    print(f"    ATTA 2022 analog Apr/FebMar={a22['GROCERY_3_ATTA']/max(b22['GROCERY_3_ATTA'],1e-9):.2f}")

    # ---------------------------------------------------------------- Q5 backtest (3 windows)
    print("\n### Q5. ROLLING BACKTEST (uses forecast.py logic)")
    import importlib.util
    fp = os.path.join(os.path.dirname(__file__), "forecast.py")
    spec = importlib.util.spec_from_file_location("fc", fp)
    fc = importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)
    _, cal2 = fc.load(data_dir); wmap, emap, mmap = fc.build_maps(cal2)

    def rmsse(tr, a, p):
        s = np.mean(np.diff(tr) ** 2) or 1e-6
        return np.sqrt(np.mean((a - p) ** 2) / s)

    for cut in (1829, 1857, 1885):
        R, A, F = [], [], []
        for sid, vv in X.iterrows():
            tr = vv[vv.index <= cut]; a = vv[(vv.index > cut) & (vv.index <= cut + 28)].values
            if len(a) < 28:
                continue
            p = fc.series_forecast(tr, cut, 28, fc.window_for(sid), wmap, emap, mmap, sid)
            R.append(rmsse(tr.values, a, p)); A.append(a); F.append(p)
        print(f"  train<=d_{cut} -> d_{cut+1}..d_{cut+28}:"
              f"  meanRMSSE={np.mean(R):.3f}  WAPE={wape(np.concatenate(A),np.concatenate(F)):.3f}")

    # ---------------------------------------------------------------- April validation
    # None of the 3 windows above touch April, and the true horizon (d_1914-1941) is
    # entirely April -- so the GROCERY_3_ATTA haircut in forecast.py can only be validated
    # against real historical Aprils. Each cutoff below is March 31 of a given year; the
    # ratio used is computed ONLY from years strictly before that year (no leakage from the
    # test window or later), exactly mirroring how forecast.py's hardcoded 0.90 was derived
    # from 2019-2022 (see SWEEP above) before ever touching the real d_1914-1941 horizon.
    print("\n### APRIL VALIDATION (ATTA haircut vs baseline, 4 historical Aprils)")
    atta_ids = [i for i in X.index if i.startswith("GROCERY_3_ATTA_")]
    cal_i = cal2.set_index("dn")

    def atta_ratio_before(test_year):
        total = X.loc[atta_ids].sum(axis=0)
        df = pd.DataFrame({"units": total}).join(cal_i[["month", "year"]])
        ratios = []
        for yr in (2019, 2020, 2021, 2022):
            if yr >= test_year:
                continue
            fm = df[(df.year == yr) & (df.month.isin([2, 3]))]["units"]
            ap = df[(df.year == yr) & (df.month == 4)]["units"]
            if len(fm) == 0 or len(ap) == 0 or fm.mean() < 1:
                continue
            ratios.append(ap.mean() / fm.mean())
        return float(np.mean(ratios)) if ratios else None

    base_r, base_w, corr_r, corr_w = [], [], [], []
    for cut, yr in ((450, 2019), (816, 2020), (1181, 2021), (1546, 2022)):
        ratio = atta_ratio_before(yr)
        Rb, Rc, Ab, Fb, Fc = [], [], [], [], []
        for sid, vv in X.iterrows():
            tr = vv[vv.index <= cut]; a = vv[(vv.index > cut) & (vv.index <= cut + 28)].values
            if len(a) < 28:
                continue
            pb = fc.series_forecast(tr, cut, 28, fc.window_for(sid), wmap, emap)
            pc = pb * ratio if (ratio is not None and sid in atta_ids) else pb
            Rb.append(rmsse(tr.values, a, pb)); Rc.append(rmsse(tr.values, a, pc))
            Ab.append(a); Fb.append(pb); Fc.append(pc)
        wb, wc = wape(np.concatenate(Ab), np.concatenate(Fb)), wape(np.concatenate(Ab), np.concatenate(Fc))
        base_r.append(np.mean(Rb)); base_w.append(wb); corr_r.append(np.mean(Rc)); corr_w.append(wc)
        rs = f"{ratio:.3f}" if ratio is not None else "n/a (no prior year)"
        print(f"  {yr} (cut d_{cut}) ratio={rs:20s}  base RMSSE={np.mean(Rb):.3f} WAPE={wb:.3f}"
              f"  ->  corrected RMSSE={np.mean(Rc):.3f} WAPE={wc:.3f}")
    print(f"  MEAN over 4 Aprils: baseline RMSSE={np.mean(base_r):.3f} WAPE={np.mean(base_w):.3f}"
          f"  ->  corrected RMSSE={np.mean(corr_r):.3f} WAPE={np.mean(corr_w):.3f}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data", default="data")
    main(ap.parse_args().data)

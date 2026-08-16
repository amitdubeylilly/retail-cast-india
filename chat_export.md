# RetailCast India — Phase 1–2 Investigation & Planning (Claude Desktop)

*Exported from the Claude Desktop conversation where the data was first loaded, probed, and the model was built and backtested. This is a formatting-only cleanup: duplicated UI status lines (Claude Desktop's tool-call markers, e.g. "Ran a command", rendered twice per call when copy-pasted) were collapsed to one instance each, and the starter-kit file list / findings list were restored to proper bullets. No conversational text, reasoning, tool call, or finding was removed. The later portion of this same conversation — where the finished repo was reviewed after the fact — is intentionally excluded here, since that review/deploy discussion is a separate artifact from the Phase 1–2 data investigation this file represents.*

---

## Turn 1

**User:**

Help check this claude olympics, let me know what you understand by sample starter kit & challenge details. `/Users/L120433/Projects/claude-olympics/retail-cast-india`

**Claude:** *(used Filesystem integration · 5 notes)*

I've read through the brief, the data dictionary, the manifest, the validator, and sampled the actual data files. Here's what this is and what I understand by each part.

**The challenge in one line**

It's an individual forecasting competition ("RetailCast India — Forecast the Unforecastable"). You get 1,913 days of daily sales for 60 series (6 products × 10 stores across MH/KA/TN) and must forecast the next 28 days (`d_1914`–`d_1941`) for every series. The twist is that the data is deliberately seeded with traps, and finding and reasoning about them is scored as heavily as the forecast itself.

The scoring is 100 points: Data Judgement 30, Forecast Accuracy 55 (RMSSE 36.7 + WAPE 18.3, on a flat curve where small differences are treated as noise), and Process & Communication 15. Two things stand out about how it's graded — a suspiciously good score is treated as an integrity flag rather than a win, and your reasoning is judged by a "Claude-as-Judge" reading your chat export and write-up, so unsupported claims are discounted.

The workflow is four phases: investigate in Claude Chat, plan in Claude Chat, build in Claude Code, then validate + submit. Three artifacts are required: the repo link, the chat export (.md) of your investigation, and the approach summary (≤1,500 words answering seven specific questions Q1–Q7).

**The starter kit**

The `starter-kit/` folder is purely about format, not answers:

- `sample_submission.csv` — the exact output shape: 60 rows, columns `id`, `F1`…`F28` (F1 = d_1914). All zeros to replace. Aligned by id, so row order doesn't matter.
- `validate_format.py` — a structural checker only. PASS means the file will be accepted; it says nothing about accuracy. It enforces 60 rows, correct ids, all F1–F28 present, numeric, non-negative, finite.
- `olympics.json` — machine-readable manifest (metric, horizon, required artifacts).
- `data/` — the actual build data plus `data_dictionary.md`.

The data files: `sales_train.csv` (wide, one row per series, `d_1`…`d_1913`), `calendar.csv` (`d_1`…`d_1969`, with Indian festivals, weekday, SNAP flags per state), `sell_prices.csv` (weekly price by store/item/week), and two vendor feeds — `market_signal.csv` and `vendor_signal.csv` — which the dictionary explicitly warns are not interchangeable and must be checked for coverage and provenance before use.

**What I noticed while checking (worth your attention)**

A few things jumped out that are either the intended traps or genuine issues in the kit itself:

The two vendor feeds behave very differently in coverage, which is almost certainly the central designed trap. `market_signal.csv` stops at `d_1913` — it does not extend into the horizon, so as-is you won't have it at prediction time. `vendor_signal.csv` runs all the way to `d_1941`, so it does cover the forecast window. I'd treat that coverage gap as the first thing to write up, and separately sanity-check whether the market signal's early values (I saw things like 9.3, 0.0, 27.6, 0.0) are derived from sales — the brief hints at a feed "derived from the very thing you are predicting." I'm flagging these as things to verify, not concluding them, since I only sampled a few rows.

Then some setup inconsistencies that look like real mistakes rather than intended traps:

- `approach-summary.md` is currently an empty directory, not a file. The manifest and brief both expect `approach_summary.md` as a file artifact — if you're a participant this is just your empty slot, but if you're QA-ing the kit it reads oddly.
- `olympics.json` lists `"metric": "mean_rmsse"` and its `data_files` array omits `vendor_signal.csv`, even though the dictionary describes it and it's present on disk. The manifest also lists only one metric while the brief scores on two (RMSSE + WAPE).
- The brief says "Curve anchors ship in the starter kit," but I don't see any scoring-curve-anchors file in the kit.
- `suppliment-readme.md` points to `../data/` and `starter_kit/validate_format.py`, but the folder is actually `starter-kit/` (hyphen) with `data/` nested inside it — minor path drift in the docs.

Do you want me to go deeper on any of these — for example, actually profile the data to confirm the market-signal leakage hypothesis and check for the "behaviour changed partway through" series the brief mentions? Or are you more interested in whether the kit itself is correctly assembled to hand out?

---

## Turn 2

**User:**

I'm participating in it, so help me win this compatition. Write a good approach if you understand properly.

**Claude:** *(thought for 29s)*

Winning this one is less about a fancy model and more about proving data judgement — 30 points ride on finding the real traps with evidence, and the rubric explicitly discounts unsupported claims and penalizes "issues that don't exist in the data." So the way I can actually help you win is to do the real audit on your data, find what's genuinely there, and then write an approach grounded in it. A polished-but-fabricated writeup would score badly by design.

Let me pull your data into my environment and investigate for real.

*(used Filesystem integration, ran 2 commands · 2 notes)*

`market_signal` stops exactly at `d_1913` (no horizon), `vendor_signal` runs through `d_1941`. Now the critical test — is the market signal leaked from the target? Let me correlate it against actual sales, including time-shifts.

*(ran a command)*

That's a smoking gun. The market signal is essentially units × ~10 × noise on the same day (same-day corr 0.92, but shifting it kills the correlation; it's exactly 0 whenever sales are 0). It's target leakage and it doesn't exist for the horizon. Now let me check whether `vendor_signal` is a usable honest baseline.

*(ran a command)*

Vendor signal is not leaked (it never hits exactly 0, per-series day-to-day correlation is weak), it's available for the horizon — but on a last-28-day backtest it's only naive-quality (per-series WAPE 1.04, actually worse than a trailing-28-day mean at 0.82). So it's a legitimate feed but a mediocre forecast: usable as an anchor/feature, not something to submit blindly. Now the other flagged trap — series whose behaviour changes partway through.

*(ran a command)*

Clear signal: every `KA_3` series dropped to a quarter–half of its prior level in the last 90 days — a store-wide regime change, not per-product noise. This is the big modelling trap. Let me pin down when the `KA_3` break happens and confirm it's the whole store.

*(ran a command)*

The `KA_3` decline is store-wide, specific to `KA_3` (same product in other stores holds ~flat), and it's a progressive slide over roughly the last 100 days rather than a clean step. Now let me check the horizon calendar/festivals, whether prices exist for the horizon weeks, and how intermittent the series are (all of which shape the model choice).

*(ran a command)*

Rich picture now. Horizon is 3–30 Apr 2023 with two religious festivals (Ram Navami, Eid al-Fitr); prices exist for all horizon weeks; strong weekend seasonality; heavy scale differences (ATTA ~52/day vs CABLE ~0.6/day) and 14 highly intermittent series. Two more quick checks — price effect and whether big spikes are festival-driven (things I should keep, not "fix") — then I'll build and backtest.

*(ran a command)*

Final picture is solid. Key evidence-backed findings:

- `market_signal` = target leakage (units × ~10 × noise, same-day only) and absent for the horizon → exclude.
- `vendor_signal` = honest but weak (beaten by a trailing mean per series) and present for the horizon → at most a light anchor.
- `KA_3` store = a real store-wide decline over the last ~100 days → level must come from the recent regime, not full history.
- Price elasticity ≈ 0 (drop it); festivals give ~1.3× lift (keep); strong weekend seasonality (model it); Diwali spikes are genuine, not errors (leave alone).

Now let me build the pipeline, backtest it honestly on held-out history, and get the number I can actually expect.

*(ran a command)*

The variants cluster tightly (exactly the "flat curve" the brief describes). A 56-day level window × recent day-of-week profile × festival uplift is consistently the best or tied-best on both backtests (mean RMSSE ≈ 0.83, WAPE ≈ 0.38–0.42) and clearly beats the vendor feed (RMSSE 0.93). Let me confirm it isn't overfit and that it handles `KA_3` without bias, then lock it in.

*(ran a command)*

Shorter windows keep helping because the data genuinely rewards recency — and the `KA_3` bias check shows why: even a 56-day level still over-forecasts the still-declining `KA_3` store (e.g. DETERGENT 121 predicted vs 71 actual). So the winning-but-honest choice is a short recent window globally, with an extra-short window for the `KA_3` regime (holding the recent level, not extrapolating the decline further — that's my hedge). Let me finalize and generate the real submission.

*(ran a command)*

Strong result — the final model gets mean RMSSE ≈ 0.82–0.83, WAPE ≈ 0.37–0.40 across both backtests, and the `KA_3` over-forecast bias is largely gone (ATTA −4 vs +208 before the fix). The write just failed because the uploads folder is read-only. Let me build this into a proper reproducible repo and write outputs to the right place.

*(used Filesystem integration, ran 7 commands, created 4 files · 4 notes)*

Done. I ran the real investigation on your data rather than writing a plausible-sounding doc, because the rubric explicitly discounts unsupported claims and pays nothing for issues that aren't actually in the data. Everything below is reproducible from `src/audit.py`.

**What the audit actually found**

- `market_signal` is target leakage — same-day per-series correlation with sales is 0.92, dropping to 0.37 when shifted a single day, and it's exactly 0 on 100% of zero-sales days (≈ units × 10 × noise). It also stops at `d_1913`, so it doesn't exist for the horizon. → excluded.
- `vendor_signal` is honest but weak — it covers the horizon but on a backtest its per-series WAPE (1.04) is worse than a trailing-28-day mean (0.82). → not used as the forecast.
- Store `KA_3` is in a real store-wide decline — all six `KA_3` series sit at 0.25–0.49× their prior-year level over the last ~100 days, while the same products in other stores hold ~1.0. → shorter recent window so I don't over-forecast it.
- Price has ≈0 elasticity (drop it); festivals give ~1.3× lift (keep, discounted to 1.15×); Diwali spikes are genuine, not errors (leave alone — the Q3 restraint story).

**The model and how it scores**

A robust, per-series `recent_level × day-of-week profile × festival uplift`. On two honest held-out 28-day windows it gets mean RMSSE ≈ 0.82–0.83, WAPE ≈ 0.37–0.40, and `submission.csv` passes the official `validate_format.py`. The `KA_3` over-forecast bias is largely fixed (ATTA backtest bias went from +208 to −4).

**What you have now**

`retailcast-solution/` written into your project (`src/forecast.py`, `src/audit.py`, `README.md`, `requirements.txt`, `submission.csv`, `approach_summary.md`) — ready to `git init`. Run it with:

```bash
python src/forecast.py --data ../starter-kit/data --out submission.csv
```

Download copies of the three graded artifacts above (the zip is the full runnable repo with data bundled).

**Two things you must still do yourself**

The chat export is a required, heavily-weighted artifact — this conversation is your Phase 1–2 investigation trail, so export it (conversation menu → Export → .md) and submit it; it's what backs every number in the approach doc. And note the approach summary is written in the first person as your decisions — read it, make sure you agree with the `KA_3` call (that's the flagged least-sure decision), and adjust anything you'd have reasoned differently, since the judge cross-checks it against your chat.

One honest caveat: I fixed the `KA_3` window at 28 days and the festival uplift at 1.15 from two backtest windows. Those are defensible but lightly tuned — if you want, I can add a third rolling holdout to confirm they're not overfit before you submit.

*(Claude attached three downloadable artifacts to this turn: the generated `submission.csv`, `approach_summary.md`, and a zip of the full `retailcast-solution/` repo.)*

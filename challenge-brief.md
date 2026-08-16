Challenge: RetailCast India — Forecast the Unforecastable

Overview: Forecast 28 Days of Demand for RetailCast India.

Challenge brief:

The Scenario: You are a data scientist at RetailCast India, a retailer running six product lines across ten stores in Maharashtra, Karnataka, and Tamil Nadu. The merchandising lead, Meera, needs a demand forecast to plan the next four weeks of replenishment. She says:

"I don't need the fanciest model. I've been burned by 'accurate' forecasts that fell apart in production. I need numbers I can actually order stock against. Here's every bit of history and context I could pull together — sales, the calendar, prices, and a market-signal feed a vendor sold us. Give me a 28-day forecast per product per store, and tell me what you trust and what you don't."

You get 1,913 days of daily sales history for 60 product-store series and forecast the next 28 days (d_1914…d_1941). Alongside sales you get the calendar (with Indian festivals), weekly prices, and two vendor feeds — a market-signal feed and a vendor baseline forecast. They are not interchangeable; check each one's coverage and provenance before you trust it.

Here's the thing about real retail data: it's messy, and some of the mess is a trap. A model that maximises fit on the history you can see is not the same as a model that will hold up on the month you can't. Before you reach for the strongest model, interrogate the data like a skeptic — and be careful: not every anomaly needs the same treatment, and not every feed you are handed is safe to use:

Is every feature you were handed something you'll actually have at prediction time — and does it mean what it looks like it means?
Are all 60 series behaving consistently over time, or has something changed for some of them?
Are there values that "help" your model in ways that are too good to be true?
The initial focus should be to find the problems in the data before you trust your own score. "Just build the best model" will most likely walk into the traps.

How You'll Work
This challenge uses Claude Chat for investigation and planning, and Claude Code for building.

Phase 1: Investigate (Claude Chat)
Load the data into Claude and interrogate it. Profile each series. Check the calendar. Look hard at the market-signal feature — where would a value like that come from, and will you have it for the future? Look for series whose behaviour changes partway through the history. Look for prices that don't line up with sales. This investigation conversation is one of your submission artifacts and is a major part of your score — investigate deliberately, don't just ask for a model.

Phase 2: Plan (Claude Chat)
Decide your approach: what to include, what to exclude, how to handle anything you found in Phase 1. Export these conversations.

Phase 3: Build (Claude Code)
Use Claude Code to implement your forecasting pipeline. It should read the data files, produce a submission.csv with your 28-day forecast for all 60 series, and be reproducible (someone can run your repo and get your submission back).

Phase 4: Self-Test, then Submit
Run the format validator in the starter kit(starter_kit/validate_format.py) to validate if your file passes. Then push your code to a Git repo and submit the three artifacts below.

How Your Submission Is Evaluated
Read this carefully — it changes how you should build.

Your forecast is scored against 28 days you will never see. After the round closes, our evaluation agent validates your submission.csv, then scores it against the true units for d_1914…d_1941 using two error metrics: mean RMSSE (a per-series scaled error) and WAPE (volume-weighted percentage error). The agent measures; a Claude-as-Judge then reads your artifacts and assigns your scores.

What this means for how you build:

The best possible honest score is bounded. The future is genuinely noisy; there is a theoretical floor no model can beat. A score that looks impossibly good is treated as an integrity flag, not a win — build honestly.
Fit on visible history ≠ accuracy on the horizon. If some series changed behaviour partway through, a model that averages over all of history will be confidently wrong about their future.
Your reasoning is graded, not just your number. Finding a data problem and saying so — with evidence, in your chat and your write-up — is worth more than silently getting lucky.
Your three submission artifacts:

Repo link — code that reads the data and regenerates your submission.csv. Use this repo as sample repo for your reference: <https://github.com/EliLillyCo/Claude-Olympics-Sample-Repo>
Claude chat export (.md) — your Phase 1–2 investigation. This is the primary evidence of your data judgement.
Approach summary / Technical Decision Log (max 1,500 words) — this document, together with your chat export, is where your data judgement gets graded. Every claim must be traceable to your chat export or your code — unsupported claims are discounted, and issues that don't exist in the data earn nothing. Answer these seven questions:

- Q1. Your audit method (~150 words). Before any findings: how did you interrogate the data? The specific checks you ran (coverage, distributions, per-store/per-series profiling, feed provenance, whatever you chose) and in what order. What made you decide the audit was done? - Q2. Data verdicts (~500 words). Every data issue you found that changed how you modelled. For each, 3-5 lines: What (the exact series, stores, feeds, or weeks — ids and day/week ranges) · Evidence (what you checked and what the data showed) · Action (what you changed in the model) · The reading you rejected (the plausible alternative interpretation of the same evidence, and why you ruled it out). - Q3. What you left alone (~150 words). At least one thing that looked anomalous but that you deliberately did not correct — and why restraint was the right call there. - Q4. Modelling choices (~250 words). What model(s) you used and — more importantly — what you considered and rejected. How did your Q2 verdicts shape the design (features included or excluded, per-series vs pooled treatment, how regime information enters)? - Q5. Validation you trust (~200 words). How did you estimate your real horizon error before submitting? Why is that estimate honest — what could make your local validation look better than reality, and how did you protect against it? State the number you expected. - Q6. Your least-sure call (~150 words). The single decision you'd revisit first with one more day. What evidence would change your mind — and how did you hedge it in the meantime? - Q7. Reproduce and stress (~100 words). The one command that regenerates submission.csv from your repo, plus: if next month's data arrived with a new problem of the same family as something you found, would your pipeline catch it or would you? Be honest.

How your 100 points break down:

| Dimension | Weight | What it rewards |

| Data Judgement | 30 | Finding, reasoning about, and correctly handling the data problems. The heart of the challenge. |

| Forecast Accuracy | 55 | Two error metrics against the held-out horizon, each scored on a published continuous curve (no tier cliffs): RMSSE (36.7 pts) and volume-weighted % error, WAPE (18.3 pts). The curve is deliberately flat across the band where standard automated forecasts land — small accuracy differences there are noise, and points above that band require genuinely better modelling. Curve anchors ship in the starter kit. |

| Process & Communication | 15 | A genuine investigation trail, a clear decision log, and a reproducible repo. |

Good luck, and be a skeptic before you're an optimist.

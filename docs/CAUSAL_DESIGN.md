# Causal Design: from association to impact

This project uses the brief's third option, **"observational analysis with a causal-design proposal."** It estimates associations rigorously (`src/12_media_models.py`) and sets out a stronger design that could be run with the right exposure data. This document records:
- why the observational results cannot identify a causal effect;
- what would be needed for them to do so;
- a ready-to-submit protocol for a randomized framing experiment.

## 1. What the observational evidence can and cannot show

The estimand of interest is the effect on the Michigan Index of Consumer Sentiment (ICS) of exposure to *biased* economic coverage. "Biased" means coverage that deviates from the benchmarks in `docs/CODEBOOK.md` §3. The **monthly time series** faces four threats.

| Threat | Mechanism | What we do about it | Remaining problem |
|---|---|---|---|
| **Common shocks** | An inflation surprise moves both coverage and sentiment. | Condition on real-time macro data. Build "excess negativity" as tone not explained by fundamentals (B4). | Fundamentals we don't measure (e.g., a grocery bill that hits before CPI does) remain in the residual. |
| **Reverse causality, demand side** | Pessimistic audiences click on and seek out negative stories, and publishers supply them. | Granger tests in both directions, placebo *lead* tests, lagged media (t−1). | Forward-looking publishers can anticipate mood, so Granger ordering is not identification. |
| **Same-survey recall** | Michigan's "news heard" is self-reported, and gloomy respondents recall bad news. | Treat it as *recall*, not *exposure*. Compare against independent supply measures (GDELT, headlines). | No item-level exposure data exist. |
| **Partisan confounding** | Party control shifts both outlet framing (slant) and partisan respondents' sentiment. | Post-2025-transition control. Month fixed effects in the slant test. Report Michigan's party breakdown. | No party-by-month microdata in the public files. |

**Conclusion:** the time-series coefficients are **predictive associations**, not causal effects.

## 2. Stronger observational identification (feasible next step)

**Design: an exposure-weighted shift-share across media markets.**

1. **Exposure.** Obtain county-level media-diet data, using either:
   - Nielsen DMA local-TV ratings combined with a cable-news carriage-position instrument (Martin & Yurukoglu 2017); or
   - a panel such as YouGov Pulse or Comscore.
2. **Treatment.** Each market's exposure-weighted excess-negativity index:

   *exposure_mt = Σ_o share_{m,o} × excess_neg_{o,t}*

3. **Outcome.** Market-level sentiment. Michigan's public files do not identify geography below region, so the outcome must come from either:
   - restricted-use Michigan microdata with county identifiers; or
   - a survey with geographic identifiers, such as the Morning Consult daily ICS (state level) or the New York Fed Survey of Consumer Expectations.
4. **Identification.** Within-month variation across markets (month fixed effects absorb national news and national macro data). Channel-position shifts serve as an instrument for exposure shares.
5. **Assumptions.**
   - Channel positions are as good as random with respect to local economic trends.
   - No spillovers across markets (national outlets are common to all markets).
   - Parallel pre-trends: markets with high and low exposure have similar sentiment trends before exposure diverges. Test this with an event-study plot.

## 3. Randomized framing experiment (protocol, ready for IRB)

**Research question.** Holding the facts constant, does a *price-level* or *negative-household* framing of the same official release lower year-ahead expectations and sentiment-style responses, compared with a balanced framing?

| Element | Specification |
|---|---|
| **Population and sample** | US adults, quota-sampled on age, income tercile, region, and party (Prolific or YouGov). N = 2,400: four arms × 600. That gives 80% power to detect 0.16 SD between any two arms at α = 0.05, with a Holm correction across six pairwise contrasts. |
| **Pre-treatment** | Party, the five Michigan ICS questions (baseline), media diet, and price recall ("what did a dozen eggs cost?"). |
| **Arms** (all built from the **same** official facts, e.g., the latest CPI release) | **A. Balanced:** rate *and* level, aggregate *and* household. **B. Rate frame:** "inflation slowed to 2.9%". **C. Level frame:** "prices are 25% higher than in 2020". **D. Negative-household frame:** "families pay $X more per month", using the same numbers. Each arm also gets a placebo variant with partisan attribution (blame on the administration vs none), cross-randomized as a 2×2 inside arms B–D. |
| **Outcomes** (pre-registered) | Primary: (1) the five Michigan ICS questions after treatment, scored with the official formula; (2) year-ahead inflation expectation. Secondary: perceived unemployment trend, and "better/worse off" with reasons. |
| **Manipulation and attention checks** | Factual recall of the release number, so we can show every arm conveyed the same facts. |
| **Analysis** | ANCOVA on the post-treatment ICS with the baseline as covariate. Heterogeneity by party, age, and income, pre-registered. Holm correction across contrasts. Persistence: re-contact after 7 days (sub-sample). |
| **Ethics** | IRB review **before** fielding. Informed consent. Every arm is truthful. A debrief shows all framings and the official source. No deception about facts. No identifiers retained beyond the panel ID. Compensation at platform-recommended rates. |

## 4. From the experimental effect to the national Michigan index (transportability)

An effect estimated in the sample is not an effect on the national ICS. Connecting the two requires four pieces.

1. **Exposure estimates.** The share of US adults exposed to each framing in a given month, and the dose (the number of exposures). These come from a media-diet panel (§2) combined with the content-supply shares measured here (`media_monthly.csv`).
2. **Representative sampling and weighting.** Reweight experimental effects to Michigan's population margins: age × income × region × party. Michigan's microdata (sda.umsurvey.org) supply these margins.
3. **Effect decay.** Use 7-day persistence to convert a single exposure into a monthly level effect.
4. **Transportability assumptions.**
   - **No unmeasured effect modifiers** between the experimental and Michigan populations (S-admissibility).
   - **Comparable outcome measurement** (web self-administered in both cases, so mode effects match).
   - **No interference.** Real-world repetition and social amplification may make field effects larger than lab effects.

The implied contribution to the national index is:

**ΔICS_national,t ≈ Σ_g w_g × Σ_f exposure_{g,f,t} × τ_{g,f} × decay**

Here *g* indexes demographic cells, *f* indexes framings, and τ is the experimental effect. Report it with a bootstrap interval that propagates uncertainty in τ, exposure, and decay.

## 5. Results that would contradict a media-bias explanation (pre-specified)

1. **No excess negativity.** Coverage tone is fully explained by fundamentals, with a symmetric response to good and bad news (B1 p_equal > 0.10 and B4 residual negligible).
2. **No incremental predictive content.** Media measures fail to improve out-of-sample prediction of sentiment or of the gap: the Clark–West test is not significant after Holm correction.
3. **Wrong timing.** Sentiment Granger-causes coverage but not the reverse, and/or *future* coverage "predicts" current sentiment as strongly as past coverage (failed placebo).
4. **Wrong cross-section.** Groups with *less* news exposure show the *same* decline as high-exposure groups. Or the decline lines up with group-specific hardship (prices, housing) after month fixed effects remove all national news.
5. **Partisan pattern dominates.** Sentiment of the out-party collapses and the in-party's rises at presidential transitions, with no matching change in the tone of the outlets each party consumes.
6. **Experimental null.** Truthful reframing of identical facts moves expectations by less than 0.05 SD, ruling out effects large enough to matter at the national level.

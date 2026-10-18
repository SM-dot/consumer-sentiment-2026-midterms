# Requirements map: brief instruction → where it is done

Status key: ✅ done · ◐ done with a stated deviation · ➕ beyond the brief

## Required research questions

| # | Question | Answer (short) | Where |
|---|---|---|---|
| 1 | How can we measure bias in news and social media? | Bias is a deviation from a benchmark: asymmetric response to good vs bad macro news, salience vs the direction of the data, same-month cross-outlet slant, and calibration against official data. Coded with a codebook-driven AI validated on 300 human labels. | Report §5, Tables 5–8; `src/07, 08, 11` |
| 2 | How can we determine the impact of bias on Michigan sentiment? | Associations: out-of-sample model comparison, both-direction tests, placebo leads, local projections. Natural-experiment logic: the 2025 transition. Causal-design proposal and IRB-ready experiment. No causal effect is identified with available data; the aggregate magnitude test rules out media as the source of the national collapse. | §6, §6.1, `docs/CAUSAL_DESIGN.md` |
| 3 | How much do unemployment, inflation and GDP explain? | About 13% of the 2019 → 2025–26 fall (about 29% with the survey-mode offset). | §3, Table 2 |
| 4 | Which perceptual mechanisms can the data measure? | Supply-side negativity and framing (measured). Anchoring and experience effects (proxy; significant). Partisan motivated reasoning (indirect). Availability and confirmation bias in readers (not measurable without exposure data). | §4, §7 |
| 5 | Does media analysis improve predictions beyond economics? | No reliable gain: RMSE rises, while household-pressure controls lower it. | §6, Table 9 |
| 6 | What evidence would contradict a media-bias explanation? | Seven pre-specified tests, with results. | §8, Table 11 |

## 1. Economic and survey baseline

| Instruction | Status | Where |
|---|---|---|
| Monthly data from 2010 plus a pre-election monitoring window | ✅ ➕ 1978–2026 for estimation | `03_build_dataset.py`, panel |
| Michigan headline, Current Conditions (ICC), Expectations (ICE) separated | ✅ | Table 1 (ICC/ICE gaps), `fig_gap_components` |
| BLS U-3, seasonally adjusted | ✅ (validated vs the BLS API) | `DATA_PROVENANCE.md` |
| Headline PCE YoY = 100 × (P / P₋₁₂ − 1) | ✅ ➕ found the supplied column was core PCE | §2, provenance checks |
| Real GDP: q/q SAAR vs y/y distinguished | ✅ both; BIC choice; robustness | §2, robustness paragraph |
| Record observation periods, publication dates, revisions | ✅ | `DATA_PROVENANCE.md`, `gdp_revisions.csv` |
| Use only information available at each date | ✅ real-time vintages, publication lags, shutdown overrides | §2 Timing |
| Do not interpolate GDP or use later releases | ✅ (look-ahead variant shown only as a forbidden contrast) | §2 |
| Economic-only model; gap = observed − out-of-sample prediction | ✅ expanding window | §2, Fig 1 |
| Prediction intervals | ✅ 80% and 95% | Fig 1, Table 1 |
| Alternative controls: real income, cumulative prices, housing affordability, debt service, underutilisation, policy uncertainty | ✅ all six | §3, Table 2; `extended_controls.csv` |
| Explain falling inflation vs elevated prices; aggregate growth vs household experience | ✅ ➕ CPI construction, necessities vs wages, inflation memory | §3 |
| Account for seasonality | ✅ month dummies (insignificant) | §2 robustness |

## 2. Media corpus

| Instruction | Status | Where |
|---|---|---|
| National and local news plus at least one social platform | ✅ Google News (national, wire, business, local), GDELT, Hacker News, Mastodon | §5, Table 5 |
| Search terms, dates, source selection, inclusion criteria | ✅ | `01b_fetch_gnews.py`, `CODEBOOK.md` §0, provenance |
| Headlines vs full articles vs posts vs comments | ✅ `unit` field | Table 5 |
| Geographic relevance, audience | ◐ foreign filter, outlet tiers, AllSides lean; no audience measurement | provenance |
| Duplicates, reposts, ads, automated activity | ✅ flagged and counted | Table 5 |
| Missing data, access restrictions, sampling limits | ✅ (Reddit, X, Bluesky refused; GDELT throttled; Google ranking) | §5, §11 |
| Distinguish supply, engagement, exposure | ✅ | `CODEBOOK.md` §2, §5 |

## 3. AI measurement

| Instruction | Status | Where |
|---|---|---|
| Coding scheme before applying the model | ✅ frozen v1.0 | `docs/CODEBOOK.md` |
| At least four dimensions | ✅ six | Codebook |
| Benchmark for each bias | ✅ | Codebook §3, §5.2 |
| 300 stratified items, two independent annotators | ◐ 300 items, one annotator (only one available) plus a 30-item test–retest; stated deviation | §5.1, Table 6a |
| Agreement and adjudication | ◐ test–retest κ/α; adjudication not applicable with one annotator | Table 6a |
| AI performance by class and by source | ✅ | Table 6; `ai_performance_by_class.csv`; source breakdown in §5.1 |
| Compare with a dictionary or conventional classifier | ✅ both, plus FinBERT and an LLM | Table 6 |
| Preserve model versions, prompts, evidence | ✅ pinned revisions, prompts; ◐ evidence excerpts only for the LLM coder | `outputs/model_versions.json`, `prompts/` |
| Swap political names and source labels | ✅ | Table 7 |
| Text ≠ reader cognitive bias | ✅ stated and respected | §7, Codebook §4 |

## 4. Association and causal impact

| Instruction | Status | Where |
|---|---|---|
| Three models: econ; + media; + household/political | ✅ (+ M3b to isolate media) | Table 9 |
| Chronological holdouts or rolling forecasts | ✅ expanding window from 2020, rolling 36-month coefficients | §6 |
| Accuracy, coefficient stability, uncertainty, sensitivity | ✅ RMSE, Clark–West, Diebold–Mariano, rolling coefficients, 48-variant sensitivity table | §6 |
| Autocorrelation, seasonality, lag selection, multiple testing | ✅ HAC/Driscoll–Kraay, month dummies, BIC lags, Holm/BH | throughout |
| Choose a causal design | ✅ observational + causal-design proposal ➕ IRB-ready experiment protocol | `CAUSAL_DESIGN.md` |
| Reverse causality | ✅ Granger both ways, placebo leads | §6 |
| Sample → national transportability | ✅ | `CAUSAL_DESIGN.md` §4 |

## 5. Pre-election tracking

| Instruction | Status | Where |
|---|---|---|
| Dashboard: sentiment vs prediction with uncertainty, gap, media measures, releases and events, composition, missingness, model performance | ✅ | `dashboard/index.html` |
| Differences by income, age, geography, political affiliation | ✅ age, income, region; ◐ party from Michigan's published reports | §4, §6.1, §9 |
| Survey-method comparability (web transition) | ✅ | §2, §9 |
| Do not attribute changes to election proximity | ✅ | §9 |
| State the cut-off and an update plan | ✅ | §9, dashboard footer |

## Deliverables

| Deliverable | Status |
|---|---|
| 10–12 page report separating findings from hypotheses | ✅ 12 pages; FINDING / HYPOTHESIS labels |
| Reproducible package: provenance, prompts, code, labelling guide | ✅ `run_all.sh` |
| Monitoring dashboard | ✅ |
| 6–8 minute presentation with one practical implication | ✅ 16 slides + 2 extra-clarification slides (answers to the six questions; causal design & limits); implication = decompose sentiment before forecasting spending |

## Beyond the brief (➕)

- **Four data-integrity catches:** core PCE, unpublished Q3 GDP, shutdown gaps, survey mode.
- **Transition natural experiment, plus a robustness test of our own headline result.**
- **Experience-effects (generational scarring) test:** explains 78% of the young's extra decline.
- **Inflation-memory half-life:** a regime-break diagnosis.
- **47-year news-recall test** using Michigan's own questions.
- **Spending-forecast implication** with out-of-sample tests.
- **Relevance precision/recall analysis** and re-runs with an alternative filter.

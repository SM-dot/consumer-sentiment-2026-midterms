# AI, Economic Perceptions, and Consumer Sentiment Ahead of the 2026 Midterms

This is the reproducible analysis package for the final course project (AI Applications in Finance).

- **Cut-off:** 2026-10-16. The October 2026 Michigan reading (46.3) is preliminary.
- **Deliverables:**
  - `report/` — research report (.docx)
  - `presentation/` — summary deck (.pptx)
  - `dashboard/index.html` — monitoring dashboard
  - this package, which covers data provenance, prompts, code, and the human-labeling guide

## Question

Is US consumer sentiment below what the economy predicts? If it is, is the shortfall explained by any of these?
1. Real household pressures that headline indicators miss.
2. Selective or negative media framing and cognitive biases.
3. Measurement, timing, or model problems.

**None of these is assumed.** Each is set up as a hypothesis with a stated test that could reject it.

## Layout

```
data/raw/            untouched downloads (UMich, BLS, BEA, Philadelphia Fed, Freddie Mac, EIA, FHFA, EPU,
                     Google News RSS, GDELT, Hacker News, Mastodon, professor's file)
data/processed/      monthly_panel.csv (real-time information set), corpus.csv, ai_codes.csv, media_monthly.csv
docs/                REQUIREMENTS_MAP.md (brief → where done), CODEBOOK.md (frozen before coding), DATA_PROVENANCE.md, CAUSAL_DESIGN.md
prompts/             llm_coding_prompt_v1.md (optional LLM coder, same codebook)
labeling/            LABELING_GUIDE.md, annotator_A.xlsx, annotator_B.xlsx, practice_20.xlsx, (_key_hidden.csv)
src/                 numbered pipeline (see below); lib.py = shared estimators and tests
outputs/tables, outputs/figures, outputs/model_versions.json
dashboard/index.html
```

| Step | Script | Purpose |
|---|---|---|
| 01 / 01b / 02 | `fetch_gdelt`, `fetch_gnews`, `fetch_social` | Cached, rate-limited corpus collection |
| 03 | `build_dataset` | Real-time monthly panel: publication lags, shutdown overrides, Philadelphia Fed GDP vintages, provenance checks |
| 04 | `baseline_models` | Economic-only model; out-of-sample sentiment gap with 80/95% prediction intervals; decomposition (RQ3); robustness; household-pressure alternatives |
| 05 | `heterogeneity` | Age and income decomposition of the decline; reported hardships; within-month panel with month fixed effects |
| 06 | `build_corpus` | Unified corpus with tiers, lean groups, dedup, ad/bot/foreign flags, keyword topics |
| 07 / 07b | `ai_code`, `llm_code_api` | AI coding per the codebook (local transformers; optional Claude API); name and source swap tests |
| 08 | `factual_calibration` | Numeric claims vs official data public on the publication date |
| 09 / 10 | `labeling_sample`, `validation` | Stratified 300-item human sample; κ / α agreement; AI vs dictionary vs TF-IDF performance |
| 11 | `media_indices` | Monthly supply, engagement, and recall indices; bias benchmarks B1–B4 |
| 12 | `media_models` | Three-model horse race; Clark–West tests; Granger tests both ways; placebo leads; local projections; rolling coefficients |
| 13 | `dashboard` | Rebuilds `dashboard/index.html` |
| 14 / 16 / 17 | `components`, `news_heard_long`, `spending_implication` | Index components and reasons; 47-year news-recall test; sentiment vs spending forecasts |
| 19 | `fresh_angles` | **Transition natural experiment** (does each side's sentiment follow the coverage it reads?) and **inflation-memory** half-life |
| 20 | `experience_cpi` | **Experience-effects (generational scarring) test** by age group with full CPI lifetime histories; necessities vs headline CPI and wages |
| 21 | `relevance_robustness` | Re-runs slant, transition and aggregate-tone results with the keyword-only relevance filter |
| 22 | `region_seasonality` | Decline by Census region; calendar-month (seasonality) test |
| 10b / 10c | `import_app_labels`, `reference_validation` | Import labels from the labelling tool; LLM-reference and human spot-check validation |
| 15 / 18 | `build_report`, `deck_data` | Rebuild the report (.docx) and the deck data; `presentation/build_deck.js` builds the .pptx |

**Reproduce:**
- `bash run_all.sh` for a full refresh.
- `bash run_all.sh --no-fetch` to rebuild from the cached raw data.

Python 3.13; pinned packages are in `requirements.txt`. Model revisions are pinned by commit hash and recorded in `outputs/model_versions.json`.

## Human validation (action needed)

The brief asks for two annotators, but only one is available. The design is therefore **single-annotator with test–retest reliability**:
- One annotator labels the 300 stratified items (relevance and household tone) in the one-tap tool linked in `labeling/LABELING_GUIDE.md`.
- The same annotator re-labels a hidden random 60 later, in a new order.

To finish the validation:
1. Export the labels from the tool.
2. Run `python src/10b_import_app_labels.py`.
3. Run `python src/10_validation.py`.
4. Rebuild the dashboard and report.

No human labels were simulated. The report states this deviation from the brief.

## Key data-integrity findings

1. The professor's "PCE YoY" column is **core PCE**, not headline. It matches BEA DPCCRG exactly. Headline (DPCERG) is used as primary, per the brief.
2. The professor's GDP column contains **2026Q3 = 3.7%**, which BEA had not published by the cut-off. It is excluded. GDP enters as first-print or then-current vintages.
3. **October 2025 U-3 does not exist** (shutdown). Several releases were delayed; see the override table.
4. Michigan's demographic tables are **3-month moving averages**. The monthly archive is used for sentiment by group.
5. **Survey mode changed** (phone to web, April–June 2024). Michigan estimates a level effect of about −6.6 points. It is applied as a sensitivity offset and is never estimated from the gap period.

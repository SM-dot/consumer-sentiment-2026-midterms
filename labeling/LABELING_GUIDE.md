# Human Labeling Guide (single annotator)

*Simplified 2026-10-16. Only one annotator is available, so the brief's two-annotator design is replaced by test–retest reliability. This deviation is stated in the report.*

**Tool:** https://claude.ai/artifact/UJUGqFM2PWP4MwN6u5vHz7. Answers save automatically, and Claude reads them directly.

**Task:** for each item, one tap:

| Choice | When to use it |
|---|---|
| **Not about the US economy** | Another country's economy, ads, sports, spam, unrelated topics |
| **Negative** | Bad news for ordinary US households: "Layoffs surge", "Grocery prices skyrocket", "Mortgage rates climb" |
| **Neutral** | "Fed holds rates steady", "What the CPI report means for you", or anything mixed or unclear |
| **Positive** | Good news: "Inflation cools to 2.4%", "Economy adds 300,000 jobs", "Gas prices fall" |

Judge the text as written, and do not look anything up. Your own politics should not affect the answer.

**Order:**
1. 20 practice items.
2. The main 300.
3. **Later, ideally the next day:** the Re-check 60. It repeats some of the items in a new order, to measure your consistency. Do not look back at your earlier answers.

**After labeling:**
1. Claude exports the stored labels.
2. `python src/10b_import_app_labels.py`
3. `python src/10_validation.py`

The validation step computes intra-rater κ and α, and scores the AI coder, FinBERT, the dictionary, and a TF-IDF classifier against your labels.

The original two-annotator, nine-field design is described in `docs/CODEBOOK.md`; `practice_20.xlsx` remains as an offline fallback.

**Ethics:** public headlines and posts only, with authors pseudonymised. No human-subject research is involved.

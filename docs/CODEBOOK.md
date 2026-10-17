# Coding Scheme for Economic Media Content (v1.0)

*Frozen 2026-10-16, before any model was applied to the corpus. Changes after this date go in a new version, with a changelog entry at the bottom.*

The codebook serves three groups:
1. The two human annotators (see `labeling/LABELING_GUIDE.md`, which repeats these rules with worked examples).
2. The automated coders: the local transformer pipeline and the optional LLM prompt in `prompts/`.
3. Anyone checking whether a "bias" claim follows from the measurements.

## 0. Unit of analysis and eligibility

| Field | Definition |
|---|---|
| **Unit** | One *item*: a news **headline** (GDELT article list), a Hacker News **story title** or **comment**, or a Mastodon **post**. Full article text is **not** coded. GDELT supplies a full-text dictionary tone, which we keep as a separate variable. |
| **Eligible** | The item refers to **US economic conditions as experienced or forecast**: prices, jobs, income, growth, recession, housing costs, interest rates, trade or tariffs as they affect the US economy, or the stock market as a signal of the economy. |
| **Not eligible** | Pure company news with no macro or household angle, foreign economies only, sports or entertainment that use economic words ("inflation of egos"), advertisements and coupons, and spam. Code `relevant = 0` and stop. |

## 1. Dimensions (minimum four required; we code six)

### D1. Tone (valence about the economy). Labels: `negative`, `neutral`, `positive`
- Tone is the valence of the **economic situation described**, from the perspective of US households.
- "Inflation cools to 2.4%" is **positive**. "Layoffs surge" is **negative**. "Fed holds rates steady" is **neutral**.
- Mixed or ambiguous items are coded **neutral**.
- Tone is **not** about whether the coder agrees with the item.

### D1b. Emotional wording. Labels: `0` none, `1` some, `2` strong
- This separates **factual description** from **emotional language**, independent of tone.
- Code `1` or `2` when valence is carried by loaded words beyond what the facts need: *soaring, skyrocketing, crushing, brutal, slams, plunges, nightmare, catastrophe, bloodbath, boom, roaring*.
- "CPI rises 0.4%" scores `0`. "Prices skyrocket as families are crushed" scores `2`.

### D2. Selection and salience. Field: `topic`, a single primary topic
| Label | Covers |
|---|---|
| `prices_rising` | Inflation, cost of living, or a specific price rising or high |
| `inflation_falling` | Disinflation, prices falling, inflation cooling |
| `layoffs` | Job cuts, unemployment rising, firings |
| `hiring` | Job gains, low unemployment, wage gains |
| `growth` | GDP, spending, output, positive or neutral |
| `recession_risk` | Recession, downturn, slowdown warnings |
| `housing_rates` | Mortgage rates, rents, home prices, affordability, interest rates on households |
| `trade_tariffs` | Tariffs or trade policy |
| `markets` | Stocks or bonds as economic signals |
| `policy_fed` | Fed, fiscal, or regulatory policy not otherwise classified |
| `other` | Eligible, but none of the above |

Salience is measured at the **aggregate** level as each topic's share of eligible items per month (*content supply*).

### D3. Framing (three sub-codes)
| Sub-code | Labels | Rule |
|---|---|---|
| `price_frame` | `level`, `rate`, `both`, `none` | **Level**: "eggs cost $6", "prices are 25% higher than 2020", "unaffordable". **Rate**: "inflation 2.9%", "prices rose 0.3% last month". |
| `unit_frame` | `aggregate`, `household`, `both`, `none` | **Aggregate**: national statistics, "the economy". **Household**: families, shoppers, workers, personal finances, anecdotes. |
| `time_frame` | `current`, `forecast`, `past`, `none` | **Forecast**: "could", "will", "economists expect", "risk of". |

### D4. Factual calibration. Fields: `numeric_claim`, `indicator`, `value`, `reference_period`
- Applies only to items that state a **number about an official indicator**: CPI, PCE, unemployment, payrolls, GDP, or mortgage rate.
- Extract the indicator, the stated value, and the reference period.
- `src/08_factual_calibration.py` compares the claim with the **official value public on the item's date**, using real-time vintages where available.
- **Calibrated**: absolute error ≤ the indicator's rounding tolerance (0.1 pp for rates, 10% for payroll levels).
- **Definition error**: the right number but the wrong measure, for example a core figure reported as headline, or month-over-month presented as annual.
- **Uncalibrated**: neither of the above.
- Forecasts and opinions are **not** checked.

### D5. Political attribution. Fields: `attr_target`, `attr_direction`, `party_named`
| Field | Labels |
|---|---|
| `attr_target` | `none`, `president_admin`, `congress`, `fed`, `business`, `foreign`, `other` |
| `attr_direction` | `credit`, `blame`, `none` |
| `party_named` | `D`, `R`, `both`, `none`. Includes named politicians: Biden or Harris count as D, Trump as R. |

**Criticism is not bias.** Attribution is recorded descriptively. Slant is defined only against a **benchmark**: the same economic facts receiving different attribution depending on which party holds office. See §3.

## 2. Measurement levels (supply vs engagement vs exposure)

| Concept | Measure in this project | What it can **not** show |
|---|---|---|
| **Content supply** | Article counts and topic shares (GDELT), and headline codes | Whether anyone read it |
| **Engagement** | HN points and comments; Mastodon favourites and boosts | Whether survey respondents saw it, or why people engaged |
| **Exposure / recall** | Michigan "news heard" questions (Tables 23–24) | Causal effect, because respondents in a bad mood may recall bad news (same-survey reverse causality) |

## 3. Bias benchmarks

Bias is always a **deviation from a stated benchmark**, never just "negative".

| Candidate bias | Benchmark | Statistic |
|---|---|---|
| **Negativity in coverage supply** | Same-size positive vs negative surprises in official data | Asymmetry ratio: tone response to bad news ÷ tone response to good news (Soroka-style asymmetric regression) |
| **Selective salience** | Actual direction of the indicator | Share of inflation coverage that is "prices rising" in months when measured inflation is **falling** |
| **Level-vs-rate framing** | None, so this is reported descriptively | `price_frame = level` share over time (relevant because households may anchor on past prices) |
| **Partisan slant** | Same outlet under presidents of each party, conditioning on the macro data | Diff-in-diff: (right-leaning − left-leaning tone) under Trump minus the same under Biden, given U-3, inflation, and growth |
| **Factual calibration** | Official real-time data | Calibration rate and the sign of errors (do errors systematically exaggerate bad news?) |

## 4. What text measures can and cannot establish

Text establishes **framing and selective coverage in the supply of content**. It cannot establish a *reader's* cognitive bias.

- **Availability bias**: needs exposure **and** recall evidence. Michigan's "news heard" is recall without verified exposure.
- **Confirmation bias**: needs belief data by prior (e.g., party) plus exposure. We have party-level sentiment only from Michigan reports, not microdata.
- **Negativity bias**: needs an asymmetric response to equal good and bad news. This is testable at the aggregate level in respondents' sentiment.
- **Anchoring to past prices**: needs price-level perceptions. Proxies are the Michigan "worse off: higher prices" mentions and the cumulative-inflation variables.

## Changelog
- v1.0 (2026-10-16): initial frozen version.

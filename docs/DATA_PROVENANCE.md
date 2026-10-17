# Data provenance, timing, and revisions

**Data cut-off:** 2026-10-16. October 2026 Michigan data are **preliminary**.

All raw files are kept unmodified under `data/raw/`. Scripts never edit raw files; they write to `data/processed/` and `outputs/`.

## 1. Economic and survey series

| Measure | Source (retrieved 2026-10-16) | Raw file | Frequency | Treatment |
|---|---|---|---|---|
| **Michigan ICS, ICC, ICE**; sub-indices by age, income tercile, and region; news heard; reasons; expectations | University of Michigan Surveys of Consumers. Data archive (all tables, monthly): `https://data.sca.isr.umich.edu/data-archive/mine.php`. Headline: `https://www.sca.isr.umich.edu/files/tbmics.csv` | `umich/all_tables.raw`, `umich/tbmics.csv` | Monthly | As published. ICC and ICE kept separate. |
| Michigan demographic tables (age, income) | `https://data.sca.isr.umich.edu/demographic-tables.php` | `umich/demo/*.xls` | **3-month moving averages** (verified: the 18–34 ICS in the table equals the mean of three monthly archive values) | Used only for group hardship profiles. The monthly archive series is used for sentiment by group. |
| Michigan methodology and partisanship reports | `methodtransitionannouncement2024.pdf`, `partisaneconomy202504.pdf`, `partisaneconomy202607_revised.pdf` | `umich/` | Reports | Documented web transition (Apr–Jun 2024). Partisan figures quoted. |
| **U-3 unemployment (SA)** | Professor file. Validated against BLS API `LNS14000000` (max abs. diff = 0.000 over 320 months). | `professor_Perceptual_Bias_Data.xlsx`, `bls/*.json` | Monthly | October 2025 is missing (no household survey during the shutdown). |
| **PCE price index, headline** | BEA NIPA flat file `NipaDataM.txt`, series `DPCERG` (Table 2.8.4). `https://apps.bea.gov/national/Release/TXT/` | `bea/` | Monthly | YoY = 100 × (P_t / P_{t-12} − 1). |
| Core PCE price index | BEA `DPCCRG` | `bea/` | Monthly | **The professor's "PCE YoY" column equals core PCE** (max abs. diff 0.00001 over 584 months vs DPCCRG; up to 2.25 pp vs headline). The brief asks for headline, so headline is primary and core is a robustness check. |
| **Real GDP growth, current vintage** | BEA `A191RL` (q/q SAAR) | `bea/NipaDataQ.txt` | Quarterly | Used only for revision analysis. |
| **Real GDP, real-time vintages** | Philadelphia Fed Real-Time Data Set, `routputMvQd.xlsx` (monthly vintages of quarterly real GDP levels) | `philly/` | Quarterly, vintage-dated monthly | For survey month *t*, the vintage dated *t* gives the latest published quarter. Growth is computed **within that vintage**, both q/q SAAR and y/y. Never interpolated to months. |
| Professor's GDP column | Professor file | | Quarterly | Max abs. diff 1.1 pp from the current BEA vintage and up to 9.1 pp from first releases (2020), so it is **not** real-time. It also contains **2026Q3 = 3.7%**, which BEA had **not published** as of the cut-off (the advance estimate is due in late October 2026). It is therefore excluded from the information set. |
| U-6, CPI (SA and NSA), core CPI, food at home, shelter, gasoline CPI, average hourly earnings, payrolls | BLS Public API v1 | `bls/*.json` | Monthly | Controls and factual calibration. |
| Real disposable income per capita, saving rate, personal interest payments, DPI | BEA `A229RX`, `A072RC`, `B069RC`, `A067RC`, `A229RC` | `bea/` | Monthly | Controls. |
| 30-year mortgage rate | Freddie Mac PMMS history CSV | `other/pmms.csv` | Weekly → monthly mean | Control. |
| Retail gasoline price | EIA `EMM_EPM0_PTE_NUS_DPG` (monthly) | `other/gas.xls` | Monthly | Deflated by CPI. |
| House prices | FHFA HPI master (purchase-only, US, SA) | `other/hpi.csv` | Monthly | Affordability index. |
| Economic policy uncertainty | Baker–Bloom–Davis, news-based index | `other/epu.xlsx` | Monthly | Control. **This index is itself built from newspaper text** (see the report discussion). |

FRED and ALFRED returned empty responses to scripted requests from the build machine. All series were therefore taken from their **primary publishers**.

## 2. Real-time information set ("use only information available by each prediction date")

**Survey timing.** Michigan's interviews run from about the last week of month *t*−1 to about the 20th of month *t*. The preliminary release comes about the second Friday of month *t*. The information set is defined as **data public by about the 15th of month *t***.

| Variable | Lag used | Why |
|---|---|---|
| U-3, U-6, CPI-based series | t−1 | Employment Situation comes out on the first Friday; CPI around the 10th–15th. |
| PCE, income, saving rate, interest burden | t−2 | Personal Income & Outlays comes out in the last week of t−1. |
| GDP | Philadelphia Fed vintage dated *t* | The latest published quarter, as it was then estimated. |
| Mortgage rate, gasoline | t (monthly mean) | Weekly and daily data, available in real time. |
| EPU | t−1 | |

**2025 shutdown overrides** (`SHUTDOWN_OVERRIDES` in `src/03_build_dataset.py`):
- BLS published no October 2025 household survey. The September 2025 report came out on 2025-11-20, and the November report on 2025-12-16.
- BEA released September 2025 personal income on 2025-12-05, and October and November combined on 2026-01-22.

Survey months October 2025 through February 2026 therefore carry the most recent data **actually** public at the time, not the usual lag. These dates come from BLS and BEA announcements, as reported in press coverage. Verify them against the BEA release archive before reusing them.

**Revisions.**
- `data/processed/gdp_revisions.csv` lists, for every quarter, the first-release vs current-vintage q/q SAAR.
- Robustness table `robustness_gap.csv` compares real-time vs ex-post data. It also includes a deliberately **forbidden** look-ahead variant (current-vintage GDP of the same quarter) to show how much the brief's timing rule matters.

## 3. Media corpus

| Component | Source | Unit | Coverage | Access notes |
|---|---|---|---|---|
| News headlines (topic queries) | Google News RSS search, US edition. Nine fixed topic queries × month. | Headline + outlet + date | 2017-01 to 2026-10 | Ranked by Google's relevance algorithm (not a random sample). Includes non-news publishers, tagged `other_institutional`. |
| News headlines (outlet queries) | Google News RSS, `site:` queries for 14 national outlets × month | Headline | 2017-01 to 2026-10 | Same query for every outlet in every month, enabling the same-period cross-source comparison. |
| News headlines (GDELT) | GDELT DOC 2.0 `artlist` | Headline | 2017-01 and 2017-02 only | GDELT throttled this IP (see `data/raw/gdelt/fetch.log`), so the list sampling moved to Google News. |
| News volume and tone, full population | GDELT DOC 2.0 `timelinevolraw` / `timelinetone`, `sourcecountry:US sourcelang:english` | Daily counts and average full-text tone | 2017-01 to 2026-10 | GDELT tone is a **dictionary** score on full text. It serves as the conventional-baseline series. |
| Social: Hacker News | Algolia HN Search API | Story titles + comments | 2010-01 to 2026-10 | Monthly hit counts for 10 queries; ≤ 12 sampled items per query × type × month. **Audience skews tech, young, high-income, and male. Not representative.** |
| Social: Mastodon | mastodon.social public hashtag timelines | Posts | About Sep 2024 – Oct 2026 (2,400 most recent per tag) | Recent window only. About 55% of posts come from automated or feed-relay accounts (flagged). |
| Social: Reddit, Bluesky, X | — | — | — | Refused unauthenticated access (HTTP 403 or rate-limit page). Claims about these platforms are **not** made. |
| **Exposure / recall** | Michigan Tables 23–24 ("heard favorable/unfavorable news") | Survey % | 1978–2026 | Self-reported recall from the same respondents (see the reverse-causality caveat). |

**Deduplication.**
- `dup_exact` flags any item whose normalized text was already seen: wire syndication, reposts, and cross-posts.
- About 60% of local-news headlines in the GDELT sample were syndicated duplicates.

**Ads and spam.** These are flagged by pattern (`ad_flag`).

**Automated activity.**
- **Mastodon:** an item is flagged as automated if any of these holds: the account is declared a bot; it posted more than 50 times in the sample; or it has more than 100k lifetime statuses (feed relays).
- **Hacker News:** no bot signal is available.

**Geography.**
- Headlines mentioning only foreign economies are flagged `foreign_flag` and excluded.
- Local or regional outlets are tagged by tier. National outlets carry a lean group from AllSides ratings. These ratings are used only to group outlets, never as article-level truth.

**Supply vs engagement vs exposure.** Headline counts and shares measure **supply**. HN points and comments, and Mastodon favourites and boosts, measure **engagement**. Only Michigan's news-heard items speak to **exposure**, and even those measure recall.

## 4. Privacy and licensing

- Only headlines, public posts, and public statistics are used.
- Social-media authors are stored as truncated SHA-256 hashes; handles are never stored.
- Full article text is not stored.
- Headlines are short factual titles used for non-commercial research.
- No human-subject data are collected.
- The proposed experiment (`docs/CAUSAL_DESIGN.md`) requires IRB approval before fielding.

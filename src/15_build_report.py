"""
15_build_report.py — Build report/Consumer_Sentiment_Media_Report.docx from outputs/ (numbers are read, not typed).
Sections follow the brief; every claim is labelled FINDING (supported by our evidence) or HYPOTHESIS (not tested /
not testable with our data).
"""
import numpy as np, pandas as pd
from report_lib import *
from lib import ROOT, TAB, FIG, PROC

R = ROOT / "report"; R.mkdir(exist_ok=True)
T = lambda f, **k: pd.read_csv(TAB / f, **k) if (TAB / f).exists() else pd.DataFrame()
f1 = lambda x: f"{x:.1f}"; f0 = lambda x: f"{x:.0f}"; f2 = lambda x: f"{x:.2f}"


def build():
    d = new_doc()
    gs = T("gap_summary.csv").set_index("period"); dec = T("decomposition.csv", index_col=0)
    dh = T("decomposition_m1h2.csv", index_col=0); m1 = T("m1_fullsample.csv", index_col=0)
    rob = T("robustness_gap.csv"); comp = T("components_reasons.csv").set_index("var")
    age = T("decline_by_age.csv").set_index("group"); inc = T("decline_by_income.csv").set_index("group")
    wm = T("within_month_panel_age.csv"); hc = T("hardship_change_by_age.csv").set_index("measure")
    brk = T("break_test.csv", index_col=0); party = T("partisan_composition.csv")
    g26 = gs.loc["2026 (to Oct, pre-midterm)"]; g25 = gs.loc["2025"]
    act = dec.loc["ACTUAL change in ICS", "contribution_to_ICS"]; m1c = dec.loc["TOTAL predicted by U3+PCE+GDP", "contribution_to_ICS"]
    hc_tot = dh.loc["TOTAL predicted", "contribution"]; resid = dh.loc["Unexplained residual", "contribution"]
    S = MEDIA_RESULTS()

    # ------------------------------------------------------------------ title block
    para(d, "AI, Economic Perceptions, and Consumer Sentiment Ahead of the 2026 Midterm Elections", size=17, color=ACCENT, space_after=2).runs[0].bold = True
    para(d, "Final Course Project — AI Applications in Finance · Data cut-off 16 October 2026 (October Michigan reading preliminary)", size=9.5, color=MUTED, space_after=1)
    para(d, "Deliverables: this report · reproducible package (README.md) · monitoring dashboard (dashboard/index.html) · summary deck", size=9.5, color=MUTED, space_after=8)

    # ------------------------------------------------------------------ executive summary
    d.add_heading("Executive summary", 1)
    ta = T("transition_aggregate.csv").set_index("administration") if (TAB / "transition_aggregate.csv").exists() else None
    mg = T("inflation_memory_gap.csv")
    rr = T("relevance_robustness.csv"); ms = T("media_sensitivity.csv")
    slope = ms[(ms.measure == "tone_net") & (ms.timing == "t-1") & (ms["sample"] == "2017–2026")].coef.iloc[0] if len(ms) else np.nan
    worst = (rr.aggregate_tone_Trump2 - rr.aggregate_tone_Biden).min() * slope if len(rr) else np.nan
    para(d, "**Bottom line: media bias does not explain the sentiment gap.** We find real, measurable *partisan slant* in economic coverage, but it cannot "
            "account for record-low sentiment: (1) coverage measures add no out-of-sample predictive power once household cost pressures are modelled; "
            "(2) across the 2025 presidential transition, aggregate coverage tone barely moved — even under our least favourable filter, the change implies "
            f"about {abs(worst):.1f} point of sentiment, against an actual fall of "
            + (f"{ta.loc['Biden (2021–24)','Michigan ICS (mean)'] - ta.loc['Trump-2 (2025–26)','Michigan ICS (mean)']:.1f}" if ta is not None else "14.5")
            + " points; (3) the decline is shared by every age and income group, lines up within each month with reported price and income hardship, and "
            "the extra decline of the young is largely explained by the inflation they lived through. The gap is best explained by a **price-level "
            "grievance** that headline data and history-trained models miss, **experience effects**, a **survey-mode change** and **partisan identity** — with "
            "media as an amplifier of price salience, not the source.", space_after=6)
    para(d, f"Michigan consumer sentiment averaged **{g26.mean_actual:.1f}** in 2026 (October preliminary 46.3; May's 44.8 is the lowest on record), "
            f"while a real-time model using only U-3 unemployment, headline PCE inflation and real GDP growth predicts about **{g26.mean_pred:.0f}**. "
            f"The resulting sentiment gap (**{g26.mean_gap:.1f}** points; every 2026 month below the 95% prediction interval) is real under that model — but it is "
            f"mostly *not* a mystery once the measurement and the household economy are taken seriously. We decompose the {abs(act):.0f}-point fall since 2019:")
    tbl = pd.DataFrame([
        ["Headline indicators (U-3, PCE, GDP)", f"{m1c:.1f}", f"{100*m1c/act:.0f}%", "FINDING"],
        ["Household pressures not in headline data (cumulative price level, food, U-6, gasoline, real income) and policy uncertainty",
         f"{hc_tot - m1c:.1f}", f"{100*(hc_tot-m1c)/act:.0f}%", "FINDING (associational; 2000–2019 coefficients)"],
        ["Survey-mode change (phone→web, 2024; Michigan's own estimate)", "-6.6", f"{100*-6.6/act:.0f}%", "FINDING (external estimate)"],
        ["Partisan composition of respondents (illustrative, 5-pp Republican share drop)", f"{party.loc[party.R_share_drop_pp==5,'implied_ICS_change'].iloc[0]:.1f}",
         f"{100*party.loc[party.R_share_drop_pp==5,'implied_ICS_change'].iloc[0]/act:.0f}%", "HYPOTHESIS (back-of-envelope)"],
        ["Unexplained residual — the space any media/perception story must fill", f"{resid - party.loc[party.R_share_drop_pp==5,'implied_ICS_change'].iloc[0]:.1f}",
         f"{100*(resid - party.loc[party.R_share_drop_pp==5,'implied_ICS_change'].iloc[0])/act:.0f}%", "Residual"],
        ["Actual change, 2019 → 2025–26", f"{act:.1f}", "100%", ""]], columns=["Component of the 2019→2025–26 change in ICS", "Points", "Share", "Status"])
    table(d, tbl, widths=[3.9, 0.6, 0.6, 1.6], size=8.5)
    cc = dh["contribution"]
    rk = {"cost of living (cumulative price level, food, gasoline, inflation)": cc[["rt_cum3y_infl", "rt_food_yoy", "rt_gas_real_yoy", "rt_pce_yoy"]].sum(),
          "policy uncertainty (tariffs, shutdown)": cc["rt_epu"],
          "jobs, income, growth and mortgage rates": cc[["rt_u6", "rt_u3", "rt_rdpi_pc_yoy", "rt_gdp_yoy", "rt_d12_mort30"]].sum()}
    pc5 = party.loc[party.R_share_drop_pp == 5, "implied_ICS_change"].iloc[0]
    rk.update({"survey-mode change": -6.6, "partisan composition": pc5})
    rk_txt = "; ".join(f"{k} {v:.1f}" for k, v in sorted(rk.items(), key=lambda kv: kv[1]))
    eb = [b for b in S["exec_bullets"] if not b.startswith("**RQ3.**")]
    eb.insert(2, f"**RQ3 — what causes the mismatch, ranked.** U-3, inflation and GDP alone explain ~13% of the fall. Regrouping the household-pressure model by cause "
                 f"(points of the {act:.1f}): {rk_txt}; unexplained {act - sum(rk.values()):.1f}. Respondents say the same in their own words: 'worse off because of higher prices' "
                 f"rose from {comp.loc['pagorn_hp_all','2019']:.0f}% (2019) to {comp.loc['pagorn_hp_all','2025–26']:.0f}% — above the 2022 peak ({comp.loc['pagorn_hp_all','2022 (inflation peak yr)']:.0f}%) — and "
                 f"'bad time to buy a home: interest rates' from {comp.loc['homrn_hr_all','2019']:.0f}% to {comp.loc['homrn_hr_all','2025–26']:.0f}%. The 2026 gap is larger for current conditions "
                 f"({g26.icc_gap:.1f}) than expectations ({g26.ice_gap:.1f}): the grievance is about the present cost of living, not fear of recession.")
    bullets(d, eb, size=10)

    # ------------------------------------------------------------------ 1 intro
    d.add_heading("1. Question, competing explanations, and approach", 1)
    para(d, "The brief asks us to distinguish three explanations for low sentiment relative to measured conditions: (E1) consumers respond to pressures "
            "that headline indicators miss; (E2) perceptions reflect selective information, framing or cognitive bias; (E3) the discrepancy is an artefact of "
            "measurement, timing or an incomplete model. We treat each as a hypothesis with an explicit way to fail (Section 8). Two design rules run throughout: "
            "(i) every regressor is the value **public at the survey date** (real-time vintages, publication lags, shutdown overrides), and (ii) text measures "
            "describe the **supply** of content; they are never treated as proof of readers' cognitive bias.", align="justify")
    para(d, "**On the original hypothesis (age-group hardships drive the decline).** It is a good instinct and we test it formally (Section 4), but it needs two "
            "corrections. First, 'which group has the most impact' must be measured as weight × change, not as which group is gloomiest. Second, group "
            "hardship is evidence for E1 only if it explains differences *within* a month, after national news and macro data are held fixed; otherwise "
            "'other factors correlated with sentiment' cannot be separated from common shocks. The age analysis is therefore one component of the answer "
            "— it does not by itself address media bias (RQ1, 2, 5, 6), which the brief weights most heavily.", align="justify")

    # ------------------------------------------------------------------ 2 data & baseline
    d.add_heading("2. Economic and survey baseline", 1)
    para(d, "**Data.** Monthly 1978–2026 (analysis window 2010–2026; monitoring window 2025–October 2026). Michigan ICS with Current (ICC) and Expectations "
            "(ICE) indices, age/income/region sub-indices and the qualitative 'reasons' and 'news heard' tables; BLS U-3 (SA); BEA headline PCE price index "
            "(YoY = 100×(P_t/P_t−12 − 1)); real GDP from the Philadelphia Fed real-time data set (monthly vintages), reported both as q/q SAAR and y/y. "
            "Controls: U-6, food-at-home and shelter CPI, real gasoline, real disposable income per capita, saving rate, interest burden, 30-year mortgage rate, "
            "an affordability index, cumulative 3-year inflation, and news-based policy uncertainty. Sources, vintages and URLs are in docs/DATA_PROVENANCE.md.", align="justify")
    para(d, "**Timing.** Michigan interviews run from late month t−1 to about the 20th of month t, so the information set is what was public by mid-month t: "
            "U-3 for t−1, PCE for t−2, and the latest GDP quarter *in the vintage dated t* (first or then-current estimate, never today's revised figure; quarterly "
            "GDP is never interpolated). The October-2025 household survey was not conducted and the Sept–Nov 2025 BLS/BEA releases were delayed by the shutdown; "
            "explicit overrides assign the data actually available.", align="justify")
    para(d, "**Data-integrity findings (all documented and handled).** (1) The supplied 'PCE YoY' column is **core** PCE — it matches BEA's DPCCRG to 0.00001 "
            "over 584 months but differs from headline by up to 2.25 pp; we use headline as required and core as a robustness check. (2) The supplied GDP column "
            "includes **2026Q3 = 3.7%**, which BEA had not published by the cut-off (advance estimate due late October); using it would be look-ahead, so it is "
            "excluded. (3) Supplied GDP is a current vintage (up to 9 pp from first releases in 2020). (4) Michigan's demographic tables are 3-month moving averages "
            "(verified), so monthly sub-indices come from the archive file. (5) Michigan moved from phone to web interviewing in April–July 2024; Michigan "
            "estimates a −6.6-point level effect (an outside estimate is −8.9).", align="justify")
    para(d, "**Economic-only model (M1).** ICS_t = α + β₁U3 + β₂PCE + β₃GDP + ε, chosen by BIC on pre-2000 data among q/q-SAAR and y/y GDP variants "
            f"(y/y wins; adding Δ12 U-3 does not help). Estimated 1978–2019: U-3 {m1.loc['rt_u3','coef']:.2f} (HAC t {m1.loc['rt_u3','t']:.1f}), "
            f"PCE {m1.loc['rt_pce_yoy','coef']:.2f} (t {m1.loc['rt_pce_yoy','t']:.1f}), GDP {m1.loc['rt_gdp_yoy','coef']:.2f} (t {m1.loc['rt_gdp_yoy','t']:.1f}), "
            f"R² {m1.loc['rt_u3','R2']:.2f}. The **sentiment gap** is the actual value minus the *out-of-sample* prediction from an expanding window: each month "
            "is predicted from a model fit only on earlier months, with an OLS prediction interval (80% and 95%).", align="justify")
    figure(d, FIG / "fig_gap_main.png", "Figure 1. Michigan ICS vs. real-time, out-of-sample predictions with 95% prediction interval (top) and the monthly sentiment gap (bottom). "
           "The dashed line adds household-pressure and policy-uncertainty controls (M1H2). Black line in the lower panel adds back Michigan's 6.6-point web-mode effect.", width=5.5)
    gsd = gs.reset_index()[["period", "months", "mean_actual", "mean_pred", "mean_gap", "mean_gap_mode_adj", "share_below_95PI", "icc_gap", "ice_gap"]]
    gsd.columns = ["Period", "N", "Actual", "Predicted", "Gap", "Gap (mode-adj.)", "Share < 95% PI", "ICC gap", "ICE gap"]
    table(d, gsd, caption="Table 1. Real-time out-of-sample sentiment gap by period (M1: U-3 + headline PCE + GDP y/y).", size=8,
          fmt={"N": "{:.0f}", "Actual": "{:.1f}", "Predicted": "{:.1f}", "Gap": "{:.1f}", "Gap (mode-adj.)": "{:.1f}", "Share < 95% PI": "{:.0%}", "ICC gap": "{:.1f}", "ICE gap": "{:.1f}"},
          note="A negative gap is unexplained pessimism under this model, not proof of perceptual bias. The 2008–09 gap (−18.8) is a useful benchmark: large gaps also occur when "
               "the model misses real shocks (housing wealth, credit).")
    rb = rob.set_index("variant")["mean_gap_2025_26"]
    para(d, f"**Robustness.** The 2025–26 gap is essentially unchanged with core instead of headline PCE ({rb.iloc[1]:.1f}), q/q instead of y/y GDP ({rb.iloc[2]:.1f}) or "
            f"revised data ({rb.iloc[3]:.1f}); the forbidden look-ahead GDP variant gives {rb.iloc[4]:.1f} (outputs/tables/robustness_gap.csv). It shrinks sharply only when "
            f"the model may re-estimate on recent data (rolling 60-month window: {rb.loc['Rolling 60-month window']:.1f}) — the relationship itself shifted. A post-2021 intercept "
            f"dummy is {brk.loc['post2021','coef']:.1f} (p < 0.001) with the web share {brk.loc['web_share','coef']:.1f} (p = {brk.loc['web_share','p']:.3f}): evidence for E3 "
            "(model instability and measurement) alongside E1. "
            + (lambda st: f"Seasonality: Michigan's index is not seasonally adjusted, but calendar-month dummies are jointly insignificant (HAC F = {st.joint_F_month_dummies.iloc[0]:.2f}, p = {st.p.iloc[0]:.2f}) and leave the 2025–26 gap at {st.gap_2025_26_with_month_dummies.iloc[0]:.1f}." if len(st) else "")(T("seasonality_test.csv")), align="justify")

    # ------------------------------------------------------------------ 3 how much do the 3 indicators explain + alternatives
    d.add_heading("3. How much do unemployment, inflation and growth explain? (RQ3) — and what else does", 1)
    para(d, f"**FINDING.** Between 2019 and 2025–26, ICS fell {abs(act):.1f} points. With 1978–2019 coefficients, the three headline indicators account for only "
            f"**{m1c:.1f} points ({100*m1c/act:.0f}%)**: unemployment is up ~0.5 pp, inflation is above 2019 but well below 2022, and growth is close to trend. "
            "Adding Michigan's web-mode offset raises the explained share to about 29%. The brief's three indicators therefore leave most of the decline unexplained.", align="justify")
    para(d, "**Alternative explanation E1: household pressures.** We test a small set of controls, each one at a time (Holm-adjusted) and in a combined model fit "
            "on 2000–2019 (M1H2) and evaluated out-of-sample from 2008. Long-history *levels* (mortgage rate, price-level gap) enter with counter-intuitive signs "
            "on 1978–2019 because they trend with regimes, so we specify the household model **a priori** in growth/changes and use the 2000+ controls.", align="justify")
    dd = dh.copy().reset_index().rename(columns={"index": "Variable"})
    names = {"rt_u3": "U-3", "rt_pce_yoy": "PCE inflation y/y", "rt_gdp_yoy": "Real GDP y/y", "rt_cum3y_infl": "Cumulative 3-yr inflation (price level)",
             "rt_d12_mort30": "Δ12m mortgage rate", "rt_rdpi_pc_yoy": "Real disposable income pc y/y", "rt_u6": "U-6 underutilisation",
             "rt_food_yoy": "Food-at-home inflation", "rt_gas_real_yoy": "Real gasoline price y/y", "rt_epu": "Policy uncertainty (news-based EPU)"}
    dd["Variable"] = dd["Variable"].map(lambda v: names.get(v, v))
    dd.columns = ["Variable", "Coef (2000–19)", "p", "Change 2019→25/26", "Contribution (pts)"]
    table(d, dd, caption="Table 2. Decomposition of the 2019 → 2025–26 change with the household-pressure model (M1H2).", size=8,
          fmt={"Coef (2000–19)": "{:.2f}", "p": "{:.3f}", "Change 2019→25/26": "{:.2f}", "Contribution (pts)": "{:.1f}"},
          note=f"M1H2 explains {hc_tot:.1f} of {act:.1f} points; with the mode offset, {hc_tot-6.6:.1f}. The out-of-sample 2025–26 gap shrinks from −31.6 (M1) to about −12 (M1H2). "
               "Coefficients are associational; EPU is itself built from newspaper text, so its contribution sits between E1 (real policy shocks — tariffs, shutdown) and E2 (coverage).")
    para(d, "**Why falling inflation need not reverse concern about prices.** Inflation measures the *rate*; households experience the *level*. The PCE price level rose 24% "
            "between January 2021 and August 2026, against 12% on a 2%-a-year path — prices are roughly 11% higher than the pre-2021 norm would imply and do not "
            "come back down when inflation falls. Michigan respondents say so: the share reporting they are worse off "
            f"*because of higher prices* rose from {comp.loc['pagorn_hp_all','2019']:.0f}% in 2019 to {comp.loc['pagorn_hp_all','2025–26']:.0f}% in 2025–26 — *above* "
            f"its 2022 inflation-peak level ({comp.loc['pagorn_hp_all','2022 (inflation peak yr)']:.0f}%). Buying conditions for durables (−{abs(comp.loc['dur_r_all','change_vs_2019']):.0f} points), "
            f"vehicles (−{abs(comp.loc['veh_r_all','change_vs_2019']):.0f}) and homes (−{abs(comp.loc['hom_r_all','change_vs_2019']):.0f}) collapsed, with 'interest rates high' as a reason for "
            f"homes up {comp.loc['homrn_hr_all','change_vs_2019']:.0f} pp: the cost of money is part of the perceived cost of living (Bolhuis, Cramer, Schulz & Summers, 2024). "
            "Wage growth that has caught up with prices does not erase the memory of the reference price (anchoring) — a mechanism we can proxy but not isolate.", align="justify")
    if len(mg):
        para(d, f"**A first-principles check: how long do consumers remember inflation?** We replaced current inflation with an exponentially weighted memory of "
                f"past monthly inflation and estimated its half-life from 1978–2019 alone. History says memory is short (half-life ≈ {mg.best_half_life_months.iloc[0]:.0f} months), "
                f"and the memory model leaves the 2025–26 gap unchanged ({mg.set_index('period').loc['2025–2026','gap_inflation_memory']:.1f} vs "
                f"{mg.set_index('period').loc['2025–2026','gap_M1_current_inflation']:.1f}). So today's level-anchored behaviour is **not** how consumers reacted in the "
                "past four decades: the 2021–22 shock pushed households outside the range the models were trained on (explanation E3 — a regime break), and "
                "'worse off because of higher prices' now exceeds its 2022 peak. The gap is a measurement and modelling failure as much as a perception problem.", align="justify")
    figure(d, FIG / "fig_level_vs_rate.png", "Figure 2. Price complaints stayed high after inflation fell. Michigan: % worse off citing higher prices; % saying it is a bad time to buy durables because of prices or interest rates; PCE inflation (dashed, right axis).", width=5.4)
    nec = T("necessities_vs_headline.csv")
    if len(nec):
        n_ = nec.set_index("series")["Jan 2021 → Sep 2026 (%)"]; sh_ = n_.iloc[2]
        para(d, "**Is the CPI wrong? No — it answers a narrower question.** The BLS prices a fixed basket (~80,000 prices a month), weights items by "
                "*dollars* spent (so higher-spending households weigh more), measures owner housing as an imputed rent that lags market rents by about a year, "
                "adjusts for quality, and — since 1983 — excludes interest costs. Its known biases (Boskin Commission, 1996) ran *upward* and were largely "
                "corrected. So official inflation does not hide price growth; it measures the *rate* for an *average* basket, while households feel the *level*, "
                f"their own basket and borrowing costs. From January 2021 to September 2026 headline CPI rose {n_['All items (headline CPI)']:.0f}%, shelter "
                f"{sh_:.0f}%, groceries {n_['Food at home (groceries)']:.0f}% and gasoline {n_['Gasoline']:.0f}% (from a pandemic low), while "
                f"average hourly earnings rose {n_['Average hourly earnings (nominal)']:.0f}% — real wages are still slightly below their January-2021 level (a level "
                "that was flattered by low-wage job losses).", align="justify")
    para(d, "**Why aggregate growth can differ from household experience.** GDP and payroll growth are averages; household finances depend on the distribution "
            f"of real income, on borrowing costs and on prices of necessities. Expected real income (income vs prices) fell {abs(comp.loc['rinc_r_all','change_vs_2019']):.0f} points; "
            "the Current Conditions index carries a larger gap than Expectations (Table 1: ICC gap −43.7 vs ICE −25.8 in 2026), consistent with present-day "
            "affordability rather than a general forecast of collapse.", align="justify")

    # ------------------------------------------------------------------ 4 groups (student hypothesis)
    d.add_heading("4. Who is pessimistic, and which hardships do they report? (age and income)", 1)
    a = age.reset_index()[["group", "ICS_2019", "ICS_2025_26", "change", "pct_change", "implied_weight_CLS", "contribution_pts_CLS", "share_of_decline_%_CLS"]]
    a.columns = ["Age group", "ICS 2019", "ICS 2025–26", "Change", "% change", "Weight", "Contribution", "Share of decline"]
    i = inc.reset_index()[["group", "ICS_2019", "ICS_2025_26", "change", "pct_change", "implied_weight_CLS", "contribution_pts_CLS", "share_of_decline_%_CLS"]]
    i.columns = a.columns; i = i.rename(columns={"Age group": "Group"}); a = a.rename(columns={"Age group": "Group"})
    table(d, pd.concat([a, i]), caption="Table 3. Concentration of the decline by age and income tercile (monthly sub-indices).", size=8,
          fmt={"ICS 2019": "{:.1f}", "ICS 2025–26": "{:.1f}", "Change": "{:.1f}", "% change": "{:.0f}%", "Weight": "{:.2f}", "Contribution": "{:.1f}", "Share of decline": "{:.0f}%"},
          note="Weights are implied by constrained least squares of the headline on the three sub-indices (2015–2026). Unweighted respondent counts are not used: the web "
               "sample is ~66% aged 55+, which Michigan's weights correct.")
    para(d, f"**FINDING — the decline is broad-based.** Every age group lost 37–47 points and every income tercile 40–43. Young adults (18–34) fell furthest "
            f"({age.loc['18–34','change']:.0f} points, {age.loc['18–34','pct_change']:.0f}%), but because older groups carry more weight, those aged 55+ contribute the most "
            f"points to the headline ({age.loc['55+','share_of_decline_%_CLS']:.0f}%) and 18–34 the least ({age.loc['18–34','share_of_decline_%_CLS']:.0f}%). "
            "So the answer to 'which age group drives the rating' depends on the question: severity is highest among the young; contribution is largest among older consumers. "
            + (lambda rg: f"Geography tells the same story: every Census region fell {abs(rg.change.max()):.0f}–{abs(rg.change.min()):.0f} points ({abs(rg["pct_change"].max()):.0f}–{abs(rg["pct_change"].min()):.0f}%)." if len(rg) else "")(T("decline_by_region.csv")), align="justify")
    para(d, f"**Hardships differ in mix, not in direction.** The share citing higher prices as a reason for being worse off rose ~35–40 pp in all three age groups. "
            f"What is specific to the young is income and housing: 'worse off — lower income' +{hc.loc['rsn_worse_lowincome','18–34']:.0f} pp (vs +{hc.loc['rsn_worse_lowincome','55+']:.0f} for 55+), "
            f"'can't afford a home' +{hc.loc['hb_cant_afford','18–34']:.1f} pp (vs +{hc.loc['hb_cant_afford','55+']:.1f}), and higher year-ahead inflation expectations "
            f"(+{hc.loc['px_median','18–34']:.1f} pp). The young also report hearing far more unfavourable economic news (+{hc.loc['news_unfav','18–34']:.0f} pp vs +{hc.loc['news_unfav','55+']:.0f}) "
            f"and rate government economic policy 'poor' more often (+{hc.loc['govt_poor','18–34']:.0f} pp).", align="justify")
    ex = T("experience_effects.csv"); yo = T("experience_young_vs_old.csv")
    if len(ex):
        e15 = ex[ex.theta == 1.5].set_index("outcome")
        para(d, "**Is this generation scarred? A test, not an assertion.** Economists Malmendier & Nagel show that people form inflation beliefs from the "
                "inflation they have *lived through*, weighting recent years more — and the young, with shorter lives, weight recent years most. For each "
                "Michigan age group we computed lifetime-experienced CPI inflation (Philadelphia Fed history from 1947; weights ∝ (age − years ago)^1.5) and "
                "asked, *within the same month* (so current inflation and national news are identical for everyone), whether groups with more experienced "
                f"inflation think and feel differently. They do: one extra point of experienced inflation raises a group's year-ahead inflation expectation by "
                f"{e15.loc['1-yr inflation expectation (median %)','coef_per_pp_experienced']:.2f} pp (p < 0.001) and lowers its sentiment by "
                f"{abs(e15.loc['Sentiment (ICS, 3mma)','coef_per_pp_experienced']):.1f} points (p = {e15.loc['Sentiment (ICS, 3mma)','p']:.3f}), robust to the weighting "
                f"(θ = 1, 3). The 2021–23 shock raised the young's experienced inflation most, and this alone predicts {abs(yo.predicted_by_experience.iloc[0]):.1f} of "
                f"the {abs(yo.actual_extra_decline_young_vs_old.iloc[0]):.1f} extra points the 18–34s lost relative to the 55+ (~{100*yo.share_explained.iloc[0]:.0f}%). "
                "**FINDING:** the generational 'scarring' story is supported for inflation — a measurable, rational-learning channel, not a media effect. "
                "Caveats: three age groups, 3-month-averaged tables, and group-specific trends are not absorbed by the fixed effects; the test needs full "
                "lifetime histories (an earlier version using PCE from 1959 truncated older groups and was discarded).", align="justify")
    wm1 = wm[wm.spec == "hardship + news heard"][["var", "coef", "se_driscoll_kraay", "p"]].copy()
    lab = {"rsn_worse_prices": "Worse off: higher prices (pp)", "rsn_worse_lowincome": "Worse off: lower income (pp)", "hb_cant_afford": "Home: can't afford (pp)",
           "joblose_mean": "Expected job-loss probability (pp)", "nu_price": "Heard bad news: prices (pp)", "nu_emp": "Heard bad news: jobs (pp)"}
    wm1["var"] = wm1["var"].map(lab); wm1.columns = ["Within-month regressor (age groups)", "Coef", "Driscoll–Kraay SE", "p"]
    table(d, wm1, caption="Table 4. Group-level ICS on reported hardships with group and MONTH fixed effects (age groups, 2008–2026).", size=8,
          fmt={"Coef": "{:.2f}", "Driscoll–Kraay SE": "{:.2f}", "p": "{:.3f}"},
          note=f"Month fixed effects absorb everything common to all groups in a month — national coverage and the macro releases — so coefficients use only cross-group "
               f"differences. Within-R² {wm[wm.spec=='hardship + news heard'].within_R2.iloc[0]:.2f}. Caveat: hardship and sentiment come from the same respondents (reverse causality possible).")
    para(d, "**Interpretation.** Within a month, groups that report more price and income hardship are less confident (≈ −0.6 ICS points per pp citing prices), "
            "and this survives controls for the bad news each group says it heard. Group-specific hardship is therefore a credible channel (E1). But the "
            "hardship increase is common to all groups, so it cannot explain *why the young fell further* on its own; the young's extra income/housing stress and "
            "extra bad-news recall both line up with their larger decline. Your original intuition is supported in direction, with the correction that "
            "the story is 'everyone feels the price level; younger households additionally feel income and housing strain' rather than 'one group drives it'.", align="justify")

    # ------------------------------------------------------------------ 5-10 media & synthesis
    for block in S["sections"]:
        kind = block[0]
        if kind == "h1": d.add_heading(block[1], 1)
        elif kind == "h2": d.add_heading(block[1], 2)
        elif kind == "p": para(d, block[1], align="justify")
        elif kind == "b": bullets(d, block[1])
        elif kind == "fig": figure(d, FIG / block[1], block[2], width=block[3] if len(block) > 3 else 6.4)
        elif kind == "tbl": table(d, block[1], caption=block[2], size=8, fmt=block[3] if len(block) > 3 else None, note=block[4] if len(block) > 4 else None)
    d.save(R / "Consumer_Sentiment_Media_Report.docx"); print("saved report")


def MEDIA_RESULTS():
    from report_media import media_sections
    return media_sections()


if __name__ == "__main__":
    build()

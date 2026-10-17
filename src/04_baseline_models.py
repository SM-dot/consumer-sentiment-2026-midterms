"""
04_baseline_models.py — Research questions 3 (how much do U-3, inflation, GDP explain?) and the
"alternative explanations" requirement (household pressures not captured by headline indicators).

Outputs (outputs/tables, outputs/figures):
  spec_selection.csv, m1_fullsample.csv, gap_m1.csv (+ICC/ICE), gap_summary.csv, decomposition.csv,
  robustness_gap.csv, extended_controls.csv, extended_gap.csv, fig_gap_*.png
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

P = load_panel()
P["rt_du3_12"] = P["rt_u3"] - P["rt_u3"].shift(12)
P["rt_d12_mort30"] = P["rt_mort30"] - P["rt_mort30"].shift(12)     # change in the cost of money (Bolhuis et al. 2024 channel)

# ------------------------------------------------------------------ 1. specification choice (pre-2000 data ONLY)
cands = {
    "U3 + PCE + GDP q/q SAAR": ["rt_u3", "rt_pce_yoy", "rt_gdp_qoq_saar"],
    "U3 + PCE + GDP y/y":      ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy"],
    "U3 + dU3(12m) + PCE + GDP y/y": ["rt_u3", "rt_du3_12", "rt_pce_yoy", "rt_gdp_yoy"],
}
allx = sorted({c for v in cands.values() for c in v})
pre = P.loc[:"1999-12"].dropna(subset=["ics"] + allx)          # COMMON sample so BIC is comparable
rows = []
for k, xs in cands.items():
    r = ols_hac(pre["ics"], pre[xs]); rows.append({"spec": k, "n": int(r.nobs), "adj_R2": r.rsquared_adj, "BIC": r.bic})
spec = pd.DataFrame(rows).sort_values("BIC"); spec.to_csv(TAB / "spec_selection.csv", index=False)
print(spec)
M1 = cands[spec.iloc[0]["spec"]]
print("Selected M1:", M1)

# ------------------------------------------------------------------ 2. full-sample fit (1978–2019, pre-pandemic) for reference
fit = ols_hac(P.loc[:"2019-12", "ics"], P.loc[:"2019-12", M1])
pd.DataFrame({"coef": fit.params, "hac_se": fit.bse, "t": fit.tvalues, "p": fit.pvalues}).assign(
    R2=fit.rsquared, n=fit.nobs).to_csv(TAB / "m1_fullsample.csv")
print(fit.summary().tables[1])

# ------------------------------------------------------------------ 3. real-time OOS gap (expanding window)
gaps = {}
for tgt in ["ics", "icc", "ice"]:
    g = expanding_oos(P, tgt, M1, start="1990-01")
    g["web_share"] = P["web_share"]
    g["gap_mode_adj"] = g["gap"] - MODE_EFFECT_UMICH * g["web_share"]      # add back the documented web effect
    g["gap_mode_adj_alt"] = g["gap"] - MODE_EFFECT_ALT * g["web_share"]
    g.to_csv(TAB / f"gap_m1_{tgt}.csv"); gaps[tgt] = g
G = gaps["ics"]

periods = {"1990–2007": ("1990-01", "2007-12"), "2008–2009 GFC": ("2008-01", "2009-12"), "2010–2019": ("2010-01", "2019-12"),
           "2020 COVID": ("2020-01", "2020-12"), "2021–2022 inflation surge": ("2021-01", "2022-12"),
           "2023–2024 disinflation": ("2023-01", "2024-12"), "2025": ("2025-01", "2025-12"),
           "2026 (to Oct, pre-midterm)": ("2026-01", "2026-10")}
summ = []
for name, (a, b) in periods.items():
    s = G.loc[a:b]
    summ.append({"period": name, "months": len(s), "mean_actual": s.actual.mean(), "mean_pred": s.pred.mean(),
                 "mean_gap": s.gap.mean(), "mean_gap_mode_adj": s.gap_mode_adj.mean(),
                 "share_below_95PI": (s.actual < s.lo95).mean(), "share_above_95PI": (s.actual > s.hi95).mean(),
                 "rmse": rmse(s.gap), "icc_gap": gaps["icc"].loc[a:b].gap.mean(), "ice_gap": gaps["ice"].loc[a:b].gap.mean()})
summ = pd.DataFrame(summ); summ.to_csv(TAB / "gap_summary.csv", index=False)
print(summ.round(2).to_string())

# ------------------------------------------------------------------ 4. RQ3: how much of the post-2019 decline do the 3 indicators explain?
base, now = ("2019-01", "2019-12"), ("2025-01", "2026-10")
b = fit.params
dx = P.loc[now[0]:now[1], M1].mean() - P.loc[base[0]:base[1], M1].mean()
contrib = (b[M1] * dx)
dec = pd.DataFrame({"mean_2019": P.loc[base[0]:base[1], M1].mean(), "mean_2025_26": P.loc[now[0]:now[1], M1].mean(),
                    "change": dx, "coef(1978–2019)": b[M1], "contribution_to_ICS": contrib})
actual_change = P.loc[now[0]:now[1], "ics"].mean() - P.loc[base[0]:base[1], "ics"].mean()
dec.loc["TOTAL predicted by U3+PCE+GDP"] = [np.nan] * 4 + [contrib.sum()]
dec.loc["ACTUAL change in ICS"] = [np.nan] * 4 + [actual_change]
dec.loc["Share explained (%)"] = [np.nan] * 4 + [100 * contrib.sum() / actual_change]
dec.loc["Web-mode offset (UMich est.)"] = [np.nan] * 4 + [MODE_EFFECT_UMICH]
dec.loc["Share explained incl. mode offset (%)"] = [np.nan] * 4 + [100 * (contrib.sum() + MODE_EFFECT_UMICH) / actual_change]
dec.to_csv(TAB / "decomposition.csv"); print(dec.round(2))

# ------------------------------------------------------------------ 5. robustness of the gap
rob = []
def gapmean(xs, data=P, tgt="ics", a="2025-01", b="2026-10"):
    g = expanding_oos(data, tgt, xs, start="1990-01"); s = g.loc[a:b]
    return s.gap.mean(), rmse(g.loc["1990-01":"2019-12"].gap)
alt = P.copy()
alt["xp_u3"], alt["xp_pce"] = P["expost_u3"].shift(1), P["expost_pce_yoy"].shift(2)
alt["xp_gdp_same_q"] = P["expost_gdp_qoq_saar_same_q"]
alt["core"] = P["rt_core_pce_yoy"]
variants = {
    "M1 (real-time, headline PCE) — MAIN": M1,
    "Core PCE instead of headline (professor's column)": [c if c != "rt_pce_yoy" else "core" for c in M1],
    "GDP q/q SAAR instead of y/y": [c if c != "rt_gdp_yoy" else "rt_gdp_qoq_saar" for c in M1],
    "Ex-post revised U3/PCE (same lags)": [{"rt_u3": "xp_u3", "rt_pce_yoy": "xp_pce"}.get(c, c) for c in M1],
    "LOOK-AHEAD: current-vintage GDP of the SAME quarter (forbidden by brief; shown for contrast)":
        [c if c != "rt_gdp_yoy" else "xp_gdp_same_q" for c in M1],
}
for k, xs in variants.items():
    gm, r = gapmean(xs, alt); rob.append({"variant": k, "mean_gap_2025_26": gm, "oos_rmse_1990_2019": r})
for w in [60, 120]:
    g = expanding_oos(P, "ics", M1, start="1990-01", window=w)
    rob.append({"variant": f"Rolling {w}-month window", "mean_gap_2025_26": g.loc["2025-01":].gap.mean(),
                "oos_rmse_1990_2019": rmse(g.loc[:"2019-12"].gap)})
rob = pd.DataFrame(rob); rob.to_csv(TAB / "robustness_gap.csv", index=False); print(rob.round(2).to_string())

# ------------------------------------------------------------------ 6. alternative explanation 1: household pressures
long_controls = {"price_gap": "Cumulative price-level gap vs 2% path (3y)", "cum3y_infl": "Cumulative 3-yr PCE inflation",
                 "mort30": "30-yr mortgage rate (level)", "d12_mort30": "12-month change in 30-yr mortgage rate",
                 "rdpi_pc_yoy": "Real disposable income per capita, y/y", "interest_burden": "Non-mortgage interest / DPI",
                 "saving_rate": "Personal saving rate"}
short_controls = {"u6": "U-6 labor underutilisation", "food_yoy": "Food-at-home CPI y/y", "gas_real_yoy": "Real gasoline price y/y",
                  "afford_idx": "Mortgage-payment affordability index", "epu": "Economic policy uncertainty (news-based)",
                  "real_ahe_yoy": "Real avg hourly earnings y/y", "shelter_yoy": "Shelter CPI y/y"}
ext = []
g_base_long = expanding_oos(P, "ics", M1, start="1990-01")
g_base_short = expanding_oos(P, "ics", M1, start="2008-01")
for dic, start, gb in [(long_controls, "1990-01", g_base_long), (short_controls, "2008-01", g_base_short)]:
    for c, lab in dic.items():
        xs = M1 + ["rt_" + c]
        sample = P.loc[:"2019-12"] if start == "1990-01" else P.loc["2000-01":"2019-12"]
        r = ols_hac(sample["ics"], sample[xs])
        g = expanding_oos(P, "ics", xs, start=start, min_train=96)
        common = g.index.intersection(gb.index)
        cw = clark_west(gb.loc[common, "gap"], g.loc[common, "gap"], gb.loc[common, "pred"], g.loc[common, "pred"])
        ext.append({"control": lab, "var": c, "est_sample": f"{sample.index[0]}–2019", "coef": r.params["rt_" + c],
                    "hac_t": r.tvalues["rt_" + c], "p": r.pvalues["rt_" + c],
                    "oos_rmse_base": rmse(gb.loc[common].gap), "oos_rmse_ext": rmse(g.loc[common].gap),
                    "CW_stat": cw[0], "CW_p": cw[1],
                    "gap_2025_26_base": gb.loc["2025-01":].gap.mean(), "gap_2025_26_ext": g.loc["2025-01":].gap.mean()})
ext = pd.DataFrame(ext)
ext["p_holm"] = holm(ext["p"]); ext["CW_p_holm"] = holm(ext["CW_p"].fillna(1))
ext["gap_closed_pts"] = ext.gap_2025_26_ext - ext.gap_2025_26_base   # >0 = control closes (shrinks) the negative gap
ext.to_csv(TAB / "extended_controls.csv", index=False); print(ext.round(3).to_string())

# Combined household-pressure model (M1H), chosen A PRIORI from theory (not by significance, to avoid data mining):
#   cost of living (cumulative 3-yr inflation: level-vs-rate channel), cost of money (12m change in mortgage rate),
#   and household income (real disposable income per capita growth).
M1H = M1 + ["rt_cum3y_infl", "rt_d12_mort30", "rt_rdpi_pc_yoy"]
# Short-history extension (2000+): adds U-6, food inflation, real gasoline, policy uncertainty
M1H2 = M1H + ["rt_u6", "rt_food_yoy", "rt_gas_real_yoy", "rt_epu"]
gH2 = expanding_oos(P, "ics", M1H2, start="2008-01", min_train=96)
gH2.to_csv(TAB / "gap_m1h2_ics.csv")
fitH2 = ols_hac(P.loc["2000-01":"2019-12", "ics"], P.loc["2000-01":"2019-12", M1H2])
pd.DataFrame({"coef": fitH2.params, "hac_se": fitH2.bse, "p": fitH2.pvalues}).assign(R2=fitH2.rsquared).to_csv(TAB / "m1h2_fullsample.csv")
print("M1H2 gap 2025-26:", gH2.loc["2025-01":].gap.mean())
# Structural-break check: does the M1 intercept shift after 2020 (HAC t-test on a post-2021 dummy, full sample)?
Pb = P.copy(); Pb["post2021"] = (Pb.index >= pd.Period("2021-01", "M")).astype(int)
rb = ols_hac(Pb["ics"], Pb[M1 + ["post2021", "web_share"]])
pd.DataFrame({"coef": rb.params, "hac_se": rb.bse, "p": rb.pvalues}).to_csv(TAB / "break_test.csv")
print("Break test:\n", pd.DataFrame({"coef": rb.params, "p": rb.pvalues}).round(3))
gH = expanding_oos(P, "ics", M1H, start="1990-01")
gH.to_csv(TAB / "gap_m1h_ics.csv")
fitH = ols_hac(P.loc[:"2019-12", "ics"], P.loc[:"2019-12", M1H])
pd.DataFrame({"coef": fitH.params, "hac_se": fitH.bse, "p": fitH.pvalues}).assign(R2=fitH.rsquared).to_csv(TAB / "m1h_fullsample.csv")
print("M1H:", M1H, "gap 2025-26:", gH.loc["2025-01":].gap.mean(), "vs M1", G.loc["2025-01":].gap.mean())

# ------------------------------------------------------------------ figures
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(2, 1, figsize=(9, 6.2), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
s = G.loc["2010-01":]; sh = gH.loc["2010-01":]
x = s.index.to_timestamp()
ax[0].fill_between(x, s.lo95, s.hi95, color="#9db4d6", alpha=.35, label="M1 95% prediction interval")
ax[0].plot(x, s.pred, color="#1f4e8c", lw=1.4, label="M1: U-3 + PCE + GDP (real-time, out-of-sample)")
ax[0].plot(sh.index.to_timestamp(), sh.pred, color="#c77c02", lw=1.2, ls="--", label="M1H: + cumulative inflation, mortgage-rate change, real income")
sh2 = gH2.loc["2010-01":]
ax[0].plot(sh2.index.to_timestamp(), sh2.pred, color="#6a3d9a", lw=1.0, ls=":", label="M1H2: + U-6, food, gasoline, policy uncertainty")
ax[0].plot(x, s.actual, color="black", lw=1.6, label="Michigan ICS (actual)")
ax[0].axvspan(pd.Timestamp("2024-04-01"), pd.Timestamp("2024-07-01"), color="grey", alpha=.15)
ax[0].text(pd.Timestamp("2024-04-15"), 105, "phone→web\ntransition", fontsize=7)
ax[0].set_ylabel("Index (1966Q1=100)"); ax[0].legend(loc="lower left", fontsize=7.5, frameon=False)
ax[0].set_title("Consumer sentiment vs. what headline economic data predict (real-time, out-of-sample)")
ax[1].bar(x, s.gap, width=25, color=np.where(s.gap < 0, "#b2382b", "#2e7d4f"))
ax[1].plot(x, s.gap_mode_adj, color="black", lw=.8, label="gap after adding back UMich's web-mode effect (6.6 pts)")
ax[1].axhline(0, color="black", lw=.6); ax[1].set_ylabel("Sentiment gap"); ax[1].legend(fontsize=7, frameon=False)
fig.tight_layout(); fig.savefig(FIG / "fig_gap_main.png", dpi=200)

fig, ax = plt.subplots(figsize=(8, 3.2))
for tgt, c in [("icc", "#7b3294"), ("ice", "#008837")]:
    s = gaps[tgt].loc["2015-01":]; ax.plot(s.index.to_timestamp(), s.gap.rolling(3).mean(), label=tgt.upper() + " gap (3mma)", color=c)
ax.axhline(0, color="black", lw=.6); ax.legend(frameon=False); ax.set_title("Gap by component: Current Conditions vs Expectations")
fig.tight_layout(); fig.savefig(FIG / "fig_gap_components.png", dpi=200)
print("done")

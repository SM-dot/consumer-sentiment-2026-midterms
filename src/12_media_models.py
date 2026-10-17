"""
12_media_models.py — Research questions 2, 5, 6: association vs. causal impact of media measures.

A. Three-model horse race (brief §4), monthly 2017-01 .. 2026-10, real-time regressors, media lagged one month
   (media in month t-1 is fully observed before month-t interviews; same-month media as sensitivity):
     M1  economic indicators only            ICS_t ~ U3 + PCE + GDP (+ web-mode share)
     M2  + media measures                    + tone_net(t-1) + salience prices(t-1) + salience labour-bad(t-1)
     M3  + household / political controls    + cum. 3-yr inflation + Δ mortgage rate + EPU + post-2025 transition
   Two targets: (i) ICS level with these regressors; (ii) the LONG-SAMPLE M1 gap (actual – 1978-based real-time
   prediction from 04_baseline_models), i.e. "does media explain what fundamentals do not?".
   Evaluation: expanding-window OOS from 2020-01 (36-month burn-in), RMSE, Clark–West (nested), coefficient
   stability (rolling 36-month coefficients), HAC(6) inference, Holm correction across media measures.
B. Reverse causality: Granger tests in both directions (Δ sentiment <-> tone, and sentiment <-> Michigan news-heard),
   lag order by BIC; placebo "lead" test (future media should not predict current sentiment if causal ordering is media->sentiment).
C. Local projections: response of the M1 gap at h = 0..6 to a one-s.d. 'excess negativity' shock.
D. Sensitivity: alternative tone measures (AI / FinBERT / dictionary / GDELT), same-month media, excluding 2020,
   excluding the web-transition months, partisan-transition control.
"""
import numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.tsa.api import VAR
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

P = load_panel()
Mm = pd.read_csv(PROC / "media_monthly.csv"); Mm["month"] = pd.PeriodIndex(Mm.month, freq="M"); Mm = Mm.set_index("month")
gap = pd.read_csv(TAB / "gap_m1_ics.csv"); gap["month"] = pd.PeriodIndex(gap.month, freq="M"); gap = gap.set_index("month")
Mm = Mm.drop(columns=[c for c in Mm.columns if c in P.columns]); D = P.join(Mm, how="left").join(gap[["gap", "pred"]].rename(columns={"pred": "m1_pred_long"}))
D["rt_d12_mort30"] = D.rt_mort30 - D.rt_mort30.shift(12)
MEDIA = ["tone_net", "sal_prices_rising", "sal_labor_bad"]
for c in MEDIA + ["excess_negativity", "tone_finbert", "tone_dict", "gd_economy_tone", "gd_prices_share", "emotional_share",
                  "level_frame_share", "news_u_all", "newsrn_u_pri_all"]:
    if c in D: D[c + "_l1"] = D[c].shift(1); D[c + "_f1"] = D[c].shift(-1)
D = D.loc["2017-01":"2026-10"]
ECON = ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy", "web_share"]
MED = [c + "_l1" for c in MEDIA]
CTRL = ["rt_cum3y_infl", "rt_d12_mort30", "rt_epu", "post_2025_transition"]
SPECS = {"M1 econ only": ECON, "M2 + media": ECON + MED, "M3 + media + controls": ECON + MED + CTRL,
         "M3b econ + controls (no media)": ECON + CTRL}


def horse_race(target, start="2020-01", label=""):
    res, preds = [], {}
    for k, xs in SPECS.items():
        g = expanding_oos(D, target, xs, start=start, min_train=30)
        preds[k] = g
    common = sorted(set.intersection(*[set(g.index) for g in preds.values()]))
    for k, g in preds.items():
        g = g.loc[common]
        row = {"target": target, "model": k, "n_oos": len(g), "rmse": rmse(g.gap), "mean_error": g.gap.mean()}
        nest = {"M2 + media": "M1 econ only", "M3 + media + controls": "M3b econ + controls (no media)", "M3b econ + controls (no media)": "M1 econ only"}
        if k in nest:
            b = preds[nest[k]].loc[common]
            row["vs"] = nest[k]; row["CW_stat"], row["CW_p"] = clark_west(b.gap, g.gap, b.pred, g.pred)
            row["DM_stat"], row["DM_p"] = diebold_mariano(b.gap, g.gap)
        res.append(row)
    return pd.DataFrame(res), preds


out = []
for tgt in ["ics", "gap"]:
    r, preds = horse_race(tgt); out.append(r)
    if tgt == "ics": PRED_ICS = preds
H = pd.concat(out); H.to_csv(TAB / "horse_race.csv", index=False); print(H.round(3).to_string())

# full-sample HAC fits with Holm-adjusted media p-values
fits = []
for tgt in ["ics", "gap"]:
    for k, xs in SPECS.items():
        r = ols_hac(D[tgt], D[xs], lags=6)
        for v in xs:
            fits.append({"target": tgt, "model": k, "var": v, "coef": r.params[v], "se": r.bse[v], "p": r.pvalues[v],
                         "R2": r.rsquared, "adjR2": r.rsquared_adj, "n": int(r.nobs)})
F = pd.DataFrame(fits)
F["p_holm_media"] = np.nan
for (t, k), g in F[F["var"].isin(MED)].groupby(["target", "model"]):
    F.loc[g.index, "p_holm_media"] = holm(g.p.values)
F.to_csv(TAB / "media_model_coefs.csv", index=False); print(F[F["var"].isin(MED)].round(3).to_string())

# ---------------- sensitivity: alternative media measures, one at a time, on the GAP (Holm across all)
sens = []
alts = ["tone_net", "tone_finbert", "tone_dict", "gd_economy_tone", "excess_negativity", "emotional_share",
        "level_frame_share", "sal_prices_rising", "sal_labor_bad", "gd_prices_share", "news_u_all", "newsrn_u_pri_all"]
for v in alts:
    for lagname, col in [("t-1", v + "_l1"), ("t (same month)", v)]:
        if col not in D or D[col].notna().sum() < 40: continue
        for sample, mask in [("2017–2026", slice(None)), ("excl. 2020", D.index.year != 2020),
                             ("excl. web transition 2024-04..06", ~D.index.isin(pd.period_range("2024-04", "2024-06", freq="M")))]:
            dd = D.loc[mask] if not isinstance(mask, slice) else D
            r = ols_hac(dd["gap"], dd[[col, "post_2025_transition", "web_share"]], lags=6)
            sens.append({"measure": v, "timing": lagname, "sample": sample, "coef": r.params[col], "p": r.pvalues[col],
                         "std_coef": r.params[col] * dd[col].std() / dd["gap"].std(), "n": int(r.nobs)})
S = pd.DataFrame(sens); S["p_holm"] = holm(S.p); S["p_bh"] = bh(S.p)
S.to_csv(TAB / "media_sensitivity.csv", index=False)
print(S[S["sample"] == "2017–2026"].round(3).to_string())

# ---------------- B. reverse causality: Granger both ways + placebo leads
gr = []
pairs = [("tone_net", "ics"), ("excess_negativity", "ics"), ("news_u_all", "ics"), ("sal_prices_rising", "ics"), ("gd_economy_tone", "ics")]
for m, s in pairs:
    if m not in D: continue
    Z = pd.DataFrame({"ds": D[s].diff(), "m": D[m].diff() if m != "excess_negativity" else D[m]}).dropna()
    if len(Z) < 40: continue
    p = VAR(Z).select_order(6).bic or 1
    p = max(1, int(p))
    g1 = grangercausalitytests(Z[["ds", "m"]], [p])[p][0]["ssr_ftest"]
    g2 = grangercausalitytests(Z[["m", "ds"]], [p])[p][0]["ssr_ftest"]
    gr.append({"media": m, "lag_BIC": p, "media->sentiment_F": g1[0], "media->sentiment_p": g1[1],
               "sentiment->media_F": g2[0], "sentiment->media_p": g2[1], "n": len(Z)})
GR = pd.DataFrame(gr); GR.to_csv(TAB / "granger.csv", index=False); print(GR.round(3).to_string())
pl = []
for v in ["tone_net", "excess_negativity", "news_u_all"]:
    if v + "_f1" not in D: continue
    r = ols_hac(D["gap"], D[[v + "_l1", v, v + "_f1", "post_2025_transition", "web_share"]], lags=6)
    pl.append({"measure": v, "coef_lag": r.params[v + "_l1"], "p_lag": r.pvalues[v + "_l1"], "coef_same": r.params[v],
               "p_same": r.pvalues[v], "coef_LEAD(placebo)": r.params[v + "_f1"], "p_LEAD": r.pvalues[v + "_f1"]})
pd.DataFrame(pl).to_csv(TAB / "placebo_leads.csv", index=False); print(pd.DataFrame(pl).round(3))

# ---------------- C. local projections: gap_{t+h} on excess-negativity shock_t
lp = []
if "excess_negativity" in D:
    sh = (D.excess_negativity - D.excess_negativity.mean()) / D.excess_negativity.std()
    for h in range(0, 7):
        y = D["gap"].shift(-h)
        X = pd.DataFrame({"shock": sh, "gap_l1": D.gap.shift(1), "web": D.web_share, "post25": D.post_2025_transition,
                          "du": D.rt_u3.diff(), "dpi": D.rt_pce_yoy.diff()})
        r = ols_hac(y, X, lags=h + 2)
        lp.append({"h": h, "coef": r.params["shock"], "se": r.bse["shock"], "p": r.pvalues["shock"], "n": int(r.nobs)})
LP = pd.DataFrame(lp); LP.to_csv(TAB / "local_projections.csv", index=False); print(LP.round(3))

# ---------------- coefficient stability: rolling 36-month M2 coefficients
roll = []
for end in D.index[35:]:
    w = D.loc[:end].iloc[-36:].dropna(subset=["ics"] + SPECS["M2 + media"])
    if len(w) < 30: continue
    r = sm.OLS(w.ics, sm.add_constant(w[SPECS["M2 + media"]])).fit()
    roll.append({"end": end, **{v: r.params[v] for v in MED}})
R = pd.DataFrame(roll).set_index("end"); R.to_csv(TAB / "rolling_media_coefs.csv")

# ---------------- figures
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(3, 1, figsize=(9, 7.5), sharex=True)
x = D.index.to_timestamp()
ax[0].plot(x, D.gap, color="#b2382b", label="Sentiment gap (actual − real-time M1)")
ax0 = ax[0].twinx(); ax0.plot(x, D.tone_net, color="#1f4e8c", lw=1, label="News tone (AI, net)"); ax0.set_ylabel("net tone")
ax[0].legend(loc="lower left", frameon=False, fontsize=7); ax0.legend(loc="lower right", frameon=False, fontsize=7)
ax[0].set_title("Sentiment gap vs. media tone")
ax[1].plot(x, D.sal_prices_rising, label="Salience: prices rising", color="#d95f02")
ax[1].plot(x, D.sal_labor_bad, label="Salience: layoffs + recession", color="#7570b3")
if "sal_inflation_falling" in D: ax[1].plot(x, D.sal_inflation_falling, label="Salience: inflation falling", color="#1b9e77")
ax[1].legend(frameon=False, fontsize=7); ax[1].set_ylabel("share of items")
if "news_u_all" in D:
    ax[2].plot(x, D.news_u_all, color="black", label="Michigan: % heard UNFAVORABLE news (recall)")
    ax[2].plot(x, D.news_f_all, color="grey", label="Michigan: % heard FAVORABLE news")
ax[2].legend(frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(FIG / "fig_media.png", dpi=200)
if len(R):
    fig, ax = plt.subplots(figsize=(8, 3))
    for v in MED: ax.plot(R.index.to_timestamp(), R[v], label=v)
    ax.axhline(0, color="black", lw=.6); ax.legend(frameon=False, fontsize=7); ax.set_title("Rolling 36-month coefficients (M2)")
    fig.tight_layout(); fig.savefig(FIG / "fig_rolling_coefs.png", dpi=200)
if len(LP):
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.errorbar(LP.h, LP.coef, yerr=1.96 * LP.se, fmt="o-", color="#1f4e8c"); ax.axhline(0, color="black", lw=.6)
    ax.set_xlabel("months ahead"); ax.set_ylabel("Δ gap per 1-sd excess negativity"); ax.set_title("Local projections")
    fig.tight_layout(); fig.savefig(FIG / "fig_lp.png", dpi=200)
print("done")

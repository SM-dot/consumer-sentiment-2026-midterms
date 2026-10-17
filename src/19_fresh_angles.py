"""
19_fresh_angles.py — Two first-principles tests that most treatments of the 'vibecession' skip.

A. THE TRANSITION TEST (does sentiment follow the coverage each side consumes?)
   If biased coverage drives sentiment, the 2025 presidential transition is a natural experiment: it flipped which
   outlets cover the economy negatively. We measure, by outlet lean and administration (Trump-1 2017–20, Biden 2021–24,
   Trump-2 2025–26), the AI net tone of SAME-QUERY economic headlines, and compare the size of the swing in coverage
   with the size of the swing in partisan sentiment documented by Michigan. A media-supply story needs the two swings
   to be comparable; a partisan-identity (motivated reasoning) story predicts sentiment swings far larger than
   coverage swings, and a price-level story predicts a common decline regardless of coverage.

B. INFLATION MEMORY (how long do consumers remember price increases?)
   Replace 'current inflation' with an exponentially weighted memory of past inflation,
       M_t(λ) = (1-λ) Σ_k λ^k π_{t-k}   (monthly PCE inflation, annualised),
   estimate the half-life ln(0.5)/ln(λ) by profile likelihood (BIC) on 1978–2019 ONLY, then re-run the real-time
   out-of-sample gap with memory instead of current inflation. If the 2022–26 gap shrinks, the 'gap' is largely
   a slowly fading memory of the price-level shock — measurable, not irrational.
"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

# ------------------------------------------------------------------ A. transition test
CORP = load_corpus(); A = pd.read_csv(PROC / "ai_codes.csv")
D = CORP.merge(A, on="item_id")
D = D[(D.ai_relevance_p > 0.5) & D.relevant_kw & (D.query_type == "outlet")].copy()
D["lean"] = D.outlet_lean.replace({"lean_left": "left", "lean_right": "right"})
D = D[D.lean.isin(["left", "center", "right"])]
D["admin"] = pd.cut(D.date, [pd.Timestamp("2017-01-20"), pd.Timestamp("2021-01-20"), pd.Timestamp("2025-01-20"), pd.Timestamp("2026-10-17")],
                    labels=["Trump-1 (2017–20)", "Biden (2021–24)", "Trump-2 (2025–26)"], right=False)
D["tone_num"] = D.ai_tone.map({"negative": -1, "neutral": 0, "positive": 1})
D["fin_num"] = D.finbert_tone.map({"negative": -1, "neutral": 0, "positive": 1})
D["dict_num"] = D.dict_tone.map({"negative": -1, "neutral": 0, "positive": 1})
cells = D.groupby(["admin", "lean"], observed=True).agg(n=("tone_num", "size"), ai_tone=("tone_num", "mean"),
                                                        finbert=("fin_num", "mean"), dictionary=("dict_num", "mean")).reset_index()
cells.to_csv(TAB / "transition_tone_by_lean.csv", index=False); print(cells.round(3).to_string())
piv = cells.pivot(index="admin", columns="lean", values="ai_tone")
swing = pd.DataFrame({
    "coverage swing, right-leaning outlets (Biden → Trump-2)": [piv.loc["Trump-2 (2025–26)", "right"] - piv.loc["Biden (2021–24)", "right"]],
    "coverage swing, left-leaning outlets (Biden → Trump-2)": [piv.loc["Trump-2 (2025–26)", "left"] - piv.loc["Biden (2021–24)", "left"]],
    "coverage swing, center outlets (Biden → Trump-2)": [piv.loc["Trump-2 (2025–26)", "center"] - piv.loc["Biden (2021–24)", "center"]],
})
# Michigan published partisan readings (reports Apr-2025 / Jul-2026): June 2022 trough (Biden) vs May 2026 trough (Trump-2)
party = pd.DataFrame({"party": ["Democrats", "Independents", "Republicans"],
                      "ICS_Jun2022_phone": [66.4, 48.5, 33.0], "ICS_May2026": [32.8, 40.6, 84.6]})
party["sentiment_swing"] = party.ICS_May2026 - party.ICS_Jun2022_phone
party.to_csv(TAB / "transition_party_sentiment.csv", index=False)
# standardise coverage swings in units of the month-to-month s.d. of each lean's monthly tone
mon = D.groupby([D.date.dt.to_period("M"), "lean"]).tone_num.mean().unstack()
sd = mon.std()
swing_sd = {k: v[0] / sd[k.split(",")[1].split()[0].replace("-leaning", "")] for k, v in swing.items()}
swing.to_csv(TAB / "transition_coverage_swing.csv", index=False)
print(swing.round(3).T); print(party)
# Same-month estimate with outlet FE: right x Trump-2 relative to Biden, left x Trump-2 relative to Biden
import statsmodels.formula.api as smf
D = D.dropna(subset=["admin", "tone_num"]).copy(); D["ms"] = D.date.dt.to_period("M").astype(str)
# identified interactions (base: center outlets under Biden); outlet FE absorb lean, month FE absorb the administration
for l in ["left", "right"]:
    for a, tag in [("Trump-1 (2017–20)", "T1"), ("Trump-2 (2025–26)", "T2")]:
        D[f"{l}_{tag}"] = ((D.lean == l) & (D.admin == a)).astype(int)
m = smf.ols("tone_num ~ left_T1 + left_T2 + right_T1 + right_T2 + C(source) + C(ms)", data=D).fit(cov_type="cluster", cov_kwds={"groups": D["ms"]})
coef = pd.DataFrame({"coef": m.params[["left_T1", "left_T2", "right_T1", "right_T2"]], "se": m.bse[["left_T1", "left_T2", "right_T1", "right_T2"]],
                     "p": m.pvalues[["left_T1", "left_T2", "right_T1", "right_T2"]]})
coef.index = ["Left outlets, Trump-1 vs Biden", "Left outlets, Trump-2 vs Biden", "Right outlets, Trump-1 vs Biden", "Right outlets, Trump-2 vs Biden"]
coef.to_csv(TAB / "transition_did.csv"); print(coef.round(3))

# ------------------------------------------------------------------ B. inflation memory
P = load_panel()
import importlib, sys
bd = importlib.import_module("03_build_dataset")
pidx = bd.bea("DPCERG").reindex(pd.period_range("1959-01", "2026-10", freq="M"))
mom = 1200 * np.log(pidx / pidx.shift(1))                      # annualised monthly inflation (%)
avail = mom.shift(2)                                            # public with a 2-month lag (PCE release)


def memory(lam):
    w = (1 - lam) * lam ** np.arange(0, 240)
    vals = avail.values; out = np.full(len(vals), np.nan)
    for t in range(240, len(vals)):
        seg = vals[t - 239:t + 1][::-1]
        if np.isnan(seg).any(): continue
        out[t] = np.dot(w, seg) / w.sum()
    return pd.Series(out, index=avail.index)


grid = [0.80, 0.85, 0.90, 0.93, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99]
rows = []
for lam in grid:
    P["mem"] = memory(lam).reindex(P.index)
    r = ols_hac(P.loc[:"2019-12", "ics"], P.loc[:"2019-12", ["rt_u3", "mem", "rt_gdp_yoy"]])
    rows.append({"lambda": lam, "half_life_months": np.log(0.5) / np.log(lam), "BIC_1978_2019": r.bic, "R2": r.rsquared,
                 "coef_memory": r.params["mem"], "t_memory": r.tvalues["mem"]})
G = pd.DataFrame(rows); G.to_csv(TAB / "inflation_memory_grid.csv", index=False); print(G.round(3).to_string())
best = G.loc[G.BIC_1978_2019.idxmin()]
P["mem"] = memory(best["lambda"]).reindex(P.index)
base = expanding_oos(P, "ics", ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy"], start="1990-01")
memg = expanding_oos(P, "ics", ["rt_u3", "mem", "rt_gdp_yoy"], start="1990-01")
both = expanding_oos(P, "ics", ["rt_u3", "rt_pce_yoy", "mem", "rt_gdp_yoy"], start="1990-01")
memg.to_csv(TAB / "gap_memory_ics.csv")
per = {"2010–2019": ("2010-01", "2019-12"), "2021–2022": ("2021-01", "2022-12"), "2023–2024": ("2023-01", "2024-12"),
       "2025–2026": ("2025-01", "2026-10")}
cmp_ = pd.DataFrame([{"period": k, "gap_M1_current_inflation": base.loc[a:b].gap.mean(), "gap_inflation_memory": memg.loc[a:b].gap.mean(),
                      "gap_both": both.loc[a:b].gap.mean(), "rmse_M1": rmse(base.loc[a:b].gap), "rmse_memory": rmse(memg.loc[a:b].gap)}
                     for k, (a, b) in per.items()])
cmp_["best_half_life_months"] = best.half_life_months
cmp_.to_csv(TAB / "inflation_memory_gap.csv", index=False); print(cmp_.round(2).to_string())
cw = clark_west(base.loc["1990":].gap, both.loc["1990":].gap, base.loc["1990":].pred, both.loc["1990":].pred)
pd.DataFrame([{"CW_stat_memory_added_to_M1": cw[0], "CW_p": cw[1], "best_lambda": best["lambda"], "half_life": best.half_life_months}]).to_csv(TAB / "inflation_memory_test.csv", index=False)
print("CW memory added to M1:", cw)

# ------------------------------------------------------------------ figures
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 2, figsize=(9.6, 3.3))
order = ["Trump-1 (2017–20)", "Biden (2021–24)", "Trump-2 (2025–26)"]
x = np.arange(3); w = .26
for i, (lean, col) in enumerate([("left", "#2a78d6"), ("center", "#8a93a1"), ("right", "#c8433f")]):
    vals = [piv.loc[a, lean] for a in order]
    ax[0].bar(x + (i - 1) * w, vals, w, color=col, label=f"{lean}-leaning outlets")
ax[0].set_xticks(x, ["Trump-1", "Biden", "Trump-2"]); ax[0].axhline(0, color="black", lw=.6)
ax[0].set_ylabel("AI net tone of economy headlines"); ax[0].legend(frameon=False, fontsize=7); ax[0].set_title("Coverage: modest swings by lean")
xp = np.arange(3)
ax[1].bar(xp - .18, party.ICS_Jun2022_phone, .36, color="#9ec5f4", label="June 2022 (Biden)")
ax[1].bar(xp + .18, party.ICS_May2026, .36, color="#1f4e8c", label="May 2026 (Trump-2)")
ax[1].set_xticks(xp, party.party); ax[1].set_ylabel("Michigan ICS"); ax[1].legend(frameon=False, fontsize=7)
ax[1].set_title("Sentiment: huge partisan swings")
fig.tight_layout(); fig.savefig(FIG / "fig_transition_test.png", dpi=200)

fig, ax = plt.subplots(figsize=(8.6, 3.1))
s = P.loc["2015-01":]
ax.plot(s.index.to_timestamp(), s.rt_pce_yoy, color="#8a93a1", lw=1, label="PCE inflation y/y (what models use)")
ax.plot(s.index.to_timestamp(), s.mem, color="#c8433f", lw=1.8, label=f"Inflation memory (half-life ≈ {best.half_life_months:.0f} months, estimated 1978–2019)")
ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=7.5, loc="upper left"); ax.set_title("Consumers remember inflation long after the rate falls")
fig.tight_layout(); fig.savefig(FIG / "fig_inflation_memory.png", dpi=200)
print("done")

# ------------------------------------------------------------------ C. aggregate supply vs sentiment by administration
Mm = pd.read_csv(PROC / "media_monthly.csv"); Mm["month"] = pd.PeriodIndex(Mm.month, freq="M"); Mm = Mm.set_index("month")
agg = []
for a, b, n in [("2017-02", "2020-12", "Trump-1 (2017–20)"), ("2021-02", "2024-12", "Biden (2021–24)"), ("2025-02", "2026-10", "Trump-2 (2025–26)")]:
    agg.append({"administration": n, "AI net tone": Mm.loc[a:b, "tone_net"].mean(), "FinBERT tone": Mm.loc[a:b, "tone_finbert"].mean(),
                "GDELT full-text tone": Mm.loc[a:b, "gd_economy_tone"].mean(), "Share of headlines on rising prices": Mm.loc[a:b, "sal_prices_rising"].mean(),
                "Michigan ICS (mean)": P.loc[a:b, "ics"].mean()})
pd.DataFrame(agg).to_csv(TAB / "transition_aggregate.csv", index=False); print(pd.DataFrame(agg).round(3))

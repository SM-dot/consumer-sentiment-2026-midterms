"""
14_components.py — Where inside the index is the pessimism, and what reasons do respondents give?
  (a) ICS components 2019 vs 2025–26: current/expected personal finances, business conditions 1y/5y, buying conditions
      for durables, plus the stated REASONS (high prices, high interest rates) — the "level vs rate" channel.
  (b) Decomposition of the 2019 -> 2025–26 change predicted by the household-pressure model (M1H2) by variable.
  (c) Partisan-composition back-of-envelope using Michigan's published party figures (explanation 3: measurement).
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

P = load_panel(); P["rt_d12_mort30"] = P.rt_mort30 - P.rt_mort30.shift(12)
U = pd.read_csv(ROOT / "data" / "raw" / "umich" / "all_tables.raw", skiprows=1)
U["date"] = pd.PeriodIndex.from_fields(year=U.yyyy, month=U.Month, freq="M"); U = U.set_index("date").apply(pd.to_numeric, errors="coerce")
b, n = ("2019-01", "2019-12"), ("2025-01", "2026-08")
comp = {"pago_r_all": "Personal finances vs a year ago (relative score)", "pexp_r_all": "Expected personal finances, 1 yr",
        "bus12_r_all": "Business conditions, next 12 months", "bus5_r_all": "Business conditions, next 5 years",
        "dur_r_all": "Buying conditions for large durables", "veh_r_all": "Buying conditions for vehicles",
        "hom_r_all": "Buying conditions for houses", "rinc_r_all": "Expected real income (income vs prices)",
        "durrn_hp_all": "Durables: bad time — prices too high (%)", "durrn_hr_all": "Durables: bad time — interest rates high (%)",
        "homrn_hp_all": "Homes: bad time — prices too high (%)", "homrn_hr_all": "Homes: bad time — interest rates high (%)",
        "pagorn_hp_all": "Worse off — higher prices (%)", "pagorn_ly_all": "Worse off — lower income (%)",
        "px1_med_all": "Expected inflation, next 12 months (median %)", "px5_med_all": "Expected inflation, 5–10 yrs (median %)",
        "govt_r_all": "Government economic policy (relative score)", "news_u_all": "Heard unfavorable business news (%)"}
rows = []
for c, lab in comp.items():
    if c in U:
        rows.append({"measure": lab, "var": c, "2019": U.loc[b[0]:b[1], c].mean(), "2022 (inflation peak yr)": U.loc["2022-01":"2022-12", c].mean(),
                     "2025–26": U.loc[n[0]:n[1], c].mean()})
C = pd.DataFrame(rows); C["change_vs_2019"] = C["2025–26"] - C["2019"]
C.to_csv(TAB / "components_reasons.csv", index=False); print(C.round(1).to_string())

# (b) M1H2 decomposition
fit = pd.read_csv(TAB / "m1h2_fullsample.csv", index_col=0)
xs = [v for v in fit.index if v != "const"]
dx = P.loc[n[0]:"2026-10", xs].mean() - P.loc[b[0]:b[1], xs].mean()
D = pd.DataFrame({"coef_2000_2019": fit.loc[xs, "coef"], "p": fit.loc[xs, "p"], "change": dx, "contribution": fit.loc[xs, "coef"] * dx})
act = P.loc[n[0]:"2026-10", "ics"].mean() - P.loc[b[0]:b[1], "ics"].mean()
D.loc["TOTAL predicted"] = [np.nan, np.nan, np.nan, D.contribution.sum()]
D.loc["Web-mode offset (UMich)"] = [np.nan, np.nan, np.nan, MODE_EFFECT_UMICH]
D.loc["ACTUAL change"] = [np.nan, np.nan, np.nan, act]
D.loc["Unexplained residual"] = [np.nan, np.nan, np.nan, act - D.loc["TOTAL predicted", "contribution"] - MODE_EFFECT_UMICH]
D.to_csv(TAB / "decomposition_m1h2.csv"); print(D.round(2))

# (c) Partisan composition (published Michigan figures, May 2026; Republican share range from the July 2026 report)
party = {"Democrats": 32.8, "Independents": 40.6, "Republicans": 84.6}
scen = []
for drop in [3, 5, 7]:
    # R share falls by `drop` pp, reallocated equally to D and I
    delta = -drop / 100 * party["Republicans"] + drop / 200 * party["Democrats"] + drop / 200 * party["Independents"]
    scen.append({"R_share_drop_pp": drop, "implied_ICS_change": delta})
pd.DataFrame(scen).to_csv(TAB / "partisan_composition.csv", index=False); print(pd.DataFrame(scen).round(2))

# figure: components
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
sub = C[C["var"].isin(["pago_r_all", "pexp_r_all", "bus12_r_all", "bus5_r_all", "dur_r_all", "rinc_r_all"])]
fig, ax = plt.subplots(figsize=(8, 3.2))
y = np.arange(len(sub))
ax.barh(y - .2, sub["2019"], height=.38, color="#9ec5f4", label="2019")
ax.barh(y + .2, sub["2025–26"], height=.38, color="#2a78d6", label="2025–26")
ax.set_yticks(y, sub.measure); ax.axvline(100, color="black", lw=.6); ax.invert_yaxis()
ax.set_xlabel("Relative score (100 = as many favorable as unfavorable)"); ax.legend(frameon=False)
ax.set_title("Index components: buying conditions and real-income expectations collapsed most")
fig.tight_layout(); fig.savefig(FIG / "fig_components.png", dpi=200)
r = U.loc["2010-01":, ["durrn_hp_all", "durrn_hr_all", "pagorn_hp_all"]].rolling(3).mean()
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(r.index.to_timestamp(), r.durrn_hp_all, color="#eb6834", label="Bad time to buy durables: prices high")
ax.plot(r.index.to_timestamp(), r.durrn_hr_all, color="#2a78d6", label="Bad time to buy durables: interest rates high")
ax.plot(r.index.to_timestamp(), r.pagorn_hp_all, color="#14171c", label="Worse off: higher prices")
pce = P.loc["2010-01":, "rt_pce_yoy"]
ax2 = ax.twinx(); ax2.plot(pce.index.to_timestamp(), pce, color="grey", ls="--", lw=1, label="PCE inflation y/y (rhs)"); ax2.set_ylabel("%")
ax.set_ylabel("% of respondents"); ax.legend(frameon=False, fontsize=7, loc="upper left"); ax2.legend(frameon=False, fontsize=7, loc="upper right")
ax.set_title("Price complaints stayed high after inflation fell: the level-vs-rate channel")
fig.tight_layout(); fig.savefig(FIG / "fig_level_vs_rate.png", dpi=200)
print("done")

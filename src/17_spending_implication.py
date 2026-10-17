"""
17_spending_implication.py — Practical implication for forecasting/risk: does sentiment still predict spending?

Target: real PCE growth over the NEXT 6 months (annualised, %), DPCERX (current vintage — a limitation we state).
BEA's monthly flat file carries DPCERX from 2007 only, so estimation starts 2007-01 and OOS evaluation starts 2015-01.
Information at month t: ICS_t, and the real-time macro set (U-3, PCE inflation, GDP).
Models (expanding-window OOS from 2015, evaluated separately on 2015–2019 and 2022–2026; 2020–21 excluded as
pandemic outliers from evaluation, not from estimation):
  S0 macro only | S1 macro + ICS | S2 macro + fundamentals-consistent ICS (= M1 prediction) | S3 macro + ICS gap
Question: did the 2022–26 gap (pessimism unexplained by fundamentals) carry information about spending? If not, a
forecaster or risk manager should down-weight the gap component of sentiment.
"""
import numpy as np, pandas as pd, sys
from lib import *
sys.path.insert(0, str(ROOT / "src"))
import importlib
bd = importlib.import_module("03_build_dataset")

P = load_panel()
c = bd.bea("DPCERX").reindex(P.index)
P["pce_fwd6"] = 100 * ((c.shift(-6) / c) ** 2 - 1)            # next-6-month real PCE growth, annualised
g = pd.read_csv(TAB / "gap_m1_ics.csv"); g["month"] = pd.PeriodIndex(g.month, freq="M"); g = g.set_index("month")
P["ics_fund"] = g.pred; P["ics_gap"] = g.gap
ECON = ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy"]
specs = {"S0 macro only": ECON, "S1 + ICS": ECON + ["ics"], "S2 + fundamentals-consistent ICS": ECON + ["ics_fund"],
         "S3 + ICS gap": ECON + ["ics_gap"], "S4 + ICS fund. & gap": ECON + ["ics_fund", "ics_gap"]}
D = P.loc["2007-01":"2026-02"].copy()
res = {k: expanding_oos(D, "pce_fwd6", xs, start="2015-01", min_train=96) for k, xs in specs.items()}
rows = []
for win, (a, b) in {"2015–2019": ("2015-01", "2019-12"), "2022–2026": ("2022-01", "2026-02")}.items():
    base = res["S0 macro only"].loc[a:b]
    for k, r in res.items():
        r = r.loc[a:b]; cidx = r.index.intersection(base.index)
        row = {"window": win, "model": k, "n": len(r), "rmse": rmse(r.gap), "mean_error": r.gap.mean()}
        if k != "S0 macro only":
            row["CW_p_vs_macro"] = clark_west(base.loc[cidx].gap, r.loc[cidx].gap, base.loc[cidx].pred, r.loc[cidx].pred)[1]
        rows.append(row)
R = pd.DataFrame(rows); R.to_csv(TAB / "spending_forecast.csv", index=False); print(R.round(3).to_string())
fit_pre = ols_hac(D.loc["2007-01":"2019-12", "pce_fwd6"], D.loc["2007-01":"2019-12", ECON + ["ics"]])
fit_post = ols_hac(D.loc["2022-01":"2026-02", "pce_fwd6"], D.loc["2022-01":"2026-02", ECON + ["ics"]])
pd.DataFrame({"coef_ICS_2007_2019": [fit_pre.params["ics"]], "p_pre": [fit_pre.pvalues["ics"]],
              "coef_ICS_2022_2026": [fit_post.params["ics"]], "p_post": [fit_post.pvalues["ics"]],
              "mean_real_pce_growth_2022_26": [D.loc["2022-01":"2026-02", "pce_fwd6"].mean()],
              "mean_ICS_2022_26": [D.loc["2022-01":"2026-02", "ics"].mean()]}).to_csv(TAB / "spending_coef_shift.csv", index=False)
print(pd.read_csv(TAB / "spending_coef_shift.csv").round(3))

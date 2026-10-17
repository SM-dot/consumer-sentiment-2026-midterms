"""
22_region_seasonality.py — Two brief requirements not yet covered.
  (a) GEOGRAPHY: decline by Census region (Michigan monthly sub-indices: Northeast, North Central, South, West).
  (b) SEASONALITY: Michigan's ICS is not seasonally adjusted. Add calendar-month dummies to the economic-only model and
      re-run the real-time out-of-sample gap; joint F-test (HAC) of the month dummies on 1978–2019.
"""
import numpy as np, pandas as pd
from lib import *

P = load_panel()
reg = {"Northeast": "ics_ne", "North Central (Midwest)": "ics_nc", "South": "ics_s", "West": "ics_w"}
U = pd.read_csv(ROOT / "data" / "raw" / "umich" / "all_tables.raw", skiprows=1)
U["date"] = pd.PeriodIndex.from_fields(year=U.yyyy, month=U.Month, freq="M"); U = U.set_index("date").apply(pd.to_numeric, errors="coerce")
rows = [{"region": k, "ICS_2019": U.loc["2019-01":"2019-12", v].mean(), "ICS_2025_26": U.loc["2025-01":"2026-08", v].mean()} for k, v in reg.items()]
R = pd.DataFrame(rows); R["change"] = R.ICS_2025_26 - R.ICS_2019; R["pct_change"] = 100 * R.change / R.ICS_2019
R.to_csv(TAB / "decline_by_region.csv", index=False); print(R.round(1))

M1 = ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy"]
for m in range(2, 13):
    P[f"mon{m}"] = (P.index.month == m).astype(int)
MD = [f"mon{m}" for m in range(2, 13)]
r = ols_hac(P.loc[:"2019-12", "ics"], P.loc[:"2019-12", M1 + MD])
ft = r.f_test(" = ".join(MD[:1]) + " = 0" if False else ", ".join(f"{d} = 0" for d in MD))
g0 = expanding_oos(P, "ics", M1, start="1990-01"); g1 = expanding_oos(P, "ics", M1 + MD, start="1990-01")
out = pd.DataFrame([{"joint_F_month_dummies": float(np.squeeze(ft.fvalue)), "p": float(ft.pvalue),
                     "gap_2025_26_without": g0.loc["2025-01":].gap.mean(), "gap_2025_26_with_month_dummies": g1.loc["2025-01":].gap.mean(),
                     "oos_rmse_1990_2019_without": rmse(g0.loc[:"2019-12"].gap), "oos_rmse_with": rmse(g1.loc[:"2019-12"].gap)}])
out.to_csv(TAB / "seasonality_test.csv", index=False); print(out.round(3).T)

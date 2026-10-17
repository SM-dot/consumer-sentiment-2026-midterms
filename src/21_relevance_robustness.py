"""
21_relevance_robustness.py — Do the media conclusions depend on the AI relevance filter?

Main pipeline keeps items passing the keyword filter AND the NLI relevance gate (p > 0.5): against the human labels this
set is 98% precise but keeps only ~54% of relevant items. Here we rebuild the key results with the keyword filter alone
(90% precise, 100% recall) and compare:
  (1) correlation of the monthly AI net-tone index under the two filters;
  (2) partisan-slant diff-in-diff (right-leaning x Democratic president, outlet + month FE);
  (3) transition test: right/left outlet tone swings Biden -> Trump-2, and aggregate tone by administration.
"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from lib import *

CORP = load_corpus(); A = pd.read_csv(PROC / "ai_codes.csv")
D0 = CORP.merge(A, on="item_id")
D0["tone_num"] = D0.ai_tone.map({"negative": -1, "neutral": 0, "positive": 1})
D0["m"] = D0.date.dt.to_period("M")
H = pd.read_excel(ROOT / "labeling" / "annotator_A.xlsx", sheet_name="items", dtype=str).set_index("item_id")
filters = {"keyword + NLI gate (main)": lambda d: d[d.relevant_kw & (d.ai_relevance_p > 0.5)],
           "keyword only (robustness)": lambda d: d[d.relevant_kw]}
rows, idx = [], {}
for name, f in filters.items():
    D = f(D0); N = D[D.platform == "news"]
    idx[name] = N.groupby("m").tone_num.mean()
    O = N[N.query_type.eq("outlet")].copy()
    O["lean"] = O.outlet_lean.replace({"lean_left": "left", "lean_right": "right"}); O = O[O.lean.isin(["left", "center", "right"])]
    O["ms"] = O.m.astype(str)
    O["dem"] = ((O.m >= pd.Period("2021-01", "M")) & (O.m <= pd.Period("2024-12", "M"))).astype(int)
    O["right_dem"] = ((O.lean == "right") & (O.dem == 1)).astype(int)
    s = smf.ols("tone_num ~ right_dem + C(source) + C(ms)", data=O).fit(cov_type="cluster", cov_kwds={"groups": O["ms"]})
    O["admin"] = np.select([O.m < pd.Period("2021-01", "M"), O.m < pd.Period("2025-01", "M")], ["T1", "B"], "T2")
    for l in ["left", "right"]:
        O[f"{l}_T2"] = ((O.lean == l) & (O.admin == "T2")).astype(int); O[f"{l}_T1"] = ((O.lean == l) & (O.admin == "T1")).astype(int)
    t = smf.ols("tone_num ~ left_T1 + left_T2 + right_T1 + right_T2 + C(source) + C(ms)", data=O).fit(cov_type="cluster", cov_kwds={"groups": O["ms"]})
    agg = {a: N[(N.m >= pd.Period(x, "M")) & (N.m <= pd.Period(y, "M"))].groupby("m").tone_num.mean().mean()
           for a, x, y in [("Biden", "2021-02", "2024-12"), ("Trump-2", "2025-02", "2026-10")]}
    h = H.join(D0.set_index("item_id")[["relevant_kw", "ai_relevance_p"]], how="left")
    kept = f(D0.assign(item_id=D0.item_id)).item_id
    hh = H.loc[H.index.intersection(kept)]
    rows.append({"filter": name, "items_used": len(N), "human_precision_on_validation_items": (hh.relevant == "1").mean(),
                 "slant_right_x_DemPres": s.params["right_dem"], "slant_p": s.pvalues["right_dem"],
                 "right_outlets_T2_vs_Biden": t.params["right_T2"], "right_p": t.pvalues["right_T2"],
                 "left_outlets_T2_vs_Biden": t.params["left_T2"], "left_p": t.pvalues["left_T2"],
                 "aggregate_tone_Biden": agg["Biden"], "aggregate_tone_Trump2": agg["Trump-2"]})
R = pd.DataFrame(rows)
both = pd.concat(idx, axis=1).dropna()
R["monthly_tone_corr_with_main"] = [1.0, both.corr().iloc[0, 1]]
R.to_csv(TAB / "relevance_robustness.csv", index=False); print(R.round(3).T)

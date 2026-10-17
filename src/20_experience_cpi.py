"""
20_experience_cpi.py — Two depth tests for 'what the official numbers miss'.

A. EXPERIENCE EFFECTS (CPI inflation, Philadelphia Fed history from 1947; sample 2013–2026) (Malmendier & Nagel 2016, 'Learning from inflation experiences', QJE).
   Each age group g at month t has a lifetime-experienced inflation
       E_{g,t} = Σ_{k=1..age_g·12} w_k π_{t-k},   w_k ∝ (age_g·12 − k)^θ,
   so recent inflation gets more weight, and MORE weight for the young (shorter lives). θ = 1.5 follows the
   original estimates; θ ∈ {1, 3} as robustness. Ages: midpoints of Michigan's groups (26, 44, 66).
   Test (within-month, group FE + month FE, Driscoll–Kraay SE): do groups with higher experienced inflation
   (i) expect higher inflation (Michigan median 1-yr expectation) and (ii) report lower sentiment, holding the month
   fixed? Month FE absorb current inflation, national news and all macro data, so only lifetime experience varies.
B. NECESSITIES vs HEADLINE CPI since January 2021: groceries (food at home), shelter, gasoline vs all items.
"""
import json, glob
import numpy as np, pandas as pd, statsmodels.api as sm
from lib import *
import importlib
bd = importlib.import_module("03_build_dataset")

# ------------------------------------------------------------------ A. experience effects
# Long CPI history (Philadelphia Fed RTDSM, latest vintage, from 1947) so every age group has a full lifetime of data
cx = pd.read_excel(ROOT / "data" / "raw" / "philly" / "pcpiMvMd.xlsx")
p = pd.Series(cx.iloc[:, -1].values, index=pd.PeriodIndex([d.replace(":", "-") for d in cx.DATE.astype(str)], freq="M")).astype(float)
p = p.reindex(pd.period_range("1947-01", "2026-10", freq="M"))
pi = 1200 * np.log(p / p.shift(1))                                        # annualised monthly CPI inflation
pi = pi.shift(1)                                                          # public with a 1-month lag
AGES = {"18–34": 26, "35–54": 44, "55+": 66}


def experienced(age_years, theta):
    n = int(age_years * 12)
    out = pd.Series(np.nan, index=pi.index)
    k = np.arange(1, n + 1)
    w = (n - k + 1.0) ** theta; w /= w.sum()
    v = pi.values
    for t in range(len(v)):
        if t - n < 0: continue
        seg = v[t - n:t][::-1]                    # k = 1..n months back
        if np.isnan(seg).any(): continue
        out.iloc[t] = float(np.dot(w, seg))
    return out


A = pd.read_csv(PROC / "umich_by_age_3mma.csv")
A["date"] = pd.PeriodIndex(A.date, freq="M")
P = load_panel()
mon = {"18–34": "ics_a1834", "35–54": "ics_a3554", "55+": "ics_a5597"}
res = []
for theta in [1.0, 1.5, 3.0]:
    rows = []
    for g, age in AGES.items():
        e = experienced(age, theta)
        sub = A[A.group == g].set_index("date")
        df = pd.DataFrame({"px_median": sub.px_median, "ics_3mma": sub.ics}).join(e.rename("exp_infl"))
        df["group"] = g; rows.append(df)
    D = pd.concat(rows).reset_index().rename(columns={"index": "date"})
    D = D[(D.date >= pd.Period("2013-01", "M")) & (D.date <= pd.Period("2026-08", "M"))].dropna()   # all groups have full lifetimes from 2013
    for y in ["px_median", "ics_3mma"]:
        dd = D.copy()
        for v in [y, "exp_infl"]:
            dd[v + "_w"] = dd[v] - dd.groupby("date")[v].transform("mean") - dd.groupby("group")[v].transform("mean") + dd[v].mean()
        dd = dd.sort_values(["date", "group"])
        r = sm.OLS(dd[y + "_w"], dd[["exp_infl_w"]]).fit(cov_type="hac-groupsum", cov_kwds={"time": dd["date"].astype(str).factorize()[0], "maxlags": 6})
        res.append({"theta": theta, "outcome": {"px_median": "1-yr inflation expectation (median %)", "ics_3mma": "Sentiment (ICS, 3mma)"}[y],
                    "coef_per_pp_experienced": r.params["exp_infl_w"], "se_DK": r.bse["exp_infl_w"], "p": r.pvalues["exp_infl_w"], "n": int(r.nobs)})
    if theta == 1.5:
        D15 = D.copy()
R = pd.DataFrame(res); R.to_csv(TAB / "experience_effects.csv", index=False); print(R.round(3).to_string())
snap = D15[D15.date.isin([pd.Period("2019-12", "M"), pd.Period("2022-12", "M"), pd.Period("2026-08", "M")])].pivot(index="date", columns="group", values="exp_infl")
snap.to_csv(TAB / "experienced_inflation_snapshot.csv"); print(snap.round(2))
# How much of the young-vs-old differential decline does experience explain? (θ = 1.5 coefficient)
b_ics = R[(R.theta == 1.5) & (R.outcome.str.startswith("Sentiment"))].coef_per_pp_experienced.iloc[0]
d_exp = {g: D15[D15.group == g].set_index("date").exp_infl for g in AGES}
chg = {g: d_exp[g].loc["2025-01":"2026-08"].mean() - d_exp[g].loc["2019-01":"2019-12"].mean() for g in AGES}
dec = pd.read_csv(TAB / "decline_by_age.csv").set_index("group")
diff_actual = dec.loc["18–34", "change"] - dec.loc["55+", "change"]
diff_pred = b_ics * (chg["18–34"] - chg["55+"])
pd.DataFrame([{"rise_in_experienced_inflation_18_34": chg["18–34"], "rise_55_plus": chg["55+"],
               "actual_extra_decline_young_vs_old": diff_actual, "predicted_by_experience": diff_pred,
               "share_explained": diff_pred / diff_actual}]).to_csv(TAB / "experience_young_vs_old.csv", index=False)
print("young-vs-old extra decline", round(diff_actual, 1), "predicted by experience", round(diff_pred, 1))

# ------------------------------------------------------------------ B. necessities vs headline CPI
B = {}
for f in glob.glob(str(ROOT / "data" / "raw" / "bls" / "*.json")):
    for s in json.load(open(f))["Results"]["series"]:
        for o in s["data"]:
            if o["period"].startswith("M") and o["period"] != "M13":
                try: B.setdefault(s["seriesID"], {})[pd.Period(f"{o['year']}-{o['period'][1:]}", "M")] = float(o["value"])
                except ValueError: pass
names = {"CUSR0000SA0": "All items (headline CPI)", "CUSR0000SAF11": "Food at home (groceries)", "CUSR0000SAH1": "Shelter (rent & owners' equivalent rent)",
         "CUSR0000SETB01": "Gasoline", "CES0500000003": "Average hourly earnings (nominal)"}
rows = []
for k, lab in names.items():
    s = pd.Series(B[k]).sort_index()
    rows.append({"series": lab, "Jan 2021 → Sep 2026 (%)": 100 * (s[pd.Period("2026-09", "M")] / s[pd.Period("2021-01", "M")] - 1)})
N = pd.DataFrame(rows); N.to_csv(TAB / "necessities_vs_headline.csv", index=False); print(N.round(1))

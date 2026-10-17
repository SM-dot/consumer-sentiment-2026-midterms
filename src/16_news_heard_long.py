"""
16_news_heard_long.py — 47-year test with Michigan's own news-RECALL measure (Tables 23–24), independent of our corpus.

  (1) Excess bad-news recall: share hearing unfavourable news regressed on real-time fundamentals 1978–2019, then the
      out-of-sample residual for 2020–2026 ("more bad news recalled than the economy warrants?").
  (2) Does recall add out-of-sample predictive content for ICS beyond U-3/PCE/GDP? (expanding window from 1990,
      Clark–West), and does it close the 2025–26 gap?
  (3) Granger both directions on monthly changes (1978–2026), lag by BIC.
Caveat: recall and sentiment come from the same interview; a gloomy respondent may recall bad news (reverse causality).
"""
import numpy as np, pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.tsa.api import VAR
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

P = load_panel()
ECON = ["rt_u3", "rt_pce_yoy", "rt_gdp_yoy"]
P["news_net_bad"] = P.news_u_all - P.news_f_all
P["news_net_bad_l1"] = P.news_net_bad.shift(1)
P["news_u_l1"] = P.news_u_all.shift(1)

# (1) excess bad-news recall
ex = expanding_oos(P, "news_net_bad", ECON + ["web_share"], start="2000-01")
ex.to_csv(TAB / "news_recall_excess.csv")
per = {"2010–2019": ("2010-01", "2019-12"), "2021–2022": ("2021-01", "2022-12"), "2023–2024": ("2023-01", "2024-12"),
       "2025": ("2025-01", "2025-12"), "2026": ("2026-01", "2026-10")}
rows = [{"period": k, "actual_net_bad_news": ex.loc[a:b].actual.mean(), "predicted_from_fundamentals": ex.loc[a:b].pred.mean(),
         "excess_bad_news_recall": ex.loc[a:b].gap.mean(), "share_above_95PI": (ex.loc[a:b].actual > ex.loc[a:b].hi95).mean()} for k, (a, b) in per.items()]
E = pd.DataFrame(rows); E.to_csv(TAB / "news_recall_excess_summary.csv", index=False); print(E.round(2))

# (2) predictive content
base = expanding_oos(P, "ics", ECON, start="1990-01")
out = []
for v in ["news_net_bad_l1", "news_u_l1", "news_net_bad"]:
    g = expanding_oos(P, "ics", ECON + [v], start="1990-01")
    c = g.index.intersection(base.index)
    cw = clark_west(base.loc[c].gap, g.loc[c].gap, base.loc[c].pred, g.loc[c].pred)
    r = ols_hac(P.loc[:"2019-12", "ics"], P.loc[:"2019-12", ECON + [v]])
    out.append({"recall_measure": v, "coef_1978_2019": r.params[v], "p": r.pvalues[v], "rmse_base": rmse(base.loc[c].gap),
                "rmse_with_recall": rmse(g.loc[c].gap), "CW_stat": cw[0], "CW_p": cw[1],
                "gap_2025_26_base": base.loc["2025-01":].gap.mean(), "gap_2025_26_with_recall": g.loc["2025-01":].gap.mean()})
O = pd.DataFrame(out); O.to_csv(TAB / "news_recall_predictive.csv", index=False); print(O.round(3).to_string())

# (3) Granger both directions
Z = pd.DataFrame({"d_ics": P.ics.diff(), "d_news": P.news_net_bad.diff()}).loc["1978-03":"2026-08"].dropna()
p = max(1, int(VAR(Z).select_order(12).bic or 1))
g1 = grangercausalitytests(Z[["d_ics", "d_news"]], [p])[p][0]["ssr_ftest"]
g2 = grangercausalitytests(Z[["d_news", "d_ics"]], [p])[p][0]["ssr_ftest"]
pd.DataFrame([{"lag_BIC": p, "recall->sentiment_F": g1[0], "recall->sentiment_p": g1[1], "sentiment->recall_F": g2[0],
               "sentiment->recall_p": g2[1], "n": len(Z)}]).to_csv(TAB / "news_recall_granger.csv", index=False)
print("Granger lag", p, "recall->sent p", round(g1[1], 4), "sent->recall p", round(g2[1], 4))

plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(8, 3))
s = ex.loc["2005-01":]
ax.fill_between(s.index.to_timestamp(), s.lo95, s.hi95, color="#9db4d6", alpha=.35, label="95% PI from fundamentals")
ax.plot(s.index.to_timestamp(), s.pred, color="#1f4e8c", label="Predicted from U-3, PCE, GDP")
ax.plot(s.index.to_timestamp(), s.actual, color="#b2382b", label="Actual: % unfavourable − % favourable news heard")
ax.legend(frameon=False, fontsize=7); ax.set_title("Bad-news recall vs what fundamentals predict (Michigan Tables 23)")
fig.tight_layout(); fig.savefig(FIG / "fig_news_recall.png", dpi=200)

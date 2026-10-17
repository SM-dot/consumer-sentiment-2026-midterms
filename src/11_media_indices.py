"""
11_media_indices.py — Monthly media measures + bias benchmarks (research question 1).

Monthly indices (data/processed/media_monthly.csv)
  SUPPLY  (news headlines, AI-coded): tone_net, tone_score, emotional_share, salience_<topic>, level_frame_share,
          household_frame_share, forecast_frame_share, blame_admin_share; same tone from FinBERT & dictionary.
  SUPPLY  (GDELT full population): gd_<topic>_share (articles matching topic / all monitored US articles), gd_<topic>_tone.
  ENGAGEMENT (social): hn_<query>_per_1k (HN items mentioning query per 1,000 items sampled baseline), social tone.
  EXPOSURE/RECALL (Michigan): news_unfav, news_fav, news_rel, unfav price/emp/govt news heard.
Bias benchmarks (outputs/tables/bias_*.csv)
  B1 Negativity asymmetry : tone_t on positive vs negative parts of real-time macro news  (Soroka-style)
  B2 Selective salience   : 'prices rising' vs 'inflation falling' coverage when measured inflation falls vs rises
  B3 Partisan slant (DiD) : outlet-query tone, outlet FE + MONTH FE (facts held fixed), lean x party-of-president
  B4 Excess negativity    : residual of tone on fundamentals -> candidate 'bias' series used in 12_media_models
"""
import glob, re
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from lib import load_corpus, ROOT, PROC, TAB, load_panel, ols_hac

RAW = ROOT / "data" / "raw"
MONTHS = pd.period_range("2017-01", "2026-10", freq="M")


def coded_news():
    C = load_corpus()
    A = pd.read_csv(PROC / "ai_codes.csv")
    D = C.merge(A, on="item_id")
    D = D[(D.ai_relevance_p > 0.5) & D.relevant_kw]
    D["m"] = D.date.dt.to_period("M")
    D["tone_num"] = D.ai_tone.map({"negative": -1, "neutral": 0, "positive": 1})
    D["fin_num"] = D.finbert_tone.map({"negative": -1, "neutral": 0, "positive": 1})
    D["dict_num"] = D.dict_tone.map({"negative": -1, "neutral": 0, "positive": 1})
    return D


def agg(D, prefix=""):
    if D.empty:
        cols = ["n_items", "tone_net", "tone_score", "tone_finbert", "tone_dict", "emotional_share", "sal_prices_rising", "sal_layoffs", "sal_labor_bad"]
        return pd.DataFrame(index=MONTHS, columns=[prefix + c for c in cols], dtype=float)
    g = D.groupby("m")
    out = pd.DataFrame({
        "n_items": g.size(), "tone_net": g.tone_num.mean(), "tone_score": g.ai_tone_score.mean(),
        "tone_finbert": g.fin_num.mean(), "tone_dict": g.dict_num.mean(),
        "emotional_share": g.ai_emotional.apply(lambda s: (s >= 1).mean()),
        "emotional_strong_share": g.ai_emotional.apply(lambda s: (s >= 2).mean()),
        "household_frame_share": g.ai_unit_frame.apply(lambda s: s.isin(["household", "both"]).mean()),
        "forecast_frame_share": g.ai_time_frame.apply(lambda s: (s == "forecast").mean()),
        "blame_admin_share": g.apply(lambda x: ((x.ai_attr_target == "president_admin") & (x.ai_attr_direction == "blame")).mean()),
        "credit_admin_share": g.apply(lambda x: ((x.ai_attr_target == "president_admin") & (x.ai_attr_direction == "credit")).mean()),
    })
    pr = D[D.ai_topic.isin(["prices_rising", "inflation_falling"])].groupby("m")
    out["level_frame_share"] = pr.ai_price_frame.apply(lambda s: s.isin(["level", "both"]).mean())
    for t in ["prices_rising", "inflation_falling", "layoffs", "hiring", "growth", "recession_risk", "housing_rates", "trade_tariffs", "markets", "policy_fed"]:
        out["sal_" + t] = g.ai_topic.apply(lambda s: (s == t).mean())
    out["sal_labor_bad"] = out.sal_layoffs + out.sal_recession_risk
    return out.add_prefix(prefix).reindex(MONTHS)


def gdelt_monthly():
    rows = {}
    for f in glob.glob(str(RAW / "gdelt" / "tl_*_all.csv")):
        key = re.search(r"tl_(.+)_(timelinevolraw|timelinetone)_all", f)
        topic, mode = key.group(1), key.group(2)
        try:
            d = pd.read_csv(f)
        except Exception:
            continue
        if d.empty or "Date" not in d.columns.str.replace("﻿", ""): continue
        d.columns = [c.replace("﻿", "") for c in d.columns]
        d["m"] = pd.to_datetime(d.Date).dt.to_period("M")
        if mode == "timelinevolraw":
            p = d.pivot_table(index="m", columns="Series", values="Value", aggfunc="sum")
            rows[f"gd_{topic}_share"] = 1000 * p["Article Count"] / p["Total Monitored Articles"]   # per 1,000 US articles
        else:
            rows[f"gd_{topic}_tone"] = d.groupby("m").Value.mean()
    return pd.DataFrame(rows).reindex(MONTHS)


def gdelt_outlets():
    rows = []
    for f in glob.glob(str(RAW / "gdelt" / "out_*_timelinetone_all.csv")):
        dom = re.search(r"out_(.+)_timelinetone", f).group(1).replace("_", ".")
        try:
            d = pd.read_csv(f); d.columns = [c.replace("﻿", "") for c in d.columns]
        except Exception:
            continue
        if d.empty: continue
        d["m"] = pd.to_datetime(d.Date).dt.to_period("M")
        for m, v in d.groupby("m").Value.mean().items():
            rows.append({"outlet": dom, "m": m, "gd_tone": v})
    return pd.DataFrame(rows)


def hn_monthly():
    p = RAW / "social" / "hn_counts.csv"
    if not p.exists(): return pd.DataFrame(index=MONTHS)
    h = pd.read_csv(p); h["m"] = pd.PeriodIndex(h.month, freq="M")
    w = h.pivot_table(index="m", columns=["query", "tag"], values="hits", aggfunc="sum")
    w.columns = [f"hn_{q.replace(' ', '_')}_{t}" for q, t in w.columns]
    return w.reindex(pd.period_range("2010-01", "2026-10", freq="M"))


def lean_group(l):
    return {"left": "left", "lean_left": "left", "right": "right", "lean_right": "right", "center": "center"}.get(l, "other")


def president(m):
    return "D" if pd.Period("2021-01", "M") <= m <= pd.Period("2024-12", "M") else "R"


def main():
    P = load_panel()
    D = coded_news()
    news = D[D.platform == "news"]
    M = agg(news)
    M = M.join(agg(D[D.source == "news.ycombinator.com"], "hn_")[["hn_n_items", "hn_tone_net", "hn_sal_prices_rising", "hn_sal_layoffs"]])
    M = M.join(agg(D[D.source == "mastodon"], "md_")[["md_n_items", "md_tone_net", "md_emotional_share"]])
    M = M.join(gdelt_monthly())
    M = M.join(P[["news_u_all", "news_f_all", "news_r_all", "newsrn_u_pri_all", "newsrn_u_emp_all", "newsrn_u_govt_all", "newsrn_u_trd_all"]].reindex(MONTHS))
    M.index.name = "month"
    M.to_csv(PROC / "media_monthly.csv")
    hn_monthly().to_csv(PROC / "hn_monthly_counts.csv")

    # ---------------- B1: negativity asymmetry in coverage SUPPLY
    X = P.reindex(MONTHS)
    X["tone_net"] = M.tone_net
    # real-time macro 'news': improvement = falling unemployment, falling inflation, rising growth (sign-aligned, z-scored)
    dn = pd.DataFrame({"du": -(X.rt_u3 - X.rt_u3.shift(1)), "dpi": -(X.rt_pce_yoy - X.rt_pce_yoy.shift(1)),
                       "dg": X.rt_gdp_yoy - X.rt_gdp_yoy.shift(1)})
    dn = (dn - dn.mean()) / dn.std()
    X["news_idx"] = dn.mean(axis=1)
    X["good"], X["bad"] = X.news_idx.clip(lower=0), X.news_idx.clip(upper=0)
    X["tone_lag"] = X.tone_net.shift(1)
    rows = []
    for tone_var in ["tone_net", "tone_finbert", "tone_dict"]:
        X["y"] = M[tone_var]; X["ylag"] = X.y.shift(1)
        r = ols_hac(X["y"], X[["good", "bad", "ylag", "rt_u3", "rt_pce_yoy", "rt_gdp_yoy"]], lags=6)
        wald = r.t_test("good = bad")
        rows.append({"tone_measure": tone_var, "b_good": r.params["good"], "p_good": r.pvalues["good"], "b_bad": r.params["bad"],
                     "p_bad": r.pvalues["bad"], "asymmetry_ratio_bad_over_good": abs(r.params["bad"]) / max(abs(r.params["good"]), 1e-9),
                     "p_equal": float(wald.pvalue), "n": int(r.nobs)})
    pd.DataFrame(rows).to_csv(TAB / "bias_B1_asymmetry.csv", index=False); print(pd.DataFrame(rows).round(3))

    # ---------------- B2: selective salience of inflation coverage
    X["infl_falling_data"] = (X.rt_pce_yoy.diff() < 0).astype(int)
    pr = news[news.ai_topic.isin(["prices_rising", "inflation_falling"])].groupby("m").ai_topic.apply(lambda s: (s == "inflation_falling").mean())
    X["share_falling_cov"] = pr.reindex(MONTHS)
    b2 = X.dropna(subset=["share_falling_cov"]).groupby("infl_falling_data").share_falling_cov.agg(["mean", "count"])
    b2.index = b2.index.map({0: "inflation rose (latest release)", 1: "inflation fell (latest release)"})
    r = ols_hac(X["share_falling_cov"], X[["infl_falling_data"]], lags=6)
    b2["diff_coef"], b2["diff_p"] = r.params["infl_falling_data"], r.pvalues["infl_falling_data"]
    b2.to_csv(TAB / "bias_B2_salience.csv"); print(b2.round(3))

    # ---------------- B3: partisan slant, same-month comparison across outlets
    O = news[news.query_type.eq("outlet")].copy() if "query_type" in news else pd.DataFrame()
    if len(O):
        O["lean"] = O.outlet_lean.map(lean_group); O = O[O.lean.isin(["left", "right", "center"])]
        O["pres"] = O.m.map(president); O["right"] = (O.lean == "right").astype(int); O["dem_pres"] = (O.pres == "D").astype(int)
        O["ms"] = O.m.astype(str)
        res = {}
        for y in ["tone_num", "ai_tone_score", "fin_num", "dict_num"]:
            mod = smf.ols(f"{y} ~ right:dem_pres + C(source) + C(ms)", data=O).fit(cov_type="cluster", cov_kwds={"groups": O["ms"]})
            res[y] = {"slant_coef_right_x_DemPres": mod.params["right:dem_pres"], "se": mod.bse["right:dem_pres"],
                      "p": mod.pvalues["right:dem_pres"], "n": int(mod.nobs)}
        cell = O.groupby(["pres", "lean"]).tone_num.agg(["mean", "count"]).unstack()
        cell.to_csv(TAB / "bias_B3_cells.csv")
        pd.DataFrame(res).T.to_csv(TAB / "bias_B3_slant.csv"); print(pd.DataFrame(res).T.round(4)); print(cell.round(3))
        # attribution: blame of the president by lean x party of president
        O["blame_admin"] = ((O.ai_attr_target == "president_admin") & (O.ai_attr_direction == "blame")).astype(int)
        O.groupby(["pres", "lean"]).blame_admin.mean().unstack().to_csv(TAB / "bias_B3_blame_cells.csv")
    G = gdelt_outlets()
    if len(G):
        G["lean"] = G.outlet.map(lambda d: lean_group(__import__("importlib").import_module("06_build_corpus").tier_lean(d)[1]))
        G["pres"] = G.m.map(president); G = G[G.lean.isin(["left", "right", "center"])]
        G["right"] = (G.lean == "right").astype(int); G["dem_pres"] = (G.pres == "D").astype(int); G["ms"] = G.m.astype(str)
        mod = smf.ols("gd_tone ~ right:dem_pres + C(outlet) + C(ms)", data=G).fit(cov_type="cluster", cov_kwds={"groups": G["ms"]})
        pd.DataFrame({"coef": [mod.params["right:dem_pres"]], "se": [mod.bse["right:dem_pres"]], "p": [mod.pvalues["right:dem_pres"]],
                      "n": [int(mod.nobs)]}, index=["GDELT full-text tone"]).to_csv(TAB / "bias_B3_slant_gdelt.csv")
        G.groupby(["pres", "lean"]).gd_tone.mean().unstack().to_csv(TAB / "bias_B3_gdelt_cells.csv")

    # ---------------- B4: excess negativity (tone not explained by fundamentals)
    F = X[["rt_u3", "rt_pce_yoy", "rt_gdp_yoy", "rt_cum3y_infl", "rt_mort30"]].copy(); F["tone"] = M.tone_net
    ok = F.dropna()
    r = sm.OLS(ok.tone, sm.add_constant(ok.drop(columns="tone"))).fit()
    M["tone_fundamental"] = r.predict(sm.add_constant(F.drop(columns="tone"))).reindex(MONTHS)
    M["excess_negativity"] = -(M.tone_net - M.tone_fundamental)       # >0 = more negative than fundamentals imply
    pd.DataFrame({"coef": r.params, "p": r.pvalues}).assign(R2=r.rsquared, n=r.nobs).to_csv(TAB / "bias_B4_tone_on_fundamentals.csv")
    M.to_csv(PROC / "media_monthly.csv")
    print("B4 R2 of tone on fundamentals:", round(r.rsquared, 3))


if __name__ == "__main__":
    main()

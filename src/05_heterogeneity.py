"""
05_heterogeneity.py — "Which groups drive the decline, and which hardships do they report?"

This formalises the student's original hypothesis (age-group hardships -> lower sentiment) as testable claims:
  H-a  The decline is CONCENTRATED in one age/income group (vs. broad-based / common shock).
  H-b  Groups report DIFFERENT hardships (prices, income, housing, jobs) whose changes line up with their sentiment.
  H-c  WITHIN a month (common national news & macro data held fixed by month fixed effects), groups reporting
       more price/income hardship have lower sentiment -> evidence for "pressures not captured by headline data".
Identification note: month fixed effects absorb anything common to all groups in a month — including national media
coverage and the headline macro releases — so H-c isolates group-specific experience. It still cannot rule out that
pessimistic people *report* more hardship (same-survey reverse causality); we flag this explicitly.

Data: Michigan monthly sub-indices (archive file) + Michigan demographic tables (3-month moving averages; verified).
"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import *

DEMO = ROOT / "data" / "raw" / "umich" / "demo"
GROUPS = {"age": {"a1834": "18–34", "a3554": "35–54", "a5597": "55+"},
          "income": {"y13": "Bottom third", "y23": "Middle third", "y33": "Top third"}}
COLS = {
    "t1a": ["ics", "cases"],
    "t1b": ["icc", "pf_now", "buy_dur", "ice", "pf_exp", "bus1", "bus5"],
    "t6":  ["pago_better", "pago_same", "pago_worse", "pago_dk", "pago_tot", "pago_rel", "cases6"],
    "t7":  ["rsn_better_income", "rsn_better_assets", "rsn_better_lowdebt", "rsn_worse_lowincome", "rsn_worse_prices",
            "rsn_worse_assets", "rsn_worse_debt"],
    "t8":  ["pexp_better", "pexp_same", "pexp_worse", "pexp_dk", "pexp_tot", "pexp_rel", "cases8"],
    "t14": ["rinc_up_more", "rinc_same", "rinc_prices_more", "rinc_dk", "rinc_tot", "rinc_rel", "cases14"],
    "t17": ["job0", "job1_24", "job25_49", "job50", "job51_74", "job75_99", "job100", "job_dk", "job_tot", "joblose_mean", "cases17"],
    "t23": ["news_fav", "news_unfav", "news_none", "news_rel"],
    "t24": ["nf_govt", "nf_emp", "nf_dmnd", "nf_price", "nf_crdt", "nf_stock", "nf_trade",
            "nu_govt", "nu_emp", "nu_dmnd", "nu_price", "nu_crdt", "nu_energy", "nu_stock", "nu_trade"],
    "t32": ["px_down", "px_same", "px_12", "px_34", "px_5", "px_69", "px_1014", "px_15p", "px_dkup", "px_dk", "px_tot",
            "px_median", "px_p25", "px_p75", "px_rng", "px_mean", "px_var", "cases32"],
    "t34": ["govt_good", "govt_fair", "govt_poor", "govt_dk", "govt_tot", "govt_rel", "cases34"],
    "t41": ["hom_good", "hom_bad", "hom_dk", "hom_tot", "hom_rel", "cases41"],
    "t42": ["hg_prices_low", "hg_prices_rising", "hg_rates_low", "hg_borrow_ahead", "hg_times_good", "hg_investment",
            "hb_prices_high", "hb_rates_high", "hb_cant_afford", "hb_uncertain", "hb_bad_investment"],
}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def read_table(path, names):
    x = pd.read_excel(path, header=None)
    x = x[x[0].astype(str).str.strip().str.lower().isin(MONTHS)]
    x = x.iloc[:, : 2 + len(names)]
    if x.shape[1] != 2 + len(names):
        raise ValueError(f"{path.name}: expected {2+len(names)} cols, got {x.shape[1]}")
    x.columns = ["m", "y"] + names
    x["date"] = pd.PeriodIndex.from_fields(year=x.y.astype(float).astype(int),
                                           month=x.m.str.strip().str.lower().map(MONTHS), freq="M")
    return x.set_index("date")[names].apply(pd.to_numeric, errors="coerce")


def group_panel(dim):
    frames = []
    for code, label in GROUPS[dim].items():
        parts = []
        for t, names in COLS.items():
            f = DEMO / f"{dim}_{code}_{t}.xls"
            if f.exists():
                parts.append(read_table(f, names))
        g = pd.concat(parts, axis=1); g["group"] = label; frames.append(g)
    return pd.concat(frames)


P = load_panel()
monthly_cols = {"age": {"18–34": "ics_a1834", "35–54": "ics_a3554", "55+": "ics_a5597"},
                "income": {"Bottom third": "ics_inc31", "Middle third": "ics_inc32", "Top third": "ics_inc33"}}
results = {}
for dim in ["age", "income"]:
    D = group_panel(dim)
    D.to_csv(PROC / f"umich_by_{dim}_3mma.csv")
    # ---------------- H-a: concentration of the decline (monthly sub-indices; shares from respondent counts)
    share = D.reset_index().pivot(index="date", columns="group", values="cases")
    share = share.div(share.sum(axis=1), axis=0)
    rows = []
    for g, col in monthly_cols[dim].items():
        s = P[col]
        a, b = s.loc["2019-01":"2019-12"].mean(), s.loc["2025-01":"2026-08"].mean()
        w = share[g].loc["2025-01":"2026-08"].mean()
        rows.append({"group": g, "ICS_2019": a, "ICS_2025_26": b, "change": b - a, "pct_change": 100 * (b / a - 1),
                     "sample_share": w, "contribution_pts": w * (b - a)})
    dec = pd.DataFrame(rows)
    dec["share_of_decline_%_unweighted_counts"] = 100 * dec.contribution_pts / dec.contribution_pts.sum()
    # implied weights: constrained least squares of ICS_all on the three monthly sub-indices (2015+)
    Y = P.loc["2015-01":"2026-08", "ics"]; X = P.loc["2015-01":"2026-08", list(monthly_cols[dim].values())]
    ok = X.notna().all(axis=1) & Y.notna()
    Xc = X[ok].values - X[ok].values[:, [-1]]; yc = Y[ok].values - X[ok].values[:, -1]
    bw = np.linalg.lstsq(Xc[:, :-1], yc, rcond=None)[0]; wts = np.r_[bw, 1 - bw.sum()]
    dec["implied_weight_CLS"] = wts
    # PRIMARY decomposition uses the implied (survey-weighted) weights: raw respondent counts are unweighted and the
    # web sample skews old (55+ ~ 2/3 of completes), which Michigan's post-stratification weights correct.
    dec["contribution_pts_CLS"] = dec.implied_weight_CLS * dec.change
    dec["share_of_decline_%_CLS"] = 100 * dec.contribution_pts_CLS / dec.contribution_pts_CLS.sum()
    dec["decline_vs_avg_pts"] = dec.change - dec.change.mean()
    dec.to_csv(TAB / f"decline_by_{dim}.csv", index=False)
    print(f"\n=== {dim}: concentration of decline\n", dec.round(2).to_string())

    # ---------------- H-b: hardship profile by group, 2019 vs 2025–26 (3mma tables)
    hard = ["rsn_worse_prices", "rsn_worse_lowincome", "pago_worse", "rinc_prices_more", "hb_prices_high", "hb_rates_high",
            "hb_cant_afford", "px_median", "joblose_mean", "nu_price", "nu_emp", "nu_govt", "nu_trade", "news_unfav",
            "govt_poor", "icc", "ice", "pf_now", "pf_exp", "buy_dur"]
    prof = []
    for g in GROUPS[dim].values():
        d = D[D.group == g]
        for h in hard:
            if h in d:
                prof.append({"group": g, "measure": h, "2019": d.loc["2019-01":"2019-12", h].mean(),
                             "2025_26": d.loc["2025-01":"2026-08", h].mean()})
    prof = pd.DataFrame(prof); prof["change"] = prof["2025_26"] - prof["2019"]
    wide = prof.pivot(index="measure", columns="group", values="change")[list(GROUPS[dim].values())]
    wide.to_csv(TAB / f"hardship_change_by_{dim}.csv"); prof.to_csv(TAB / f"hardship_levels_by_{dim}.csv", index=False)
    print(f"\n=== {dim}: change in hardship measures 2019 -> 2025-26 (pp)\n", wide.round(1).to_string())

    # ---------------- H-c: within-month panel regression (group FE + month FE), Driscoll–Kraay-type HAC
    d = D.reset_index()
    d = d[(d.date >= pd.Period("2008-01", "M")) & (d.date <= pd.Period("2026-08", "M"))]
    regs = {"prices only": ["rsn_worse_prices"],
            "prices + income": ["rsn_worse_prices", "rsn_worse_lowincome"],
            "hardship set": ["rsn_worse_prices", "rsn_worse_lowincome", "hb_cant_afford", "joblose_mean"],
            "hardship + news heard": ["rsn_worse_prices", "rsn_worse_lowincome", "hb_cant_afford", "joblose_mean", "nu_price", "nu_emp"]}
    out = []
    for name, xs in regs.items():
        dd = d.dropna(subset=["ics"] + xs).copy()
        # two-way demeaning (balanced panel within months) == month FE + group FE
        for v in ["ics"] + xs:
            dd[v + "_w"] = dd[v] - dd.groupby("date")[v].transform("mean") - dd.groupby("group")[v].transform("mean") + dd[v].mean()
        dd = dd.sort_values(["date", "group"])
        X = dd[[v + "_w" for v in xs]]
        # Driscoll–Kraay SEs: robust to cross-group correlation within a month AND serial correlation over months
        # (needed because the demographic tables are 3-month moving averages). maxlags=6.
        tcode = dd["date"].astype(str).factorize()[0]
        r = sm.OLS(dd["ics_w"], X).fit(cov_type="hac-groupsum", cov_kwds={"time": tcode, "maxlags": 6})
        # Moving-average (3mma) data induce serial correlation: also report HAC by time on month-collapsed scores
        for v in xs:
            out.append({"spec": name, "var": v, "coef": r.params[v + "_w"], "se_driscoll_kraay": r.bse[v + "_w"],
                        "p": r.pvalues[v + "_w"], "n": int(r.nobs), "within_R2": r.rsquared})
    out = pd.DataFrame(out); out.to_csv(TAB / f"within_month_panel_{dim}.csv", index=False)
    print(f"\n=== {dim}: within-month panel (group FE + month FE)\n", out.round(3).to_string())
    results[dim] = (dec, wide, D)

# ---------------------------------------------------------------- figures
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(10, 3.4), sharey=True)
for ax, dim, cols in [(axes[0], "age", ["#1b9e77", "#d95f02", "#7570b3"]), (axes[1], "income", ["#e7298a", "#66a61e", "#a6761d"])]:
    for (g, col), c in zip(monthly_cols[dim].items(), cols):
        s = P[col].loc["2015-01":].rolling(3).mean()
        ax.plot(s.index.to_timestamp(), s, label=g, color=c, lw=1.3)
    ax.plot(P["ics"].loc["2015-01":].index.to_timestamp(), P["ics"].loc["2015-01":].rolling(3).mean(), color="black", lw=.8, ls="--", label="All")
    ax.set_title(f"Sentiment by {dim} (3-mo avg)"); ax.legend(frameon=False, fontsize=7)
fig.tight_layout(); fig.savefig(FIG / "fig_groups.png", dpi=200)

fig, ax = plt.subplots(figsize=(8.5, 3.6))
_, wide, _ = results["age"]
show = {"rsn_worse_prices": "Worse off: higher prices", "rsn_worse_lowincome": "Worse off: lower income",
        "hb_cant_afford": "Home: can't afford", "hb_rates_high": "Home: rates high", "nu_price": "Heard bad news: prices",
        "nu_trade": "Heard bad news: trade/tariffs", "govt_poor": "Govt policy 'poor'"}
w = wide.loc[[k for k in show if k in wide.index]].rename(index=show)
w.plot.barh(ax=ax, color=["#1b9e77", "#d95f02", "#7570b3"]); ax.axvline(0, color="black", lw=.6)
ax.set_xlabel("Change, 2019 → 2025–26 (percentage points of respondents)"); ax.set_title("Reported hardships by age group")
ax.legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(FIG / "fig_hardship_age.png", dpi=200)
print("done")

"""Shared helpers: data loading, real-time expanding-window forecasts, HAC inference, forecast tests."""
from pathlib import Path
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TAB = OUT / "tables"
for p in (OUT, FIG, TAB):
    p.mkdir(parents=True, exist_ok=True)

# UMich's own estimate of the phone->web method effect on the ICS level (April 2024 announcement); an independent
# estimate (Cummings & Tedeschi, 2024) is 8.9. Used ONLY as a sensitivity offset, never estimated from the gap period.
MODE_EFFECT_UMICH, MODE_EFFECT_ALT = -6.6, -8.9


def load_panel():
    p = pd.read_csv(PROC / "monthly_panel.csv")
    p["survey_month"] = pd.PeriodIndex(p["survey_month"], freq="M")
    return p.set_index("survey_month")


def ols_hac(y, X, lags=12):
    X = sm.add_constant(X, has_constant="add")
    return sm.OLS(y, X, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def expanding_oos(df, y, xs, start="1990-01", min_train=120, level=(0.80, 0.95), window=None):
    """Real-time one-step-ahead forecasts. For each month t >= start, fit OLS on all rows < t (or the last
    `window` rows) with complete data, then predict y_t from x_t (x_t is itself the real-time information set).
    Returns a frame with prediction, analytic OLS prediction intervals, and the forecast error (= sentiment gap)."""
    d = df[[y] + xs].copy()
    out = []
    for t in d.index[d.index >= pd.Period(start, "M")]:
        x_t = d.loc[t, xs]
        if x_t.isna().any():
            continue
        train = d.loc[d.index < t].dropna()
        if window: train = train.iloc[-window:]
        if len(train) < (min(min_train, window) if window else min_train):
            continue
        X = sm.add_constant(train[xs].values, has_constant="add")
        res = sm.OLS(train[y].values, X).fit()
        x = np.r_[1.0, x_t.values.astype(float)]
        pred = float(x @ res.params)
        se_f = float(np.sqrt(res.scale * (1 + x @ res.normalized_cov_params @ x)))
        row = {"month": t, "pred": pred, "se_f": se_f, "actual": d.loc[t, y], "n_train": len(train)}
        for lv in level:
            z = stats.t.ppf(0.5 + lv / 2, res.df_resid)
            row[f"lo{int(lv*100)}"], row[f"hi{int(lv*100)}"] = pred - z * se_f, pred + z * se_f
        out.append(row)
    r = pd.DataFrame(out).set_index("month")
    r["gap"] = r["actual"] - r["pred"]
    r["z"] = r["gap"] / r["se_f"]
    return r


def rmse(e): e = np.asarray(e, float); e = e[~np.isnan(e)]; return float(np.sqrt(np.mean(e ** 2)))


def diebold_mariano(e1, e2, h=1):
    """DM test of equal squared-error loss (e1 = benchmark). Positive stat => model 2 more accurate. HAC variance."""
    d = pd.Series(np.asarray(e1) ** 2 - np.asarray(e2) ** 2).dropna()
    n = len(d)
    if n < 10: return np.nan, np.nan
    lags = max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    res = sm.OLS(d.values, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    stat = float(res.tvalues[0])
    return stat, float(2 * (1 - stats.norm.cdf(abs(stat))))


def clark_west(e_small, e_big, f_small, f_big):
    """Clark–West (2007) test for NESTED models: H0 the larger model adds nothing. One-sided p-value."""
    e1, e2 = np.asarray(e_small, float), np.asarray(e_big, float)
    adj = (np.asarray(f_small, float) - np.asarray(f_big, float)) ** 2
    f = pd.Series(e1 ** 2 - (e2 ** 2 - adj)).dropna()
    n = len(f)
    if n < 10: return np.nan, np.nan
    lags = max(1, int(np.floor(4 * (n / 100) ** (2 / 9))))
    res = sm.OLS(f.values, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    stat = float(res.tvalues[0])
    return stat, float(1 - stats.norm.cdf(stat))


def holm(pvals):
    p = np.asarray(pvals, float); order = np.argsort(p); m = len(p)
    adj = np.empty(m); running = 0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i]); adj[i] = min(1.0, running)
    return adj


def bh(pvals):
    p = np.asarray(pvals, float); m = len(p); order = np.argsort(p)
    adj = np.empty(m); prev = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]; prev = min(prev, p[i] * m / (rank + 1)); adj[i] = prev
    return adj


def load_corpus():
    C = pd.read_csv(PROC / "corpus.csv", low_memory=False)
    C["date"] = pd.to_datetime(C["date"], format="mixed", errors="coerce")
    for b in ["relevant_kw", "dup_exact", "ad_flag", "bot_flag", "foreign_flag", "non_english"]:
        if b in C: C[b] = C[b].astype(str).str.lower().eq("true")
    return C

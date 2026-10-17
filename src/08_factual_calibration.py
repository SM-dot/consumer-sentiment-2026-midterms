"""
08_factual_calibration.py — Codebook D4: do numerical claims match official data AVAILABLE AT PUBLICATION?

For each item (headline/post) that states a number about an official indicator we:
  1. extract (indicator, value, horizon) with transparent regular expressions (rule-based extraction is auditable;
     the extracted claim and the text are kept side by side in outputs/tables/calibration_claims.csv);
  2. build the set of official values that were PUBLIC on the item's date (the latest and the previous release —
     outlets routinely cite either), using approximate release calendars below;
  3. classify: calibrated (|error| <= tolerance) | definition_error (matches a *different* official measure, e.g.
     core vs headline CPI, monthly vs annual) | uncalibrated; and record the signed error in the "bad-news"
     direction (positive = claim makes the economy look worse than the official figure).
Limitations: payroll and PCE comparisons use current-vintage data (revisions can create spurious "errors" — we use
wide tolerances); mortgage-rate claims may cite non-Freddie Mac sources (we flag them separately).
"""
import json, re, glob
import numpy as np, pandas as pd
from lib import load_corpus, ROOT, PROC, TAB

RAW = ROOT / "data" / "raw"


def bls_series():
    rows = []
    for f in glob.glob(str(RAW / "bls" / "*.json")):
        for s in json.load(open(f))["Results"]["series"]:
            for o in s["data"]:
                if o["period"].startswith("M") and o["period"] != "M13":
                    try: v = float(o["value"])
                    except ValueError: v = np.nan
                    rows.append((s["seriesID"], pd.Period(f"{o['year']}-{o['period'][1:]}", "M"), v))
    d = pd.DataFrame(rows, columns=["id", "m", "v"]).drop_duplicates(["id", "m"])
    return d.pivot(index="m", columns="id", values="v").sort_index()


B = bls_series()
cpi_nsa, core_nsa, cpi_sa = B["CUUR0000SA0"], B["CUUR0000SA0L1E"], B["CUSR0000SA0"]
OFFICIAL = {   # indicator -> {measure_name: monthly series}, all in the units headlines use
    "cpi": {"headline_yoy": 100 * (cpi_nsa / cpi_nsa.shift(12) - 1), "core_yoy": 100 * (core_nsa / core_nsa.shift(12) - 1),
            "headline_mom": 100 * (cpi_sa / cpi_sa.shift(1) - 1)},
    "unemployment": {"u3": B["LNS14000000"], "u6": B["LNS13327709"]},
    "payrolls": {"change_k": B["CES0000000001"].diff()},
}
panel = pd.read_csv(PROC / "monthly_panel.csv"); panel["m"] = pd.PeriodIndex(panel.survey_month, freq="M")
raw = pd.read_csv(PROC / "raw_period_dated_series.csv", index_col=0); raw.index = pd.PeriodIndex(raw.index, freq="M")
OFFICIAL["pce"] = {"headline_yoy": raw["pce_yoy"], "core_yoy": raw["core_pce_yoy"]}
RT_GDP = panel.set_index("m")[["rt_gdp_qoq_saar", "rt_gdp_yoy"]]
pm = pd.read_csv(RAW / "other" / "pmms.csv"); pm["date"] = pd.to_datetime(pm["date"]); pm = pm.set_index("date")["pmms30"].dropna()
RELEASE_DAY = {"cpi": 13, "unemployment": 6, "payrolls": 6, "pce": 28}      # typical; +-4 days tolerance in released()      # approximate day-of-month of release (month m+1)
TOL = {"cpi": 0.1, "unemployment": 0.1, "pce": 0.1, "gdp": 0.15, "mortgage": 0.15, "payrolls": 60}

NUM = r"(?<![\d.\-–])(-?\d{1,2}(?:\.\d{1,2})?)\s?(?:%|percent|per cent|pct)"
RANGE = re.compile(r"\d\s?[-–]\s?\d{1,2}(?:\.\d)?\s?(?:%|percent)")
EXCLUDE = re.compile(r"expect|forecast|project|poll|survey|voters|americans say|of (?:people|respondents|households)|could|would|might|will|target", re.I)
US_CONTEXT = re.compile(r"\b(u\.?s\.?|us|america\w*|federal|bls|cpi|fed\b|nationwide|national)\b", re.I)
PATTERNS = [
    ("cpi", re.compile(r"(inflation|consumer prices?|cpi|consumer price index)\b[^.;:!?]{0,70}?" + NUM, re.I)),
    ("pce", re.compile(r"(\bpce\b|personal consumption expenditures?)\b[^.;:!?]{0,70}?" + NUM, re.I)),
    ("unemployment", re.compile(r"(unemployment|jobless) rate\b[^.;:!?]{0,50}?" + NUM, re.I)),
    ("gdp", re.compile(r"(\bgdp\b|gross domestic product|economy (grew|grows|shrank|contracted|expanded))\b[^.;:!?]{0,60}?" + NUM, re.I)),
    ("mortgage", re.compile(r"mortgage rates?\b[^.;:!?]{0,50}?" + NUM, re.I)),
    ("payrolls", re.compile(r"\b(add(?:ed|s)?|creat(?:ed|es)|gain(?:ed|s)?|lost|shed|cut)\s+(?:a\s+)?(?:net\s+)?([\d,]{2,9}|\d+(?:\.\d+)?\s?(?:k|thousand|million))\s+(?:new\s+)?jobs", re.I)),
]


def released(ind, d):
    """Reference months that could be 'the latest' on date d: release days vary by a few days month to month, so we
    accept m-1 (if d is past the earliest plausible release day) and m-2; outlets also cite the prior release."""
    day = RELEASE_DAY[ind]; m = pd.Period(d, "M")
    return ([m - 1] if d.day >= day - 4 else []) + [m - 2]


def parse_payroll(s):
    s = s.lower().replace(",", "").strip()
    if "million" in s: return float(re.findall(r"[\d.]+", s)[0]) * 1000
    if "k" in s or "thousand" in s: return float(re.findall(r"[\d.]+", s)[0])
    return float(s) / 1000


def check(ind, val, text, d, span=""):
    t = text.lower()
    if ind in ("cpi", "pce"):
        mom = bool(re.search(r"month|monthly|m/m|from (january|february|march|april|may|june|july|august|september|october|november|december)\b(?! \d{4})", t)) and abs(val) < 1.5
        primary = "headline_mom" if (mom and ind == "cpi") else "headline_yoy"
        if mom and ind == "pce": return None                     # PCE m/m not tracked
        if re.search(r"core\W+(\w+\W+){0,2}(inflation|cpi|consumer prices?|pce)", span.lower()): primary = "core_yoy" if not mom else None
        if primary is None: return None
        cands = {k: [OFFICIAL[ind][k].get(m, np.nan) for m in released(ind, d)] for k in OFFICIAL[ind]}
    elif ind == "unemployment":
        primary = "u3"; cands = {k: [OFFICIAL[ind][k].get(m, np.nan) for m in released(ind, d)] for k in OFFICIAL[ind]}
    elif ind == "payrolls":
        primary = "change_k"; cands = {"change_k": [OFFICIAL[ind]["change_k"].get(m, np.nan) for m in released(ind, d)]}
        if re.search(r"\b(lost|shed|cut)\b", t): val = -abs(val)
    elif ind == "gdp":
        m = pd.Period(d, "M")
        vs = [RT_GDP.loc[v] for v in (m, m + 1) if v in RT_GDP.index]   # vintage m (mid-month) and m+1 (covers late-month releases)
        if not vs: return None
        primary = "qoq_saar"; cands = {"qoq_saar": [v.rt_gdp_qoq_saar for v in vs], "yoy": [v.rt_gdp_yoy for v in vs]}
        if re.search(r"shr[ai]nk|contract", t): val = -abs(val)
    elif ind == "mortgage":
        w = pm.loc[d - pd.Timedelta(days=21): d]
        if w.empty: return None
        primary = "pmms30"; cands = {"pmms30": list(w.values)}
    tol = TOL["gdp" if ind == "gdp" else ind]
    best = {k: min((abs(val - c) for c in v if pd.notna(c)), default=np.nan) for k, v in cands.items()}
    p_err = best.get(primary, np.nan)
    if np.isnan(p_err): return None
    status = "calibrated" if p_err <= tol + 1e-9 else (
        "definition_error" if any(b <= tol + 1e-9 for k, b in best.items() if k != primary and not np.isnan(b)) else "uncalibrated")
    ref = [c for c in cands[primary] if pd.notna(c)]
    signed = val - min(ref, key=lambda c: abs(val - c))
    bad_dir = {"cpi": 1, "pce": 1, "unemployment": 1, "mortgage": 1, "gdp": -1, "payrolls": -1}[ind]
    return {"measure": primary, "official_closest": val - signed, "abs_error": p_err, "status": status,
            "error_in_bad_news_direction": bad_dir * signed}


def main():
    C = load_corpus()
    C = C[C.relevant_kw & ~C.dup_exact & ~C.ad_flag]
    out = []
    for r in C.itertuples():
        for ind, pat in PATTERNS:
            m = pat.search(r.text)
            if not m: continue
            span = m.group(0)
            # skip ranges, forecasts/expectations/polls, and (for social posts) items without explicit US context
            if RANGE.search(span) or EXCLUDE.search(span): break
            if (r.platform == "social" or r.source_tier in ("local_regional", "other_institutional")) and not US_CONTEXT.search(r.text): break
            try:
                val = parse_payroll(m.group(2)) if ind == "payrolls" else float(m.groups()[-1])
            except (ValueError, IndexError):
                continue
            if ind == "unemployment" and not (2 <= val <= 16): continue
            if ind == "mortgage" and not (2 <= val <= 12): continue
            if ind in ("cpi", "pce") and not (-3 <= val <= 12): continue
            if ind == "gdp" and not (-35 <= val <= 35): continue
            pre = r.text[max(0, m.start() - 25): m.end()]
            res = check(ind, val, r.text, r.date, pre)
            if res:
                out.append({"item_id": r.item_id, "date": r.date, "platform": r.platform, "source": r.source,
                            "source_tier": r.source_tier, "outlet_lean": r.outlet_lean, "indicator": ind,
                            "claim_value": val, "matched_span": m.group(0)[:120], "text": r.text[:300], **res})
            break   # one claim per item (the first indicator matched)
    D = pd.DataFrame(out); D.to_csv(TAB / "calibration_claims.csv", index=False)
    if D.empty:
        print("no claims"); return
    D["month"] = D.date.dt.to_period("M").astype(str)
    summ = D.groupby(["indicator"]).agg(n=("status", "size"), calibrated=("status", lambda s: (s == "calibrated").mean()),
                                        definition_error=("status", lambda s: (s == "definition_error").mean()),
                                        uncalibrated=("status", lambda s: (s == "uncalibrated").mean()),
                                        mean_bad_news_error=("error_in_bad_news_direction", "median"))   # median: robust to mis-parsed outliers
    summ.loc["ALL"] = [len(D), (D.status == "calibrated").mean(), (D.status == "definition_error").mean(),
                       (D.status == "uncalibrated").mean(), np.nan]
    summ.to_csv(TAB / "calibration_summary.csv")
    by_src = D.groupby(["platform", "source_tier"]).agg(n=("status", "size"), calibrated=("status", lambda s: (s == "calibrated").mean()),
                                                        mean_bad_news_error=("error_in_bad_news_direction", "mean"))
    by_src.to_csv(TAB / "calibration_by_source.csv")
    D.groupby("month").agg(n_claims=("status", "size"), calibrated_share=("status", lambda s: (s == "calibrated").mean()),
                           bad_news_error=("error_in_bad_news_direction", "mean")).to_csv(TAB / "calibration_monthly.csv")
    print(summ.round(3)); print(by_src.round(3))


if __name__ == "__main__":
    main()

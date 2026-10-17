"""
03_build_dataset.py — Economic & survey baseline (Section 1 of the brief).

Produces data/processed/monthly_panel.csv : one row per SURVEY MONTH (1978-01 .. 2026-10) containing
  * Michigan ICS / ICC / ICE (+ age, income, region sub-indices, news-heard, reasons, expectations)
  * the three required macro indicators AS AVAILABLE AT THE SURVEY DATE (real-time information set)
  * household-pressure controls (also lagged to their publication dates)
and data/processed/provenance_checks.csv : cross-checks of the professor-supplied file vs. primary sources.

TIMING CONVENTION (documented in docs/DATA_PROVENANCE.md):
  Michigan interviews run from ~the last week of month t-1 to ~the 20th of month t; preliminary results
  are released ~2nd Friday of t. We define the information set as "what was public by ~the 15th of month t".
    U-3 (BLS)            month t-1   (Employment Situation, first Friday of t)
    PCE price YoY (BEA)  month t-2   (Personal Income & Outlays, last week of t-1)
    Real GDP (BEA)       latest quarter in the Philadelphia Fed real-time vintage dated month t
                         (first-release / then-current estimate — NOT today's revised value)
    Controls             lagged to their own release calendars (see LAGS below)
  2025 federal shutdown: explicit overrides (SHUTDOWN_OVERRIDES) — no October-2025 household survey was run.
  Quarterly GDP is NEVER interpolated to months: each month carries the latest *published* quarterly growth rate.
"""
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
IDX = pd.period_range("1978-01", "2026-10", freq="M")

# ---------------------------------------------------------------- professor file
def professor():
    d = pd.read_excel(RAW / "professor_Perceptual_Bias_Data.xlsx", header=None).iloc[1:]
    def col(dc, vc, name):
        s = d[[dc, vc]].dropna()
        s.columns = ["date", name]
        s["date"] = pd.to_datetime(s["date"]).dt.to_period("M")
        return s.set_index("date")[name].astype(float)
    u = col(0, 1, "prof_u3"); ics = col(3, 4, "prof_ics"); pce = col(7, 8, "prof_pce_yoy")
    g = d[[10, 11]].dropna(); g.columns = ["date", "prof_gdp_qoq_saar"]
    g["q"] = pd.to_datetime(g["date"]).dt.to_period("Q")
    return u, ics, pce, g.set_index("q")["prof_gdp_qoq_saar"].astype(float)

# ---------------------------------------------------------------- Michigan
def umich():
    t = pd.read_csv(RAW / "umich" / "all_tables.raw", skiprows=1)
    t["date"] = pd.PeriodIndex.from_fields(year=t.yyyy, month=t.Month, freq="M")
    t = t.set_index("date").drop(columns=["Month", "yyyy"])
    return t.apply(pd.to_numeric, errors="coerce")

def umich_tbmics():
    """Headline series incl. the most recent (prelim) months that the archive table has not yet posted."""
    import io, requests
    txt = (RAW / "umich" / "tbmics.csv")
    if not txt.exists():
        txt.write_text(requests.get("https://www.sca.isr.umich.edu/files/tbmics.csv", timeout=60).text)
    s = pd.read_csv(txt)
    s["date"] = pd.PeriodIndex.from_fields(year=s.YYYY, month=pd.to_datetime(s.Month, format="%B").dt.month, freq="M")
    return s.set_index("date")["ICS_ALL"].astype(float)

# ---------------------------------------------------------------- BEA flat files
def bea(code, freq="M"):
    f = RAW / "bea" / ("NipaDataM.txt" if freq == "M" else "NipaDataQ.txt")
    if not hasattr(bea, "_cache"): bea._cache = {}
    if f not in bea._cache:
        bea._cache[f] = pd.read_csv(f, dtype=str)
    d = bea._cache[f]
    d = d[d["%SeriesCode"] == code].copy()
    d["Value"] = d["Value"].str.replace(",", "").astype(float)
    if freq == "M":
        d["date"] = pd.PeriodIndex([p.replace("M", "-") for p in d.Period], freq="M")
    else:
        d["date"] = pd.PeriodIndex([p[:4] + "Q" + p[-1] for p in d.Period], freq="Q")
    return d.set_index("date")["Value"]

# ---------------------------------------------------------------- BLS
def bls():
    import json
    rows = []
    for f in sorted((RAW / "bls").glob("bls_*.json")):
        for s in json.load(open(f))["Results"]["series"]:
            for o in s["data"]:
                if o["period"].startswith("M") and o["period"] != "M13":
                    try: v = float(o["value"])
                    except ValueError: v = np.nan          # "-" = not collected (Oct-2025 shutdown)
                    rows.append((s["seriesID"], pd.Period(f"{o['year']}-{o['period'][1:]}", "M"), v))
    d = pd.DataFrame(rows, columns=["id", "date", "v"]).drop_duplicates(["id", "date"])
    return d.pivot(index="date", columns="id", values="v")

# ---------------------------------------------------------------- Philadelphia Fed real-time GDP
def realtime_gdp():
    """For each vintage month v: latest quarter available, its q/q SAAR growth and y/y growth, in that vintage."""
    x = pd.read_excel(RAW / "philly" / "routputMvQd.xlsx")
    x["q"] = pd.PeriodIndex([s.replace(":", "") for s in x.DATE.astype(str)], freq="Q")
    x = x.set_index("q").drop(columns="DATE").apply(pd.to_numeric, errors="coerce")
    out = {}
    for c in x.columns:
        yy, mm = int(c[7:9]), int(c.split("M")[-1])
        yr = 1900 + yy if yy >= 65 else 2000 + yy
        v = pd.Period(f"{yr}-{mm:02d}", "M")
        s = x[c].dropna()
        if len(s) < 6: continue
        q = s.index[-1]
        out[v] = {"rt_gdp_quarter": str(q),
                  "rt_gdp_qoq_saar": 100 * ((s.iloc[-1] / s.iloc[-2]) ** 4 - 1),
                  "rt_gdp_yoy": 100 * (s.iloc[-1] / s.iloc[-5] - 1)}
    rt = pd.DataFrame(out).T
    rt.index = pd.PeriodIndex(rt.index, freq="M")
    rt[["rt_gdp_qoq_saar", "rt_gdp_yoy"]] = rt[["rt_gdp_qoq_saar", "rt_gdp_yoy"]].astype(float)
    # first-release growth for each quarter (used to document revisions)
    first = {}
    for c in x.columns:
        s = x[c].dropna()
        if len(s) < 2: continue
        q = s.index[-1]
        if q not in first:
            first[q] = 100 * ((s.iloc[-1] / s.iloc[-2]) ** 4 - 1)
    return rt, pd.Series(first, name="first_release_qoq_saar")

# ---------------------------------------------------------------- other controls
def pmms():
    p = pd.read_csv(RAW / "other" / "pmms.csv")
    p["date"] = pd.to_datetime(p["date"]).dt.to_period("M")
    return p.groupby("date")["pmms30"].mean()

def gas():
    g = pd.read_excel(RAW / "other" / "gas.xls", sheet_name="Data 1", skiprows=2)
    g.columns = ["date", "gas"]
    g["date"] = pd.to_datetime(g["date"]).dt.to_period("M")
    return g.set_index("date")["gas"].astype(float)

def epu():
    e = pd.read_excel(RAW / "other" / "epu.xlsx")
    e = e[pd.to_numeric(e.Year, errors="coerce").notna() & e.Month.notna()]
    e["date"] = pd.PeriodIndex.from_fields(year=e.Year.astype(int), month=e.Month.astype(int), freq="M")
    return e.set_index("date")["News_Based_Policy_Uncert_Index"].astype(float).sort_index()

def fhfa():
    h = pd.read_csv(RAW / "other" / "hpi.csv")
    h = h[(h.place_id == "USA") & (h.hpi_flavor == "purchase-only") & (h.frequency == "monthly")]
    h["date"] = pd.PeriodIndex.from_fields(year=h.yr, month=h.period, freq="M")
    return h.set_index("date")["index_sa"].astype(float)

# ---------------------------------------------------------------- real-time availability
LAGS = {"u3": 1, "pce_yoy": 2, "core_pce_yoy": 2, "u6": 1, "cpi_yoy": 1, "food_yoy": 1, "shelter_yoy": 1, "real_ahe_yoy": 1,
        "rdpi_pc_yoy": 2, "saving_rate": 2, "interest_burden": 2, "price_gap": 2, "cum3y_infl": 2,
        "mort30": 0, "afford_idx": 2, "gas_real_yoy": 0, "epu": 1}
# Survey month -> data month actually public by mid-month (2025 shutdown; BLS: no Oct-2025 household survey,
# Sep-2025 jobs report released 2025-11-20; BEA: Sep-2025 PIO released 2025-12-05, Oct+Nov combined 2026-01-22).
SHUTDOWN_OVERRIDES = {
    "u3":      {"2025-10": "2025-08", "2025-11": "2025-08", "2025-12": "2025-09"},
    "core_pce_yoy": {"2025-11": "2025-08", "2025-12": "2025-09", "2026-01": "2025-09", "2026-02": "2025-11"},
    "pce_yoy": {"2025-11": "2025-08", "2025-12": "2025-09", "2026-01": "2025-09", "2026-02": "2025-11"},
}

def available(series, name):
    lag = LAGS[name]
    out = series.reindex(IDX).shift(lag)
    for sm, dm in SHUTDOWN_OVERRIDES.get(name, {}).items():
        if pd.Period(sm, "M") in out.index:
            out[pd.Period(sm, "M")] = series.get(pd.Period(dm, "M"), np.nan)
    return out


def main():
    pu3, pics, ppce, pgdp = professor()
    um = umich()
    ics_head = umich_tbmics()
    B = bls()
    rt, first = realtime_gdp()

    # ---- raw (period-dated) series
    pce_idx = bea("DPCERG")
    pce_yoy = 100 * (pce_idx / pce_idx.shift(12) - 1)
    u3 = pu3.combine_first(B["LNS14000000"])                         # professor values; BLS fills/validates
    cpi = B["CUSR0000SA0"]
    raw = pd.DataFrame(index=IDX)
    raw["u3"] = u3; raw["pce_yoy"] = pce_yoy
    core = bea("DPCCRG"); raw["core_pce_yoy"] = 100 * (core / core.shift(12) - 1)   # = professor's "PCE YoY" column (verified identical)
    raw["u6"] = B["LNS13327709"]
    raw["cpi_yoy"] = 100 * (cpi / cpi.shift(12) - 1)
    raw["food_yoy"] = 100 * (B["CUSR0000SAF11"] / B["CUSR0000SAF11"].shift(12) - 1)
    raw["shelter_yoy"] = 100 * (B["CUSR0000SAH1"] / B["CUSR0000SAH1"].shift(12) - 1)
    rahe = B["CES0500000003"] / cpi
    raw["real_ahe_yoy"] = 100 * (rahe / rahe.shift(12) - 1)
    rdpi = bea("A229RX"); raw["rdpi_pc_yoy"] = 100 * (rdpi / rdpi.shift(12) - 1)
    raw["saving_rate"] = bea("A072RC")
    raw["interest_burden"] = 100 * bea("B069RC") / bea("A067RC")   # non-mortgage interest paid / DPI
    # Cumulative price pressure: (i) 36-month PCE inflation; (ii) price LEVEL gap vs a 2%-per-year path
    # anchored 36 months earlier. Both stay elevated after the inflation RATE falls -> "level vs rate" channel.
    raw["cum3y_infl"] = 100 * (pce_idx / pce_idx.shift(36) - 1)
    raw["price_gap"] = 100 * (np.log(pce_idx) - np.log(pce_idx.shift(36)) - 3 * np.log(1.02))
    raw["mort30"] = pmms()
    hp = fhfa(); dpi_pc = bea("A229RC")
    r = raw["mort30"] / 1200
    pay = hp.reindex(IDX) * r / (1 - (1 + r) ** -360)               # payment on an index-priced home, 80% LTV omitted (scale-free)
    raw["afford_idx"] = 100 * (pay / dpi_pc.reindex(IDX)) / (pay / dpi_pc.reindex(IDX)).loc["2019-01":"2019-12"].mean()
    g = gas(); gr = g / cpi.reindex(g.index)
    raw["gas_real_yoy"] = 100 * (gr / gr.shift(12) - 1)
    raw["epu"] = epu()

    panel = pd.DataFrame(index=IDX)
    panel.index.name = "survey_month"
    # ---- Michigan (survey month is contemporaneous by definition)
    panel["ics"] = um["ics_all"].reindex(IDX).combine_first(ics_head.reindex(IDX)).combine_first(pics.reindex(IDX))
    panel["ics_is_preliminary"] = (panel.index == pd.Period("2026-10", "M")).astype(int)   # Oct-2026 = preliminary (released ~Oct 9)
    panel["ics_prof"] = pics.reindex(IDX)
    panel["icc"] = um["icc_all"]; panel["ice"] = um["ice_all"]
    for c in ["ics_a1834", "ics_a3554", "ics_a5597", "ics_inc31", "ics_inc32", "ics_inc33",
              "news_f_all", "news_u_all", "news_r_all", "newsrn_u_pri_all", "newsrn_u_emp_all", "newsrn_u_govt_all",
              "newsrn_u_trd_all", "newsrn_f_pri_all", "newsrn_f_emp_all", "newsrn_f_govt_all",
              "pagorn_hp_all", "pagorn_ly_all", "pagorn_hy_all", "pago_r_all", "pexp_r_all", "rinc_r_all",
              "px1_med_all", "px5_med_all", "govt_r_all", "homrn_hp_all", "homrn_hr_all", "durrn_hp_all",
              "pjob_mean_all", "umex_r_all", "bus12_r_all", "pstk_mean_all"]:
        if c in um: panel[c] = um[c]
    # Survey-mode share (web) during the documented 2024 transition
    panel["web_share"] = 0.0
    for m, w in {"2024-04": .25, "2024-05": .5, "2024-06": .75}.items():
        panel.loc[pd.Period(m, "M"), "web_share"] = w
    panel.loc[panel.index >= pd.Period("2024-07", "M"), "web_share"] = 1.0
    # Political-calendar markers (used as controls / moderators, NOT as evidence of election effects)
    panel["post_2025_transition"] = (panel.index >= pd.Period("2025-01", "M")).astype(int)
    panel["midterm_window"] = ((panel.index >= pd.Period("2026-05", "M"))).astype(int)

    # ---- real-time macro information set
    panel["rt_u3"] = available(raw["u3"], "u3")
    panel["rt_pce_yoy"] = available(raw["pce_yoy"], "pce_yoy")
    panel = panel.join(rt.reindex(IDX))
    for c in [k for k in LAGS if k not in ("u3", "pce_yoy")]:
        panel["rt_" + c] = available(raw[c], c)
    # ---- revised ("ex-post") values kept separately, ONLY for the revision robustness check
    panel["expost_u3"] = raw["u3"]; panel["expost_pce_yoy"] = raw["pce_yoy"]
    q = panel.index.asfreq("Q")
    gq = bea("A191RL", "Q")
    panel["expost_gdp_qoq_saar_same_q"] = gq.reindex(q).values   # contemporaneous quarter (look-ahead) — robustness only

    panel.to_csv(PROC / "monthly_panel.csv")
    raw.to_csv(PROC / "raw_period_dated_series.csv")

    # ---- provenance checks
    chk = []
    a = pd.concat([pics, panel["ics"]], axis=1, keys=["prof", "umich"]).dropna()
    chk.append(("ICS: professor vs UMich official", len(a), (a.prof - a.umich).abs().max()))
    b = pd.concat([pu3, B["LNS14000000"]], axis=1, keys=["prof", "bls"]).dropna()
    chk.append(("U-3: professor vs BLS API LNS14000000", len(b), (b.prof - b.bls).abs().max()))
    c = pd.concat([ppce, pce_yoy], axis=1, keys=["prof", "bea"]).dropna()
    chk.append(("PCE YoY: professor vs BEA DPCERG HEADLINE (computed)", len(c), (c.prof - c.bea).abs().max()))
    c2 = pd.concat([ppce, raw["core_pce_yoy"]], axis=1, keys=["prof", "bea"]).dropna()
    chk.append(("PCE YoY: professor vs BEA DPCCRG CORE (computed) -> professor column is CORE", len(c2), (c2.prof - c2.bea).abs().max()))
    d = pd.concat([pgdp, gq], axis=1, keys=["prof", "bea"]).dropna()
    chk.append(("GDP q/q SAAR: professor vs BEA A191RL (current vintage)", len(d), (d.prof - d.bea).abs().max()))
    e = pd.concat([pgdp, first], axis=1, keys=["prof", "first"]).dropna()
    chk.append(("GDP q/q SAAR: professor vs FIRST release (Philly Fed)", len(e), (e.prof - e["first"]).abs().max()))
    pd.DataFrame(chk, columns=["check", "n_overlap", "max_abs_diff"]).to_csv(PROC / "provenance_checks.csv", index=False)
    rev = pd.concat([first, gq], axis=1, keys=["first_release", "current_vintage"]).dropna()
    rev["revision"] = rev.current_vintage - rev.first_release
    rev.to_csv(PROC / "gdp_revisions.csv")
    extra = sorted(set(pgdp.index) - set(gq.index))
    print(pd.read_csv(PROC / "provenance_checks.csv").to_string())
    print("Professor GDP quarters NOT yet published by BEA as of cut-off:", extra)
    print("Missing U-3 months (BLS):", list(raw["u3"].loc["2024":].index[raw["u3"].loc["2024":].isna()]))
    print(panel.loc["2026-04":, ["ics", "icc", "ice", "rt_u3", "rt_pce_yoy", "rt_gdp_quarter", "rt_gdp_qoq_saar"]])


if __name__ == "__main__":
    main()

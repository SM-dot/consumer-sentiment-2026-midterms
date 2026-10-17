"""
01_fetch_gdelt.py — Build the NEWS side of the media corpus from the GDELT DOC 2.0 API.

What it collects (all cached to data/raw/gdelt/, so re-runs only fetch what is missing):
  1. Topic timelines (daily article volume + average tone), US sources, English, 2017-01 → today.
  2. Outlet timelines (tone of economy coverage by named national outlet) for cross-source comparison.
  3. Article lists (headline, URL, domain, date) sampled per month × topic — the unit we code with AI.

GDELT's "tone" is a dictionary score computed by GDELT on full article text; we treat it as the
conventional DICTIONARY baseline. Our own LLM coding is applied to headlines (see 05_*).

Usage:  python src/01_fetch_gdelt.py [timelines|outlets|articles|all]
Rate limit: GDELT asks for <= 1 request / 5 s. We sleep 7 s and back off on refusals.
"""
import sys, time, json, hashlib, urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "gdelt"
OUT.mkdir(parents=True, exist_ok=True)
API = "https://api.gdeltproject.org/api/v2/doc/doc"
UA = {"User-Agent": "Mozilla/5.0 (academic research; consumer-sentiment course project)"}
END = "20261016000000"          # data cut-off for this project (documented in README)

# Search terms are fixed BEFORE looking at results (pre-registration of the corpus definition).
TOPICS = {   # single-phrase queries: GDELT throttles multi-term OR queries as "larger queries" (see fetch.log)
    "economy":        'economy',            # NOTE: cached file was retrieved with '(economy OR economic)' before the simplification
    "prices":         'inflation',
    "cost_of_living": '"cost of living"',
    "infl_falling":   '"inflation cools"',
    "layoffs":        'layoffs',
    "hiring":         'hiring',
    "recession":      'recession',
    "tariffs":        'tariffs',
    "gas":            '"gas prices"',
    "housing":        '"mortgage rates"',
}
OUTLETS = ["foxnews.com", "foxbusiness.com", "breitbart.com", "nypost.com", "cnn.com", "msnbc.com",
           "nytimes.com", "washingtonpost.com", "wsj.com", "apnews.com", "reuters.com",
           "usatoday.com", "cnbc.com", "npr.org", "nbcnews.com", "cbsnews.com", "abcnews.go.com"]
# One combined query per month (rate-limit budget); items are tagged by topic AFTER retrieval with the codebook keywords.
TOPICS["econ_all"] = '(economy OR inflation OR prices OR layoffs OR recession OR "jobs report" OR tariffs OR "cost of living")'
ARTICLE_TOPICS = ["econ_all"]
FILTER = " sourcecountry:US sourcelang:english"


def get(params, cache_name, fmt):
    path = OUT / cache_name
    if path.exists() and path.stat().st_size > 50:
        return path.read_text()
    for attempt in range(8):
        try:
            r = requests.get(API, params=params, headers=UA, timeout=90)
            txt = r.text
            if r.status_code == 200 and not txt.startswith("Please limit") and (fmt != "json" or txt.strip().startswith("{")):
                path.write_text(txt)
                time.sleep(30)
                return txt
            if fmt == "json" and r.status_code == 200 and txt.strip() == "":
                path.write_text('{"articles": []}')
                time.sleep(30)
                return path.read_text()
        except requests.RequestException as e:
            print("  error", e)
        wait = 120 * (attempt + 1)
        print(f"  backoff {wait}s ({cache_name})", flush=True)
        time.sleep(wait)
    print("  FAILED", cache_name)
    return None


def years():
    # One request returns the full daily series 2017-01-01 .. END (verified), so a single span suffices.
    yield "all", "20170101000000", END


def timelines():
    for key, q in TOPICS.items():
        for mode in ["timelinevolraw", "timelinetone"]:
            for y, s, e in years():
                get({"query": q + FILTER, "mode": mode, "format": "csv",
                     "startdatetime": s, "enddatetime": e},
                    f"tl_{key}_{mode}_{y}.csv", "csv")
        print("done topic", key, flush=True)


def outlets():
    for dom in OUTLETS:
        for mode in ["timelinetone"]:
            for y, s, e in years():
                get({"query": "economy" + f" domain:{dom}", "mode": mode, "format": "csv",
                     "startdatetime": s, "enddatetime": e},
                    f"out_{dom.replace('.', '_')}_{mode}_{y}.csv", "csv")
        print("done outlet", dom, flush=True)


def articles():
    import pandas as pd
    months = pd.period_range("2017-01", "2026-10", freq="M")
    for key in ARTICLE_TOPICS:
        for m in months:
            s = m.start_time.strftime("%Y%m%d%H%M%S")
            e = min((m + 1).start_time.strftime("%Y%m%d%H%M%S"), END)
            get({"query": TOPICS[key] + FILTER, "mode": "artlist", "format": "json",
                 "maxrecords": 250, "sort": "hybridrel", "startdatetime": s, "enddatetime": e},
                f"art_{key}_{m}.json", "json")
        print("done articles", key, flush=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    # Article lists moved to Google News (01b) after GDELT throttling; timelines/outlet tone stay here.
    if what in ("timelines", "all"): timelines()
    if what in ("outlets", "all"): outlets()
    if what == "articles": articles()

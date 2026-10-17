"""
01b_fetch_gnews.py — Headline corpus from Google News RSS search (public RSS endpoint; headlines + outlet + date only).

Why: GDELT's article-list endpoint throttled this IP to ~1 request / 5–10 min (see data/raw/gdelt/fetch.log), so
headline sampling moved here; GDELT is still used for full-population volume/tone timelines and outlet tone.

Design (fixed before retrieval):
  * TOPIC queries  x month (2017-01 .. 2026-10): up to 100 headlines each, US edition (gl=US, hl=en-US).
  * OUTLET queries x month: '(economy OR inflation OR jobs OR prices) site:<domain>' for 14 national outlets spanning
    the AllSides lean spectrum -> same-period, same-query comparison ACROSS sources.
Selection caveat: Google ranks results by its own relevance algorithm (not random sampling); results include
non-news publishers (think tanks, Fed banks) which 06_build_corpus tags as 'other_institutional'.
"""
import time, re, html, json
from pathlib import Path
import requests, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "gnews"; OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) academic-research"}
TOPICS = {"inflation": "inflation", "cost_of_living": '"cost of living" OR "grocery prices"', "layoffs": "layoffs OR \"job cuts\"",
          "jobs_report": '"jobs report" OR hiring OR unemployment', "recession": "recession", "economy": "economy",
          "tariffs": "tariffs", "gas_prices": '"gas prices"', "housing": '"mortgage rates" OR "home prices" OR rent'}
OUTLETS = ["foxnews.com", "foxbusiness.com", "nypost.com", "breitbart.com", "cnn.com", "msnbc.com", "nytimes.com",
           "washingtonpost.com", "nbcnews.com", "apnews.com", "reuters.com", "wsj.com", "usatoday.com", "cnbc.com"]
OUTLET_Q = "(economy OR inflation OR jobs OR prices)"


def fetch(q, a, b, name):
    path = OUT / f"{name}.json"
    if path.exists(): return
    url = "https://news.google.com/rss/search"
    params = {"q": f"{q} after:{a} before:{b}", "hl": "en-US", "gl": "US", "ceid": "US:en"}
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                items = []
                for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
                    g = lambda tag: (re.search(fr"<{tag}[^>]*>(.*?)</{tag}>", it, re.S) or [None, ""])[1]
                    src = re.search(r'<source url="(.*?)">(.*?)</source>', it)
                    items.append({"title": html.unescape(g("title")), "link": g("link"), "pubDate": g("pubDate"),
                                  "source_url": src.group(1) if src else "", "source_name": html.unescape(src.group(2)) if src else ""})
                path.write_text(json.dumps({"query": params["q"], "items": items}))
                time.sleep(2.0); return
            print("status", r.status_code, name, flush=True)
        except requests.RequestException as e:
            print("err", e, flush=True)
        time.sleep(30 * (attempt + 1))


if __name__ == "__main__":
    import sys
    months = pd.period_range("2017-01", "2026-10", freq="M")
    if "--reverse" in sys.argv: months = months[::-1]      # second worker; both skip files that already exist
    for m in months:
        a = m.start_time.strftime("%Y-%m-%d"); b = (m + 1).start_time.strftime("%Y-%m-%d")
        for k, q in TOPICS.items():
            fetch(q, a, b, f"topic_{k}_{m}")
        for d in OUTLETS:
            fetch(f"{OUTLET_Q} site:{d}", a, b, f"outlet_{d.replace('.', '_')}_{m}")
        print("month", m, flush=True)

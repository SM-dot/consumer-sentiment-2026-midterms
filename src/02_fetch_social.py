"""
02_fetch_social.py — SOCIAL-MEDIA side of the corpus.

Platform access reality (documented in docs/DATA_PROVENANCE.md):
  * Reddit: API and Pushshift-style archives refused unauthenticated requests from this machine (HTTP 403 / rate-limit page).
  * Bluesky public search: HTTP 403 without authentication.
  * X/Twitter: no free historical access.
  * Hacker News (Algolia API): free, complete history since 2007 -> used for the HISTORICAL social series.
    Caveat: audience is tech-sector heavy, younger, higher-income, male-skewed; NOT representative of Michigan respondents.
  * Mastodon (mastodon.social public hashtag timelines): free, recent months only -> used for the MONITORING window.

Outputs (data/raw/social/):
  hn_counts.csv           monthly hit counts per query x item type (story/comment)
  hn_items_<YYYY-MM>.json sampled items (title / comment text, points, num_comments, created_at)
  mastodon_<tag>.json     recent posts for each hashtag
"""
import time, json, hashlib, datetime as dt
from pathlib import Path
import requests, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "social"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (academic research; consumer-sentiment course project)"}
HN = "https://hn.algolia.com/api/v1/search_by_date"
END = dt.datetime(2026, 10, 16)

HN_QUERIES = ["inflation", "prices", "cost of living", "layoffs", "hiring", "recession", "economy", "tariffs", "mortgage rates", "jobs report"]
SAMPLE_QUERIES = ["inflation", "cost of living", "layoffs", "recession", "economy"]   # items drawn for AI coding
SAMPLE_PER_QUERY_MONTH = 12


def ts(d): return int(d.timestamp())


def hn(params):
    for a in range(6):
        try:
            r = requests.get(HN, params=params, headers=UA, timeout=60)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(5 * (a + 1))
    return None


def hn_counts():
    path = OUT / "hn_counts.csv"
    done = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["month", "query", "tag", "hits"])
    have = set(zip(done.month, done["query"], done.tag))
    rows = done.to_dict("records")
    for m in pd.period_range("2010-01", "2026-10", freq="M"):
        a, b = m.start_time, min((m + 1).start_time, pd.Timestamp(END))
        for q in HN_QUERIES:
            for tag in ["story", "comment"]:
                if (str(m), q, tag) in have:
                    continue
                j = hn({"query": f'"{q}"', "tags": tag, "hitsPerPage": 0,
                        "numericFilters": f"created_at_i>={ts(a)},created_at_i<{ts(b)}"})
                rows.append({"month": str(m), "query": q, "tag": tag, "hits": None if j is None else j.get("nbHits")})
                time.sleep(0.4)
        pd.DataFrame(rows).to_csv(path, index=False)
        print("hn counts", m, flush=True)


def hn_samples():
    for m in pd.period_range("2010-01", "2026-10", freq="M"):
        path = OUT / f"hn_items_{m}.json"
        if path.exists():
            continue
        a, b = m.start_time, min((m + 1).start_time, pd.Timestamp(END))
        items = []
        for q in SAMPLE_QUERIES:
            for tag in ["story", "comment"]:
                j = hn({"query": f'"{q}"', "tags": tag, "hitsPerPage": SAMPLE_PER_QUERY_MONTH,
                        "numericFilters": f"created_at_i>={ts(a)},created_at_i<{ts(b)}"})
                for h in (j or {}).get("hits", []):
                    items.append({"id": "hn_" + str(h.get("objectID")), "query": q, "type": tag,
                                  "created_at": h.get("created_at"), "title": h.get("title") or h.get("story_title"),
                                  "text": h.get("comment_text") if tag == "comment" else h.get("story_text"),
                                  "url": h.get("url"), "points": h.get("points"), "num_comments": h.get("num_comments"),
                                  "author_hash": hashlib.sha256((h.get("author") or "").encode()).hexdigest()[:10]})  # pseudonymised
                time.sleep(0.4)
        path.write_text(json.dumps(items))
        print("hn sample", m, len(items), flush=True)


def mastodon():
    for tag in ["inflation", "economy", "layoffs", "recession", "tariffs", "costofliving", "jobs"]:
        path = OUT / f"mastodon_{tag}.json"
        if path.exists():
            continue
        posts, max_id = [], None
        for _ in range(60):   # up to ~2400 posts per tag
            p = {"limit": 40}
            if max_id: p["max_id"] = max_id
            try:
                r = requests.get(f"https://mastodon.social/api/v1/timelines/tag/{tag}", params=p, headers=UA, timeout=60)
                batch = r.json() if r.status_code == 200 else []
            except Exception:
                batch = []
            if not batch:
                break
            for s in batch:
                posts.append({"id": "md_" + s["id"], "created_at": s["created_at"], "language": s.get("language"),
                              "content_html": s.get("content"), "reblogs": s.get("reblogs_count"),
                              "favourites": s.get("favourites_count"), "replies": s.get("replies_count"),
                              "bot": (s.get("account") or {}).get("bot"),
                              "acct_hash": hashlib.sha256(((s.get("account") or {}).get("acct", "")).encode()).hexdigest()[:10],
                              "acct_created": (s.get("account") or {}).get("created_at"),
                              "acct_statuses": (s.get("account") or {}).get("statuses_count")})
            max_id = batch[-1]["id"]
            time.sleep(1.2)
        path.write_text(json.dumps(posts))
        print("mastodon", tag, len(posts), posts[-1]["created_at"] if posts else None, flush=True)


if __name__ == "__main__":
    mastodon()
    hn_samples()
    hn_counts()

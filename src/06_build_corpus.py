"""
06_build_corpus.py — Assemble the balanced media corpus and its documentation tables (Section 2 of the brief).

Output: data/processed/corpus.csv  (one row per item) with
  item_id, platform {news, social}, source (domain / platform), unit {headline, story_title, comment, post},
  date, month, text, url, source_tier {national, wire, business, local_regional}, outlet_lean {left, lean_left,
  center, lean_right, right, unrated}, engagement fields, and quality flags:
  dup_exact (same normalised text seen earlier = syndication/repost), ad_flag, bot_flag, non_english, foreign_flag,
  relevant_kw (keyword eligibility pre-filter, codebook §0), topic_kw (dictionary salience baseline, codebook D2).
Also writes outputs/tables/corpus_composition.csv and corpus_missingness.csv for the dashboard and report.
"""
import json, re, glob, html, hashlib
import numpy as np, pandas as pd
from lib import ROOT, PROC, TAB

RAW = ROOT / "data" / "raw"

# Outlet tiers & lean. Lean labels follow AllSides media-bias ratings (public, accessed 2026-10); they are used ONLY to
# group outlets for the cross-source comparison, never as ground truth about any article.
NATIONAL = {"nytimes.com": "lean_left", "washingtonpost.com": "lean_left", "cnn.com": "left", "msnbc.com": "left",
            "nbcnews.com": "lean_left", "cbsnews.com": "lean_left", "abcnews.go.com": "lean_left", "npr.org": "lean_left",
            "politico.com": "lean_left", "huffpost.com": "left", "theguardian.com": "left", "axios.com": "lean_left",
            "usatoday.com": "lean_left", "thehill.com": "center", "newsweek.com": "center", "foxnews.com": "right",
            "foxbusiness.com": "lean_right", "breitbart.com": "right", "nypost.com": "lean_right",
            "washingtonexaminer.com": "lean_right", "dailywire.com": "right", "washingtontimes.com": "lean_right",
            "newsmax.com": "right", "dailycaller.com": "right", "theblaze.com": "right", "time.com": "lean_left",
            "vox.com": "left", "slate.com": "left", "salon.com": "left", "theatlantic.com": "lean_left",
            "latimes.com": "lean_left", "chicagotribune.com": "center", "nationalreview.com": "right",
            "yahoo.com": "lean_left", "news.yahoo.com": "lean_left", "msn.com": "unrated"}
WIRE = {"apnews.com": "lean_left", "reuters.com": "center", "upi.com": "center"}
BUSINESS = {"wsj.com": "center", "bloomberg.com": "lean_left", "cnbc.com": "lean_left", "marketwatch.com": "center",
            "finance.yahoo.com": "center", "forbes.com": "center", "businessinsider.com": "lean_left", "fortune.com": "center",
            "barrons.com": "center", "ft.com": "center", "investopedia.com": "unrated", "thestreet.com": "unrated",
            "fool.com": "unrated", "kiplinger.com": "unrated", "money.com": "unrated", "seekingalpha.com": "unrated",
            "zerohedge.com": "unrated", "benzinga.com": "unrated", "morningstar.com": "unrated"}

ECON_KW = re.compile(r"\b(econom\w*|inflation|deflation|disinflation|prices?|cost of living|grocer\w*|gas(oline)? prices?|"
                     r"layoffs?|laid off|job cuts?|jobs? report|unemploy\w*|jobless|hiring|payrolls?|wages?|"
                     r"recession|downturn|gdp|growth|tariffs?|trade war|mortgage|rent|housing|home prices?|"
                     r"interest rates?|the fed|federal reserve|rate cuts?|rate hikes?|stocks?|dow|s&p|nasdaq|"
                     r"consumer (sentiment|confidence|spending)|affordab\w*|paycheck|debt|credit card)\b", re.I)
FOREIGN = re.compile(r"\b(nigeria|india|china's|chinese economy|uk |britain|british|euro ?zone|europe|germany|japan|"
                     r"canada|canadian|australia|brazil|argentina|turkey|russia|pakistan|egypt|kenya|ghana|"
                     r"philippines|south africa|mexico's|ecb|bank of england|bank of japan|rbi|zimbabwe|venezuela|rwanda|uganda|tanzania|zambia|"
                     r"ethiopia|malawi|namibia|botswana|sri lanka|bangladesh|vietnam|indonesia|malaysia|thailand|korea|israel|iran|"
                     r"saudi|ukraine|poland|france|french|italy|italian|spain|spanish|greece|ireland|irish|scotland|sweden|norway|"
                     r"switzerland|swiss|new zealand|colombia|chile|peru|lebanon|kyrgyz\w*|kazakh\w*|uzbek\w*|mongolia|cambodia|"
                     r"myanmar|nepal|jamaica|trinidad|brunei|singapore|hong kong|taiwan|sweden|denmark|finland|austria|belgium|"
                     r"netherlands|dutch|portugal|romania|hungary|czech|serbia|croatia|morocco|tunisia|algeria|angola|mozambique|"
                     r"cameroon|senegal|ivory coast|sudan|somalia|afghanistan|iraq|syria|jordan|qatar|uae|dubai|oman|kuwait|bahrain|"
                     r"ecuador|bolivia|paraguay|uruguay|cuba|haiti|dominican|guatemala|honduras|el salvador|nicaragua|costa rica|panama)\b", re.I)
US_KW = re.compile(r"\b(u\.?s\.?|us|america\w*|federal|fed|nation(al)?|washington|biden|trump|harris|congress|"
                   r"white house|wall street|bls|bea|states?|county|city)\b", re.I)
ADS = re.compile(r"(sponsored|promo code|coupon|% off|discount code|sign up now|giveaway|casino|bonus code|buy now)", re.I)
TOPIC_KW = {   # dictionary salience baseline (codebook D2), first match wins in this order
    "inflation_falling": r"inflation (cool|eas|slow|fall|drop|declin|retreat|moderat)\w*|disinflation|prices? (fall|drop|declin|eas)\w*|deflation",
    "prices_rising": r"inflation|cost of living|prices?|grocer|expensive|afford",
    "layoffs": r"layoff|laid off|job cuts?|firing|unemploy\w* (rise|rises|jump|climb)|jobless claims (rise|jump)",
    "hiring": r"hiring|jobs? (gain|growth|added|report)|payroll|added \d|unemploy\w* (fall|drop|low)|wage gains?",
    "recession_risk": r"recession|downturn|slowdown|contraction",
    "housing_rates": r"mortgage|rent|housing|home (price|sale)|interest rate",
    "trade_tariffs": r"tariff|trade war|trade deal|import tax",
    "growth": r"\bgdp\b|growth|expansion|consumer spending|retail sales",
    "markets": r"stock|dow|s&p|nasdaq|wall street|market",
    "policy_fed": r"\bfed\b|federal reserve|powell|rate (cut|hike)|stimulus|budget|deficit",
}


def norm(t):
    t = html.unescape(re.sub("<[^>]+>", " ", t or ""))
    t = re.sub(r"\s+([,.:;!?%])", r"\1", t)          # GDELT tokenises punctuation ("18 . 55 pct")
    t = re.sub(r"(\d) \. (\d)", r"\1.\2", t)
    return re.sub(r"\s+", " ", t).strip()


def tier_lean(domain):
    d = domain.lower().replace("www.", "")
    for table, tier in [(WIRE, "wire"), (BUSINESS, "business"), (NATIONAL, "national")]:
        if d in table: return tier, table[d]
    return "local_regional", "unrated"


def news_items():
    rows = []
    for f in sorted(glob.glob(str(RAW / "gdelt" / "art_*.json"))):
        try: arts = json.load(open(f)).get("articles", [])
        except json.JSONDecodeError: continue
        for a in arts:
            tier, lean = tier_lean(a.get("domain", ""))
            rows.append({"platform": "news", "source": a.get("domain", "").lower(), "unit": "headline",
                         "date": pd.to_datetime(a["seendate"], format="%Y%m%dT%H%M%SZ"), "text": norm(a.get("title")),
                         "url": a.get("url"), "source_tier": tier, "outlet_lean": lean,
                         "non_english": a.get("language") != "English", "query_file": f.split("/")[-1]})
    return pd.DataFrame(rows)


def gnews_items():
    rows = []
    for f in sorted(glob.glob(str(RAW / "gnews" / "*.json"))):
        name = f.split("/")[-1][:-5]
        qtype = "outlet" if name.startswith("outlet_") else "topic"
        qkey = "_".join(name.split("_")[1:-1])
        for it in json.load(open(f)).get("items", []):
            dom = re.sub(r"^https?://(www\.)?", "", it.get("source_url", "")).split("/")[0].lower()
            title = norm(it.get("title"))
            sn = it.get("source_name", "")
            if sn and title.endswith(" - " + sn): title = title[: -len(sn) - 3]
            tier, lean = tier_lean(dom)
            if tier == "local_regional" and (dom.endswith(".gov") or dom.endswith(".org") or dom.endswith(".edu")):
                tier = "other_institutional"
            try: dt = pd.to_datetime(it["pubDate"], format="%a, %d %b %Y %H:%M:%S %Z").tz_localize(None)
            except Exception: continue
            rows.append({"platform": "news", "source": dom, "source_name": sn, "unit": "headline", "date": dt,
                         "text": title, "url": it.get("link"), "source_tier": tier, "outlet_lean": lean,
                         "non_english": False, "query_file": name, "query_type": qtype, "query_key": qkey,
                         "query_month": name.split("_")[-1]})
    G = pd.DataFrame(rows)
    if len(G):   # Google occasionally returns items outside the requested window; keep only in-window items
        G = G[G.date.dt.to_period("M").astype(str) == G.query_month]
    return G


def hn_items():
    rows = []
    for f in sorted(glob.glob(str(RAW / "social" / "hn_items_*.json"))):
        for h in json.load(open(f)):
            txt = h.get("text") if h["type"] == "comment" else h.get("title")
            rows.append({"platform": "social", "source": "news.ycombinator.com", "unit": "comment" if h["type"] == "comment" else "story_title",
                         "date": pd.to_datetime(h["created_at"]).tz_localize(None), "text": norm(txt)[:1000],
                         "url": h.get("url"), "source_tier": "social_hn", "outlet_lean": "unrated",
                         "eng_points": h.get("points"), "eng_comments": h.get("num_comments"),
                         "author_hash": h.get("author_hash"), "item_native_id": h["id"], "non_english": False})
    return pd.DataFrame(rows)


def mastodon_items():
    rows = []
    for f in sorted(glob.glob(str(RAW / "social" / "mastodon_*.json"))):
        for s in json.load(open(f)):
            rows.append({"platform": "social", "source": "mastodon", "unit": "post",
                         "date": pd.to_datetime(s["created_at"]).tz_localize(None), "text": norm(s.get("content_html"))[:1000],
                         "url": None, "source_tier": "social_mastodon", "outlet_lean": "unrated",
                         "eng_favourites": s.get("favourites"), "eng_reblogs": s.get("reblogs"), "eng_replies": s.get("replies"),
                         "bot_declared": bool(s.get("bot")), "author_hash": s.get("acct_hash"),
                         "acct_statuses": s.get("acct_statuses"), "item_native_id": s["id"],
                         "non_english": (s.get("language") or "en") != "en", "hashtag_file": f.split("/")[-1]})
    return pd.DataFrame(rows)


def main():
    C = pd.concat([news_items(), gnews_items(), hn_items(), mastodon_items()], ignore_index=True)
    C = C[C.text.str.len() > 8].copy()
    C["month"] = C.date.dt.to_period("M").astype(str)
    key = C.text.str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True).str.strip()
    C["norm_hash"] = key.map(lambda s: hashlib.md5(s.encode()).hexdigest()[:12])
    C = C.sort_values("date")
    C["dup_exact"] = C.duplicated(["norm_hash"], keep="first")              # syndication / repost / cross-post
    C["dup_count"] = C.groupby("norm_hash").norm_hash.transform("size")
    C["ad_flag"] = C.text.str.contains(ADS)
    # Automated-activity heuristics (Mastodon): declared bot accounts, or > 50 posts in our sample from one account,
    # or accounts with > 100k lifetime statuses (feed-relay accounts). HN has no bot flag; vote-ring detection n/a.
    acct_n = C[C.source == "mastodon"].groupby("author_hash").size()
    C["bot_flag"] = (C.get("bot_declared", False).fillna(False).astype(bool)
                     | ((C.source == "mastodon") & C.author_hash.map(acct_n).fillna(0).gt(50))
                     | ((C.source == "mastodon") & pd.to_numeric(C.get("acct_statuses"), errors="coerce").fillna(0).gt(100000)))
    C["foreign_flag"] = C.text.str.contains(FOREIGN) & ~C.text.str.contains(r"\bu\.?s\.?\b|america", case=False)
    C["relevant_kw"] = C.text.str.contains(ECON_KW) & ~C.foreign_flag & ~C.ad_flag & ~C.non_english.fillna(False).astype(bool)
    C["topic_kw"] = "other"
    for t, pat in reversed(list(TOPIC_KW.items())):          # reversed so the FIRST listed pattern wins
        C.loc[C.text.str.contains(pat, case=False, regex=True), "topic_kw"] = t
    # Stable content-hash IDs (rebuilds must not re-key items that were already AI-coded / human-labelled)
    C["item_id"] = [f"{p[:1]}_" + hashlib.md5(f"{s}|{d}|{t}".encode()).hexdigest()[:12]
                    for p, s, d, t in zip(C.platform, C.source, C.date, C.text)]
    C = C.drop_duplicates("item_id")
    C.to_csv(PROC / "corpus.csv", index=False)

    # ---------------- documentation tables
    comp = C.groupby(["platform", "unit", "source_tier"]).agg(
        items=("item_id", "size"), relevant=("relevant_kw", "sum"), duplicates=("dup_exact", "sum"),
        ads=("ad_flag", "sum"), bot=("bot_flag", "sum"), foreign=("foreign_flag", "sum"),
        first=("date", "min"), last=("date", "max"), sources=("source", "nunique")).reset_index()
    comp.to_csv(TAB / "corpus_composition.csv", index=False)
    months = pd.period_range("2017-01", "2026-10", freq="M").astype(str)
    miss = pd.DataFrame(index=months)
    for name, mask in {"news_headlines": C.platform.eq("news"), "hn_items": C.source.eq("news.ycombinator.com"),
                       "mastodon_posts": C.source.eq("mastodon")}.items():
        miss[name] = C[mask & C.relevant_kw & ~C.dup_exact].groupby("month").size().reindex(months).fillna(0).astype(int)
    if "query_type" in C:
        q = C[C.platform.eq("news") & C.query_type.notna()].groupby(["query_month", "query_type"]).size().unstack(fill_value=0)
        miss = miss.join(q.add_prefix("gnews_returned_"), how="left")
    miss.index.name = "month"; miss.to_csv(TAB / "corpus_missingness.csv")
    lean = C[(C.platform == "news")].groupby(["source_tier", "outlet_lean"]).size().unstack(fill_value=0)
    lean.to_csv(TAB / "corpus_lean_by_tier.csv")
    print(comp.to_string()); print(lean); print("total", len(C), "relevant non-dup", int((C.relevant_kw & ~C.dup_exact).sum()))


if __name__ == "__main__":
    main()

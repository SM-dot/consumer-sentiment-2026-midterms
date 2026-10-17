"""
07_ai_code.py — Apply the frozen codebook (docs/CODEBOOK.md v1.0) with AI models, plus a dictionary baseline.

AI coder (local, deterministic, version-pinned — revisions recorded in outputs/model_versions.json):
  * Zero-shot NLI  : MoritzLaurer/deberta-v3-base-zeroshot-v2.0  -> relevance, tone, topic, framing, attribution
                     (hypotheses below are a direct transcription of the codebook definitions)
  * FinBERT        : ProsusAI/finbert                             -> secondary tone model (financial-domain)
  * Emotion model  : j-hartmann/emotion-english-distilroberta-base -> emotional wording (with a loaded-word lexicon)
Dictionary baseline: rule-based economic-direction lexicon (DICT below) -> tone & topic (topic_kw from 06).
Optional LLM coder : prompts/llm_coding_prompt_v1.md + src/07b_llm_code_api.py (Claude via Anthropic API).

Usage: python src/07_ai_code.py [--items data/processed/corpus.csv] [--limit N] [--out data/processed/ai_codes.csv]
       python src/07_ai_code.py --swap   (counterfactual name/source-swap test; writes outputs/tables/swap_test.csv)
"""
import argparse, json, re, time
import numpy as np, pandas as pd, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from lib import load_corpus, ROOT, PROC, TAB, OUT

DEV = "mps" if torch.backends.mps.is_available() else "cpu"
MODELS = {
    "nli": ("MoritzLaurer/deberta-v3-base-zeroshot-v2.0", "8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8"),
    "finbert": ("ProsusAI/finbert", "0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031"),
    "emotion": ("j-hartmann/emotion-english-distilroberta-base", "0e1cd914e3d46199ed785853e12b57304e04178b"),
}

# ---------------------------------------------------------------- hypotheses (codebook transcription)
H_REL = "This text is about the United States economy, prices, jobs, interest rates, or household finances."
# Tone v2 (2026-10-16, after a development check — see README "AI coder development log"):
# v1 hypotheses ("good/bad news ... for American households") were almost never entailed by the NLI model (98.9% neutral),
# so tone uses the standard sentiment template plus a codebook polarity rule for price-direction headlines, which generic
# sentiment gets backwards ("inflation cools", "gas prices fall" read as negative).
H_TONE = {"positive": "The sentiment of this text is positive.",
          "negative": "The sentiment of this text is negative."}
TONE_MARGIN = 0.15
PRICE_UP = re.compile(r"(inflation|prices?|costs?|rents?|cpi|pce|grocer\w*|gas)\W+(\w+\W+){0,3}(ris|rose|jump|surg|soar|climb|spik|accelerat|hot|higher|skyrocket|up)\w*", re.I)
PRICE_DOWN = re.compile(r"(inflation|prices?|costs?|rents?|cpi|pce|grocer\w*|gas)\W+(\w+\W+){0,3}(cool|eas|slow|fall|fell|drop|declin|moderat|retreat|lower|down|dip|tumbl|plung)\w*", re.I)


def tone_v2(texts, nli, topics):
    t = nli.entail(texts, list(H_TONE.values()))
    score = t[:, 0] - t[:, 1]
    lab = np.where(score < -TONE_MARGIN, "negative", np.where(score > TONE_MARGIN, "positive", "neutral"))
    rule = np.array(["none"] * len(texts), dtype=object)
    for i, (x, tp) in enumerate(zip(texts, topics)):
        if tp in ("prices_rising", "inflation_falling", "housing_rates"):
            up, dn = bool(PRICE_UP.search(x)), bool(PRICE_DOWN.search(x))
            if up and not dn: lab[i], score[i], rule[i] = "negative", -abs(score[i]) if score[i] else -0.5, "price_up"
            elif dn and not up: lab[i], score[i], rule[i] = "positive", abs(score[i]) if score[i] else 0.5, "price_down"
    return lab, score, rule
H_TOPIC = {"prices_rising": "This text is mainly about rising prices, inflation, or the cost of living.",
           "inflation_falling": "This text is mainly about inflation cooling or prices falling.",
           "layoffs": "This text is mainly about layoffs, job cuts, or rising unemployment.",
           "hiring": "This text is mainly about hiring, job gains, or low unemployment.",
           "growth": "This text is mainly about economic growth, GDP, or consumer spending.",
           "recession_risk": "This text is mainly about a recession or an economic downturn.",
           "housing_rates": "This text is mainly about mortgage rates, rents, home prices, or interest rates.",
           "trade_tariffs": "This text is mainly about tariffs or trade policy.",
           "markets": "This text is mainly about the stock market.",
           "policy_fed": "This text is mainly about the Federal Reserve or government economic policy.",
           "other": "This text is mainly about some other topic."}
H_PRICE = {"level": "This text describes how high prices or costs are.",
           "rate": "This text reports an inflation rate or a percentage change in prices."}
H_UNIT = {"aggregate": "This text is about national economic statistics or the economy as a whole.",
          "household": "This text is about the experiences of families, workers, or consumers."}
H_TIME = {"current": "This text describes current economic conditions.",
          "forecast": "This text is about a prediction or forecast of the future economy.",
          "past": "This text is about past economic events or history."}
H_ATTR = {("president_admin", "blame"): "This text blames the president or the administration for economic problems.",
          ("president_admin", "credit"): "This text credits the president or the administration for economic improvements.",
          ("congress", "blame"): "This text blames Congress or a political party for economic problems.",
          ("fed", "blame"): "This text blames the Federal Reserve for economic problems.",
          ("business", "blame"): "This text blames companies or corporations for economic problems.",
          ("foreign", "blame"): "This text blames foreign countries or trade partners for economic problems."}
PARTY_D = re.compile(r"\b(democrat\w*|biden|harris|obama|pelosi|schumer|bidenomics)\b", re.I)
PARTY_R = re.compile(r"\b(republican\w*|gop|trump|maga|vance|mcconnell|johnson's|trumponomics)\b", re.I)
LOADED = re.compile(r"\b(soar\w*|skyrocket\w*|surg\w*|plung\w*|plummet\w*|crash\w*|crush\w*|brutal|slam\w*|nightmare|"
                    r"catastroph\w*|disaster\w*|bloodbath|carnage|devastat\w*|crisis|panic\w*|alarm\w*|staggering|"
                    r"boom\w*|roar\w*|blowout|stunning|shock\w*|spiral\w*|freefall|tank\w*|gouging|painful|squeez\w*|"
                    r"agony|dire|grim|bleak|terrif\w*|horrif\w*|insane|outrage\w*)\b", re.I)

# ---------------------------------------------------------------- dictionary baseline (direction-aware rules)
NEG_PAT = [r"(inflation|prices?|costs?|rents?|cpi|pce)\W+(\w+\W+){0,3}(ris|rose|jump|surg|soar|climb|spik|accelerat|hot|high)\w*",
           r"(unemploy\w*|jobless\w*)\W+(\w+\W+){0,3}(ris|rose|jump|climb|surg|high)\w*", r"layoff|laid off|job cuts?|lose jobs?",
           r"recession|downturn|slowdown|contract\w*|shrink\w*|slump\w*|plung\w*|crash\w*|tumbl\w*|sell-?off",
           r"(stocks?|dow|s&p|nasdaq|markets?)\W+(\w+\W+){0,2}(fall|fell|drop|slid|sink|sank|tumbl|plung)\w*",
           r"unaffordab\w*|struggl\w*|squeez\w*|pain\w*|worr\w*|fear\w*|bankrupt\w*|default\w*|delinquen\w*|crisis|tariffs? (hit|hurt|raise)"]
POS_PAT = [r"(inflation|prices?|costs?|cpi|pce)\W+(\w+\W+){0,3}(cool|eas|slow|fall|fell|drop|declin|moderat|retreat|low)\w*",
           r"(unemploy\w*|jobless\w*)\W+(\w+\W+){0,3}(fall|fell|drop|declin|low)\w*",
           r"(add|added|adds|gain|gains|creat\w*)\W+(\w+\W+){0,3}jobs?|hiring (surge|jump|rebound|strong)|jobs? (boom|surge)|strong jobs",
           r"(econom\w*|gdp|growth|spending|wages?|incomes?)\W+(\w+\W+){0,3}(grow|grew|beat|rebound|surge|strong|robust|accelerat|rise|rose|boom)\w*",
           r"(stocks?|dow|s&p|nasdaq|markets?)\W+(\w+\W+){0,2}(rall|surg|soar|gain|record|climb|jump|rise|rose)\w*",
           r"record high|soft landing|recover\w*|optimis\w*|confidence (rise|rises|jumps|improves)|rate cuts?"]


def dict_tone(t):
    neg = sum(bool(re.search(p, t, re.I)) for p in NEG_PAT); pos = sum(bool(re.search(p, t, re.I)) for p in POS_PAT)
    return "negative" if neg > pos else "positive" if pos > neg else "neutral", pos - neg


# ---------------------------------------------------------------- model wrappers
class NLI:
    def __init__(self):
        name, rev = MODELS["nli"]
        self.tok = AutoTokenizer.from_pretrained(name, revision=rev)
        self.m = AutoModelForSequenceClassification.from_pretrained(name, revision=rev).to(DEV).eval()
        if DEV == "mps": self.m = self.m.half()          # fp16 on Apple GPU: ~10x faster; labels checked vs fp32 in README
        self.ent = [i for i, l in self.m.config.id2label.items() if l.lower().startswith("entail")][0]

    @torch.no_grad()
    def entail(self, premises, hyps, bs=64):
        """P(entailment) for each (premise, hypothesis) pair; returns array len(premises) x len(hyps)."""
        pairs = [(p, h) for p in premises for h in hyps]
        order = np.argsort([len(p) + len(h) for p, h in pairs])     # length-sorted batches minimise padding
        res = np.empty(len(pairs), dtype=np.float32)
        for i in range(0, len(pairs), bs):
            idx = order[i:i + bs]; b = [pairs[j] for j in idx]
            enc = self.tok([p for p, _ in b], [h for _, h in b], truncation="only_first", max_length=128,
                           padding=True, return_tensors="pt").to(DEV)
            logits = self.m(**enc).logits.float()
            res[idx] = torch.softmax(logits, -1)[:, self.ent].cpu().numpy()
        return res.reshape(len(premises), len(hyps))


class Clf:
    def __init__(self, key):
        name, rev = MODELS[key]
        self.tok = AutoTokenizer.from_pretrained(name, revision=rev)
        self.m = AutoModelForSequenceClassification.from_pretrained(name, revision=rev).to(DEV).eval()
        if DEV == "mps": self.m = self.m.half()
        self.labels = [self.m.config.id2label[i].lower() for i in range(self.m.config.num_labels)]

    @torch.no_grad()
    def probs(self, texts, bs=64):
        out = []
        for i in range(0, len(texts), bs):
            enc = self.tok(texts[i:i + bs], truncation=True, max_length=192, padding=True, return_tensors="pt").to(DEV)
            out.append(torch.softmax(self.m(**enc).logits.float(), -1).cpu().numpy())
        return np.concatenate(out)


def code(texts, nli, fin, emo):
    """Apply all dimensions to a list of texts. Single-label dimensions = argmax entailment across hypotheses
    (standard zero-shot); multi-label sub-codes = independent entailment > 0.5."""
    R = {}
    rel = nli.entail(texts, [H_REL])[:, 0]; R["ai_relevance_p"] = rel
    top = nli.entail(texts, list(H_TOPIC.values())); R["ai_topic"] = np.array(list(H_TOPIC))[top.argmax(1)]
    R["ai_tone"], R["ai_tone_score"], R["ai_tone_rule"] = tone_v2(texts, nli, R["ai_topic"])
    pr = nli.entail(texts, list(H_PRICE.values())) > 0.5
    R["ai_price_frame"] = np.where(pr[:, 0] & pr[:, 1], "both", np.where(pr[:, 0], "level", np.where(pr[:, 1], "rate", "none")))
    un = nli.entail(texts, list(H_UNIT.values())) > 0.5
    R["ai_unit_frame"] = np.where(un[:, 0] & un[:, 1], "both", np.where(un[:, 0], "aggregate", np.where(un[:, 1], "household", "none")))
    tm = nli.entail(texts, list(H_TIME.values())); R["ai_time_frame"] = np.array(list(H_TIME))[tm.argmax(1)]
    at = nli.entail(texts, list(H_ATTR.values())); best = at.argmax(1); keys = list(H_ATTR)
    R["ai_attr_target"] = np.where(at.max(1) > 0.5, [keys[i][0] for i in best], "none")
    R["ai_attr_direction"] = np.where(at.max(1) > 0.5, [keys[i][1] for i in best], "none")
    f = fin.probs(texts); lab = fin.labels
    R["finbert_tone"] = np.array(lab)[f.argmax(1)]
    R["finbert_score"] = f[:, lab.index("positive")] - f[:, lab.index("negative")]
    e = emo.probs(texts); R["emo_nonneutral_p"] = 1 - e[:, emo.labels.index("neutral")]
    R["emo_top"] = np.array(emo.labels)[e.argmax(1)]
    loaded = np.array([len(LOADED.findall(t)) for t in texts])
    R["loaded_words"] = loaded
    R["ai_emotional"] = np.where((loaded >= 2) | ((loaded >= 1) & (R["emo_nonneutral_p"] > .8)), 2,
                                 np.where((loaded >= 1) | (R["emo_nonneutral_p"] > .7), 1, 0))
    d = [dict_tone(t) for t in texts]
    R["dict_tone"] = [x[0] for x in d]; R["dict_score"] = [x[1] for x in d]
    R["party_named"] = ["both" if PARTY_D.search(t) and PARTY_R.search(t) else "D" if PARTY_D.search(t)
                        else "R" if PARTY_R.search(t) else "none" for t in texts]
    return pd.DataFrame(R)


def sample_for_coding(C, topic_cap=12, outlet_cap=10, hn_cap=15):
    """Stratified coding sample (fixed seed; documented in README):
       News   : <= topic_cap headlines per month x topic query, <= outlet_cap per month x outlet query
                (Google News), all GDELT-list headlines; relevant, non-duplicate, non-ad only.
       HN     : <= hn_cap items per month x unit (story title / comment).
       Mastodon: all relevant, non-duplicate, non-bot posts.
    Duplicates/ads/bots stay in the corpus (and in composition tables) but are not coded."""
    base = C[C.relevant_kw & ~C.dup_exact & ~C.ad_flag & ~C.bot_flag.fillna(False)]
    news = base[base.platform == "news"].copy()
    news["qf"] = news.query_file.fillna("gdelt")
    cap = lambda g: g.sample(min(len(g), outlet_cap if str(g.name).startswith("outlet_") else
                                 (topic_cap if str(g.name).startswith("topic_") else len(g))), random_state=7)
    news = news.groupby("qf", group_keys=False).apply(cap)
    hn = base[base.source == "news.ycombinator.com"]
    hn = hn.groupby(["month", "unit"], group_keys=False).apply(lambda g: g.sample(min(len(g), hn_cap), random_state=7))
    md = base[base.source == "mastodon"]
    return pd.concat([news, hn, md])


def swap_text(t):
    """Counterfactual: swap partisan names/labels; returns (swapped_text, changed?)."""
    pairs = [("Biden", "Trump"), ("Bidenomics", "Trumponomics"), ("Democrats", "Republicans"), ("Democratic", "Republican"),
             ("Harris", "Vance"), ("Obama", "Bush"), ("Pelosi", "McConnell"), ("Schumer", "Thune")]
    m = {}
    for a, b in pairs: m[a], m[b] = b, a
    pat = re.compile(r"\b(" + "|".join(map(re.escape, m)) + r")\b")
    new = pat.sub(lambda x: m[x.group(0)], t)
    return new, new != t


def run_swap(nli, fin, emo, codes, C):
    """Name-swap test on items naming a party/politician + source-label test on a random sample."""
    df = C.merge(codes, on="item_id")
    pol = df[df.party_named != "none"].sample(min(400, (df.party_named != "none").sum()), random_state=11)
    sw = [swap_text(t) for t in pol.text]; keep = [c for _, c in sw]
    pol = pol[keep]; swapped = [s for s, c in sw if c]
    a = code(list(pol.text), nli, fin, emo); b = code(swapped, nli, fin, emo)
    res = pd.DataFrame({"item_id": pol.item_id.values, "orig": pol.text.values, "swapped": swapped,
                        "tone_o": a.ai_tone, "tone_s": b.ai_tone, "score_o": a.ai_tone_score, "score_s": b.ai_tone_score,
                        "attr_o": a.ai_attr_target + ":" + a.ai_attr_direction, "attr_s": b.ai_attr_target + ":" + b.ai_attr_direction,
                        "fin_o": a.finbert_tone, "fin_s": b.finbert_tone, "party_o": pol.party_named.values})
    res.to_csv(TAB / "swap_test_items.csv", index=False)
    smp = df.sample(400, random_state=12)
    texts = list(smp.text)
    labs = {"Fox News": [f"Fox News: {t}" for t in texts], "CNN": [f"CNN: {t}" for t in texts],
            "none": texts}
    lab_codes = {k: code(v, nli, fin, emo) for k, v in labs.items()}
    summ = [{"test": "party/name swap", "n": len(res), "tone_flip_rate": (res.tone_o != res.tone_s).mean(),
             "mean_abs_score_change": (res.score_o - res.score_s).abs().mean(),
             "mean_score_change_D_to_R": (res.score_s - res.score_o)[res.party_o == "D"].mean(),
             "mean_score_change_R_to_D": (res.score_s - res.score_o)[res.party_o == "R"].mean(),
             "attribution_flip_rate": (res.attr_o != res.attr_s).mean(), "finbert_flip_rate": (res.fin_o != res.fin_s).mean()}]
    for k in ["Fox News", "CNN"]:
        summ.append({"test": f"source label '{k}:' vs none", "n": 400,
                     "tone_flip_rate": (lab_codes[k].ai_tone != lab_codes["none"].ai_tone).mean(),
                     "mean_abs_score_change": (lab_codes[k].ai_tone_score - lab_codes["none"].ai_tone_score).abs().mean(),
                     "mean_signed_score_change": (lab_codes[k].ai_tone_score - lab_codes["none"].ai_tone_score).mean(),
                     "attribution_flip_rate": (lab_codes[k].ai_attr_target != lab_codes["none"].ai_attr_target).mean(),
                     "finbert_flip_rate": (lab_codes[k].finbert_tone != lab_codes["none"].finbert_tone).mean()})
    summ.append({"test": "Fox vs CNN label (direct)", "n": 400,
                 "tone_flip_rate": (lab_codes["Fox News"].ai_tone != lab_codes["CNN"].ai_tone).mean(),
                 "mean_signed_score_change": (lab_codes["Fox News"].ai_tone_score - lab_codes["CNN"].ai_tone_score).mean()})
    pd.DataFrame(summ).to_csv(TAB / "swap_test.csv", index=False)
    print(pd.DataFrame(summ).round(3).to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--swap", action="store_true"); ap.add_argument("--retone", action="store_true")
    a = ap.parse_args()
    C = load_corpus()
    nli, fin, emo = NLI(), Clf("finbert"), Clf("emotion")
    (OUT / "model_versions.json").write_text(json.dumps({k: {"name": v[0], "revision": v[1]} for k, v in MODELS.items()}
                                                        | {"torch": torch.__version__, "device": DEV, "codebook": "v1.0"}, indent=2))
    if a.retone:   # recompute tone v2 for already-coded items (keeps v1 in ai_tone_v1)
        A = pd.read_csv(PROC / "ai_codes.csv"); txt = C.set_index("item_id").text.astype(str)
        if "ai_tone_v1" not in A: A["ai_tone_v1"] = A["ai_tone"]
        lab, score, rule = tone_v2(list(txt.reindex(A.item_id).fillna("")), nli, A.ai_topic)
        A["ai_tone"], A["ai_tone_score"], A["ai_tone_rule"] = lab, score, rule
        A.to_csv(PROC / "ai_codes.csv", index=False); print(A.ai_tone.value_counts(), A.ai_tone_rule.value_counts()); return
    if a.swap:
        run_swap(nli, fin, emo, pd.read_csv(PROC / "ai_codes.csv"), C); return
    S = sample_for_coding(C)
    if a.limit: S = S.sample(a.limit, random_state=1)
    path = PROC / "ai_codes.csv"
    done = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["item_id"])
    S = S[~S.item_id.isin(done.item_id)]
    print("to code:", len(S), "device", DEV, flush=True)
    chunks = []
    for i in range(0, len(S), 2000):
        t0 = time.time(); part = S.iloc[i:i + 2000]
        r = code(list(part.text.astype(str)), nli, fin, emo); r.insert(0, "item_id", part.item_id.values)
        done = pd.concat([done, r], ignore_index=True); done.to_csv(path, index=False)
        print(f"coded {i+len(part)}/{len(S)} in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

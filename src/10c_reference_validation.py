"""
10c_reference_validation.py — Validation with what is actually available (stated plainly in the report):
  * LLM REFERENCE SET: 300 stratified items labelled by Claude Opus 5.5 (in-session) on relevance + household tone,
    following the one-tap rule, blind to the AI-coder outputs. It is an AI benchmark, NOT human ground truth.
  * HUMAN SPOT-CHECK: every item the human annotator has labelled in the labelling tool (main set).
Outputs: outputs/tables/validation_vs_llm_reference.csv, validation_human_spotcheck.csv
"""
import json, glob
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from lib import ROOT, PROC, TAB

LAB = ROOT / "labeling"
key = pd.read_csv(LAB / "_key_hidden.csv").set_index("item_id")
ai = pd.read_csv(PROC / "ai_codes.csv").set_index("item_id")
ref = pd.read_csv(PROC / "llm_codes.csv", dtype=str).set_index("item_id")

# human labels from the tool export (labeling/app_export/labels/*.json)
hum = {}
for f in glob.glob(str(LAB / "app_export" / "labels" / "*.json")):
    d = json.load(open(f)); d = d.get("data", d)
    for k, v in (d.get("main") or {}).items():
        hum[k] = {"relevant": v.get("relevant"), "tone": v.get("tone")}
H = pd.DataFrame(hum).T
D = key[["text", "src_grp"]].join(ai[["ai_tone", "finbert_tone", "ai_relevance_p"]]).join(ref[["relevant", "tone"]].add_prefix("ref_"))
D["dict_tone"] = key["dict_tone"]
D["ai_relevant"] = np.where(D.ai_relevance_p > 0.5, "1", "0")
if len(H): D = D.join(H.add_prefix("hum_"))


def scores(y, p, label):
    y, p = y.astype(str), p.astype(str)
    return {"comparison": label, "n": len(y), "accuracy": (y == p).mean(), "macro_F1": f1_score(y, p, average="macro"),
            "kappa": cohen_kappa_score(y, p)}


rows = []
R = D[D.ref_relevant == "1"].copy()
clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True), LogisticRegression(max_iter=2000, class_weight="balanced"))
R["tfidf_tone"] = cross_val_predict(clf, R.text, R.ref_tone, cv=StratifiedKFold(5, shuffle=True, random_state=0))
for name, col in [("AI coder v2 (NLI + price rule)", "ai_tone"), ("FinBERT", "finbert_tone"), ("Dictionary", "dict_tone"),
                  ("TF-IDF + LR (5-fold CV, trained on LLM reference)", "tfidf_tone")]:
    rows.append({"reference": "LLM reference (300; relevant items)", "dimension": "tone", **scores(R.ref_tone, R[col], name)})
    for g, sub in R.groupby("src_grp"):
        rows.append({"reference": "LLM reference", "dimension": "tone", "subset": g, **scores(sub.ref_tone, sub[col], name)})
rows.append({"reference": "LLM reference (300)", "dimension": "relevance", **scores(D.ref_relevant, D.ai_relevant, "AI coder relevance (NLI p>0.5)")})
V = pd.DataFrame(rows); V.to_csv(TAB / "validation_vs_llm_reference.csv", index=False)
print(V[V.get("subset").isna() if "subset" in V else slice(None)].round(3).to_string())

hs = []
if len(H):
    Hh = D.dropna(subset=["hum_relevant"])
    hs.append({"dimension": "relevance", **scores(Hh.hum_relevant, Hh.ref_relevant, "LLM reference vs human")})
    hs.append({"dimension": "relevance", **scores(Hh.hum_relevant, Hh.ai_relevant, "AI coder vs human")})
    Ht = Hh[(Hh.hum_relevant == "1")]
    for name, col in [("LLM reference vs human", "ref_tone"), ("AI coder v2 vs human", "ai_tone"), ("FinBERT vs human", "finbert_tone"), ("Dictionary vs human", "dict_tone")]:
        hs.append({"dimension": "tone", **scores(Ht.hum_tone, Ht[col].fillna("not_relevant"), name)})
S = pd.DataFrame(hs); S.to_csv(TAB / "validation_human_spotcheck.csv", index=False); print(S.round(3).to_string())

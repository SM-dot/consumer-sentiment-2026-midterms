"""
10_validation.py — Inter-annotator agreement, adjudication, and AI-vs-human performance.

  python src/10_validation.py --agreement   # after A and B finish (before adjudication)
  python src/10_validation.py               # after adjudication: full evaluation of all coders vs gold

Coders evaluated against adjudicated human gold:
  ai (zero-shot NLI, codebook hypotheses) | finbert | dictionary | conventional classifier (TF-IDF + logistic
  regression, 5-fold stratified CV on the gold set — so it is trained on the SAME human labels it is tested on,
  out-of-fold) | llm (optional, if data/processed/llm_codes.csv exists).
If human files are not yet complete the script says so and only reports MACHINE-MACHINE agreement, which is a
consistency check, NOT validation.
"""
import sys
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score, classification_report, confusion_matrix, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from lib import ROOT, PROC, TAB

LAB = ROOT / "labeling"
DIMS = ["relevant", "tone", "emotional", "topic", "price_frame", "unit_frame", "time_frame", "attr_target", "attr_direction"]
ORDINAL = {"tone": ["negative", "neutral", "positive"], "emotional": ["0", "1", "2"]}


def kalpha(a, b, ordinal_levels=None):
    """Krippendorff's alpha for two coders, nominal or ordinal (interval on ranks), no missing within pairs."""
    ok = a.notna() & b.notna() & (a != "") & (b != "")
    a, b = a[ok].astype(str), b[ok].astype(str)
    if len(a) < 2: return np.nan
    vals = sorted(set(a) | set(b))
    if ordinal_levels:
        rank = {v: i for i, v in enumerate(ordinal_levels)}
        if not set(vals) <= set(rank): ordinal_levels = None
    def delta(x, y):
        return (rank[x] - rank[y]) ** 2 if ordinal_levels else float(x != y)
    pairs = list(zip(a, b)) + list(zip(b, a))
    n = len(pairs)
    Do = np.mean([delta(x, y) for x, y in pairs])
    allv = list(a) + list(b)
    De = np.mean([delta(x, y) for i, x in enumerate(allv) for j, y in enumerate(allv) if i != j]) if len(allv) < 1500 else \
        np.mean([delta(np.random.choice(allv), np.random.choice(allv)) for _ in range(200000)])
    return 1 - Do / De if De > 0 else np.nan


def read(path):
    x = pd.read_excel(path, sheet_name="items", dtype=str)
    return x.set_index("item_id")[DIMS + (["adjudication_reason"] if "adjudication_reason" in x else [])]


def complete(df):
    return df["relevant"].notna().mean() > 0.98


def agreement():
    A, B = read(LAB / "annotator_A.xlsx"), read(LAB / "annotator_B.xlsx")
    if not (complete(A) and complete(B)):
        print(f"Human labels incomplete: A {A.relevant.notna().sum()}/300, B {B.relevant.notna().sum()}/300."); return None
    B = B.loc[A.index]; rows = []
    for d in DIMS:
        if A[d].isna().all() and B[d].isna().all(): continue      # dimension not human-labelled (one-tap app labels relevance + tone)
        mask = (A.relevant == "1") & (B.relevant == "1") if d != "relevant" else pd.Series(True, index=A.index)
        a, b = A.loc[mask, d].fillna(""), B.loc[mask, d].fillna("")
        rows.append({"dimension": d, "n": int(mask.sum()), "pct_agree": (a == b).mean(),
                     "cohen_kappa": cohen_kappa_score(a, b) if a.nunique() > 1 else np.nan,
                     "kripp_alpha": kalpha(a, b, ORDINAL.get(d))})
    R = pd.DataFrame(rows); R.to_csv(TAB / "human_agreement.csv", index=False); print(R.round(3).to_string())
    # adjudication sheet: agreed values pre-filled, disagreements blank with both labels shown
    adj = A.copy()
    for d in DIMS:
        adj[d + "_A"], adj[d + "_B"] = A[d], B[d]
        adj[d] = np.where(A[d].fillna("") == B[d].fillna(""), A[d], "")
    adj["adjudication_reason"] = ""
    key = pd.read_csv(LAB / "_key_hidden.csv").set_index("item_id")[["text"]]
    adj.join(key).reset_index().to_excel(LAB / "adjudication.xlsx", sheet_name="items", index=False)
    print("Wrote labeling/adjudication.xlsx — resolve blank cells, then run without --agreement.")
    return R


def single_annotator():
    """Single-annotator design (only one person available): gold = annotator A's main labels; reliability =
    intra-rater (test–retest) agreement on the 60 re-check items. Deviation from the brief's two-annotator design."""
    A = read(LAB / "annotator_A.xlsx")
    if not complete(A):
        print(f"Labels incomplete: {A.relevant.notna().sum()}/300."); return None
    rows = []
    if (LAB / "recheck_A.xlsx").exists():
        R = read(LAB / "recheck_A.xlsx"); A2 = A.loc[R.index]
        for d in ["relevant", "tone"]:
            a, b = A2[d].fillna("none"), R[d].fillna("none")
            rows.append({"dimension": d, "design": "intra-rater test–retest (same annotator, re-labelled later)", "n": len(a),
                         "pct_agree": (a == b).mean(), "cohen_kappa": cohen_kappa_score(a, b),
                         "kripp_alpha": kalpha(a, b, ORDINAL.get(d))})
    if rows:
        pd.DataFrame(rows).to_csv(TAB / "human_agreement.csv", index=False); print(pd.DataFrame(rows).round(3))
    elif (TAB / "human_agreement.csv").exists():
        (TAB / "human_agreement.csv").unlink()
    A.reset_index().to_excel(LAB / "adjudication.xlsx", sheet_name="items", index=False)   # gold = single annotator
    return True


def evaluate():
    if not (LAB / "annotator_B.xlsx").exists() or read(LAB / "annotator_B.xlsx").relevant.isna().all():
        if (LAB / "annotator_A.xlsx").exists() and not read(LAB / "annotator_A.xlsx").relevant.isna().all():
            if single_annotator() is None: return machine_only()
    path = LAB / "adjudication.xlsx"
    if not path.exists():
        print("No adjudicated gold yet."); return machine_only()
    G = pd.read_excel(path, sheet_name="items", dtype=str).set_index("item_id")
    if G.relevant.isna().mean() > 0.02 or G.loc[G.relevant == "1", "tone"].isna().mean() > 0.02:
        print("Adjudication incomplete."); return machine_only()
    K = pd.read_csv(LAB / "_key_hidden.csv").set_index("item_id")
    A = pd.read_csv(PROC / "ai_codes.csv").set_index("item_id")
    D = G.join(K[["text", "src_grp", "w_cell", "dict_tone", "topic_kw"]]).join(A[["ai_tone", "finbert_tone", "ai_topic",
                "ai_price_frame", "ai_unit_frame", "ai_time_frame", "ai_attr_target", "ai_attr_direction", "ai_emotional", "ai_relevance_p"]])
    llm = PROC / "llm_codes.csv"
    if llm.exists():
        D = D.join(pd.read_csv(llm).set_index("item_id").add_prefix("llm_"))
    D = D[D.relevant == "1"]
    # conventional classifier: TF-IDF + LR, out-of-fold predictions on gold
    clf = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True), LogisticRegression(max_iter=2000, class_weight="balanced"))
    cv = StratifiedKFold(5, shuffle=True, random_state=0)
    D["tfidf_tone"] = cross_val_predict(clf, D.text, D.tone, cv=cv)
    D["tfidf_topic"] = np.nan if D.topic.isna().all() else cross_val_predict(clf, D.text, D.topic, cv=StratifiedKFold(3, shuffle=True, random_state=0)) if D.topic.value_counts().min() >= 3 else np.nan
    D["finbert_tone"] = D.finbert_tone.replace({"neutral": "neutral"})
    rows, reports = [], []
    tasks = {"tone": {"AI (NLI zero-shot)": "ai_tone", "FinBERT": "finbert_tone", "Dictionary": "dict_tone", "TF-IDF+LR (CV)": "tfidf_tone", "LLM": "llm_tone"},
             "topic": {"AI (NLI zero-shot)": "ai_topic", "Dictionary": "topic_kw", "TF-IDF+LR (CV)": "tfidf_topic", "LLM": "llm_topic"},
             "price_frame": {"AI (NLI zero-shot)": "ai_price_frame", "LLM": "llm_price_frame"},
             "unit_frame": {"AI (NLI zero-shot)": "ai_unit_frame", "LLM": "llm_unit_frame"},
             "time_frame": {"AI (NLI zero-shot)": "ai_time_frame", "LLM": "llm_time_frame"},
             "attr_target": {"AI (NLI zero-shot)": "ai_attr_target", "LLM": "llm_attr_target"}}
    for dim, coders in tasks.items():
        if dim not in D or D[dim].isna().all(): continue          # not human-labelled
        for name, col in coders.items():
            if col not in D or D[col].isna().all(): continue
            y, p = D[dim].fillna("not_relevant").astype(str), D[col].fillna("not_relevant").astype(str)
            rows.append({"dimension": dim, "coder": name, "n": len(y), "accuracy": (y == p).mean(),
                         "macro_F1": f1_score(y, p, average="macro"), "weighted_F1": f1_score(y, p, average="weighted"),
                         "kappa_vs_gold": cohen_kappa_score(y, p)})
            for g, sub in D.groupby("src_grp"):
                rows.append({"dimension": dim, "coder": name, "subset": g, "n": len(sub),
                             "accuracy": (sub[dim].fillna("not_relevant").astype(str) == sub[col].fillna("not_relevant").astype(str)).mean(),
                             "macro_F1": f1_score(sub[dim].fillna("not_relevant").astype(str), sub[col].fillna("not_relevant").astype(str), average="macro")})
            rep = pd.DataFrame(classification_report(y, p, output_dict=True, zero_division=0)).T
            rep["dimension"], rep["coder"] = dim, name; reports.append(rep)
            cm = pd.DataFrame(confusion_matrix(y, p, labels=sorted(set(y))), index=sorted(set(y)), columns=sorted(set(y)))
            cm.to_csv(TAB / f"confusion_{dim}_{col}.csv")
    pd.DataFrame(rows).to_csv(TAB / "ai_performance.csv", index=False)
    pd.concat(reports).to_csv(TAB / "ai_performance_by_class.csv")
    print(pd.DataFrame(rows).query("subset != subset").round(3).to_string())


def machine_only():
    """Consistency (NOT validity): agreement among machine coders on the full coded set."""
    A = pd.read_csv(PROC / "ai_codes.csv")
    C = pd.read_csv(PROC / "corpus.csv", usecols=["item_id", "topic_kw"])
    A = A.merge(C, on="item_id")
    A["finbert_tone"] = A.finbert_tone.astype(str)
    rows = [{"pair": "AI(NLI) vs Dictionary — tone", "agree": (A.ai_tone == A.dict_tone).mean(), "kappa": cohen_kappa_score(A.ai_tone, A.dict_tone)},
            {"pair": "AI(NLI) vs FinBERT — tone", "agree": (A.ai_tone == A.finbert_tone).mean(), "kappa": cohen_kappa_score(A.ai_tone, A.finbert_tone)},
            {"pair": "FinBERT vs Dictionary — tone", "agree": (A.finbert_tone == A.dict_tone).mean(), "kappa": cohen_kappa_score(A.finbert_tone, A.dict_tone)},
            {"pair": "AI(NLI) vs Dictionary — topic", "agree": (A.ai_topic == A.topic_kw).mean(), "kappa": cohen_kappa_score(A.ai_topic, A.topic_kw)}]
    R = pd.DataFrame(rows); R["n"] = len(A); R.to_csv(TAB / "machine_agreement.csv", index=False)
    print("MACHINE-MACHINE agreement (consistency only, not validation):"); print(R.round(3).to_string())


if __name__ == "__main__":
    agreement() if "--agreement" in sys.argv else evaluate()

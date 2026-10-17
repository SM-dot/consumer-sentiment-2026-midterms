"""
09_labeling_sample.py — Draw the stratified 300-item human-validation sample and write blind annotation workbooks.

Strata (fixed in advance): platform/source (news 200: split by outlet-lean group; Hacker News 50; Mastodon 50)
x period (2017–20, 2021–22, 2023–24, 2025–26) with OVERSAMPLING of AI-predicted positive items (rare class) so that
per-class F1 is estimable. Sampling weights are stored so population-level accuracy can be re-weighted.
Annotators never see AI or dictionary labels (they are kept in labeling/_key_hidden.csv).
"""
import numpy as np, pandas as pd
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, Alignment, PatternFill
from lib import load_corpus, ROOT, PROC

LAB = ROOT / "labeling"; LAB.mkdir(exist_ok=True)
rng = np.random.default_rng(20261016)
FIELDS = {"relevant": ["1", "0"], "tone": ["negative", "neutral", "positive"], "emotional": ["0", "1", "2"],
          "topic": ["prices_rising", "inflation_falling", "layoffs", "hiring", "growth", "recession_risk", "housing_rates",
                    "trade_tariffs", "markets", "policy_fed", "other"],
          "price_frame": ["level", "rate", "both", "none"], "unit_frame": ["aggregate", "household", "both", "none"],
          "time_frame": ["current", "forecast", "past", "none"],
          "attr_target": ["none", "president_admin", "congress", "fed", "business", "foreign", "other"],
          "attr_direction": ["none", "credit", "blame"]}


def period(d):
    y = d.year
    return "2017-20" if y <= 2020 else "2021-22" if y <= 2022 else "2023-24" if y <= 2024 else "2025-26"


def draw(C, A):
    D = C.merge(A, on="item_id")
    D = D[D.date.dt.year >= 2017].copy()
    D["period"] = D.date.map(period)
    D["lean_grp"] = D.outlet_lean.replace({"lean_left": "left", "lean_right": "right"})
    D["src_grp"] = np.where(D.platform == "news", "news_" + D.lean_grp.where(D.lean_grp.isin(["left", "right", "center"]), "other"),
                            np.where(D.source == "mastodon", "mastodon", "hn"))
    quota = {"news_left": 50, "news_right": 50, "news_center": 40, "news_other": 60, "hn": 50, "mastodon": 50}
    picks = []
    for g, q in quota.items():
        pool = D[D.src_grp == g]
        if pool.empty: continue
        per = pool.groupby("period")
        n_per = max(1, q // max(1, per.ngroups))
        for _, cell in per:
            pos = cell[cell.ai_tone == "positive"]; rest = cell[cell.ai_tone != "positive"]
            k_pos = min(len(pos), max(1, n_per // 3))                      # oversample positives (~1/3 of cell)
            s = pd.concat([pos.sample(k_pos, random_state=int(rng.integers(1e9))),
                           rest.sample(min(len(rest), n_per - k_pos), random_state=int(rng.integers(1e9)))])
            s = s.assign(w_cell=len(cell) / max(len(s), 1))
            picks.append(s)
    S = pd.concat(picks).drop_duplicates("item_id")
    if len(S) < 300:   # top up at random from unused items
        extra = D[~D.item_id.isin(S.item_id)].sample(300 - len(S), random_state=1).assign(w_cell=1.0)
        S = pd.concat([S, extra])
    return S.sample(300, random_state=2) if len(S) > 300 else S


def workbook(df, path, title):
    wb = Workbook(); ws = wb.active; ws.title = "items"
    hdr = ["row", "item_id", "date", "source", "text"] + list(FIELDS) + ["notes"]
    ws.append(hdr)
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1F4E79")
    for i, r in enumerate(df.itertuples(), 1):
        ws.append([i, r.item_id, str(r.date)[:10], r.source if r.platform == "news" else r.source.split(".")[0], r.text] + [""] * (len(FIELDS) + 1))
    ws.column_dimensions["E"].width = 90
    for col in "FGHIJKLMN": ws.column_dimensions[col].width = 16
    for row in ws.iter_rows(min_row=2, max_col=5):
        row[4].alignment = Alignment(wrap_text=True, vertical="top")
    for j, (f, opts) in enumerate(FIELDS.items()):
        col = chr(ord("F") + j)
        dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=True)
        ws.add_data_validation(dv); dv.add(f"{col}2:{col}{len(df)+1}")
    ws.freeze_panes = "F2"
    g = wb.create_sheet("guide"); g.append([title]); g.append(["Follow labeling/LABELING_GUIDE.md. Do not consult AI outputs or the other annotator."])
    wb.save(path)


def main():
    C = load_corpus()
    A = pd.read_csv(PROC / "ai_codes.csv")
    S = draw(C, A)
    practice = C.merge(A, on="item_id")
    practice = practice[~practice.item_id.isin(S.item_id) & (practice.date.dt.year >= 2017)].sample(20, random_state=5)
    S[["item_id", "date", "platform", "source", "source_tier", "outlet_lean", "src_grp", "period", "w_cell", "text",
       "ai_tone", "ai_topic", "finbert_tone", "dict_tone", "topic_kw"]].to_csv(LAB / "_key_hidden.csv", index=False)
    workbook(S.sample(frac=1, random_state=101), LAB / "annotator_A.xlsx", "Annotator A — 300 items")
    workbook(S.sample(frac=1, random_state=202), LAB / "annotator_B.xlsx", "Annotator B — 300 items")
    workbook(practice, LAB / "practice_20.xlsx", "Practice round (not scored)")
    print(S.groupby(["src_grp", "period"]).size().unstack(fill_value=0)); print(S.ai_tone.value_counts())


if __name__ == "__main__":
    main()

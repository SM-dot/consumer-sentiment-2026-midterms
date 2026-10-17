"""18_deck_data.py — Export the numbers the slide deck needs (presentation/deck_data.json)."""
import json
import numpy as np, pandas as pd
from lib import ROOT, TAB, PROC, load_panel

T = lambda f, **k: pd.read_csv(TAB / f, **k) if (TAB / f).exists() else pd.DataFrame()


def main():
    P = load_panel()
    g = T("gap_m1_ics.csv"); g["month"] = pd.PeriodIndex(g.month, freq="M"); g = g.set_index("month")
    q = g.loc["2015-01":]
    # quarterly averages keep the native line chart readable on a slide
    qa = q[["actual", "pred", "lo95", "hi95"]].groupby(q.index.asfreq("Q")).mean()
    dec = T("decomposition.csv", index_col=0); dh = T("decomposition_m1h2.csv", index_col=0); party = T("partisan_composition.csv")
    gs = T("gap_summary.csv").set_index("period"); age = T("decline_by_age.csv").set_index("group")
    hc = T("hardship_change_by_age.csv").set_index("measure"); comp = T("corpus_composition.csv")
    hr = T("horse_race.csv"); rp = T("news_recall_predictive.csv"); rg = T("news_recall_granger.csv"); sp = T("spending_forecast.csv")
    b1 = T("bias_B1_asymmetry.csv"); b3 = T("bias_B3_slant.csv", index_col=0); cal = T("calibration_summary.csv", index_col=0)
    act = dec.loc["ACTUAL change in ICS", "contribution_to_ICS"]; m1c = dec.loc["TOTAL predicted by U3+PCE+GDP", "contribution_to_ICS"]
    hh = dh.loc["TOTAL predicted", "contribution"] - m1c; pc = float(party.loc[party.R_share_drop_pp == 5, "implied_ICS_change"].iloc[0])
    resid = act - m1c - hh - (-6.6) - pc
    L = g.iloc[-1]
    data = {
        "latest": {"actual": round(L.actual, 1), "pred": round(L.pred, 1), "gap": round(L.gap, 1), "lo95": round(L.lo95, 1), "hi95": round(L.hi95, 1)},
        "gap2026": round(gs.loc["2026 (to Oct, pre-midterm)", "mean_gap"], 1), "gap_gfc": round(gs.loc["2008–2009 GFC", "mean_gap"], 1),
        "below_pi_2026": round(100 * gs.loc["2026 (to Oct, pre-midterm)", "share_below_95PI"]),
        "chart_gap": {"labels": [str(p) for p in qa.index], "actual": qa.actual.round(1).tolist(), "pred": qa.pred.round(1).tolist(),
                      "lo95": qa.lo95.round(1).tolist(), "hi95": qa.hi95.round(1).tolist()},
        "decomp": [["Headline data (U-3, PCE, GDP)", round(m1c, 1)], ["Household pressures & policy uncertainty", round(hh, 1)],
                   ["Survey mode: phone → web", -6.6], ["Partisan composition (illustrative)", round(pc, 1)], ["Unexplained residual", round(resid, 1)]],
        "actual_change": round(act, 1),
        "age": {"groups": list(age.index), "change": age.change.round(1).tolist(), "share": age["share_of_decline_%_CLS"].round(0).tolist()},
        "hard": {k: {gname: round(hc.loc[k, gname], 1) for gname in hc.columns} for k in ["rsn_worse_prices", "rsn_worse_lowincome", "hb_cant_afford", "news_unfav", "govt_poor"] if k in hc.index},
        "corpus_items": int(comp["items"].sum()) if len(comp) else 0,
        "corpus_sources": int(comp[comp.platform == "news"].sources.sum()) if len(comp) else 0,
    }
    if len(hr):
        h = hr.set_index(["target", "model"])
        data["horse"] = {"m2_p_ics": float(h.loc[("ics", "M2 + media"), "CW_p"]), "m2_p_gap": float(h.loc[("gap", "M2 + media"), "CW_p"]),
                         "rmse": {m: round(float(h.loc[("ics", m), "rmse"]), 2) for m in ["M1 econ only", "M2 + media", "M3b econ + controls (no media)", "M3 + media + controls"]}}
    if len(rp):
        r = rp.iloc[1]; data["recall"] = {"rmse_base": round(r.rmse_base, 1), "rmse_with": round(r.rmse_with_recall, 1),
                                          "gap_base": round(r.gap_2025_26_base, 1), "gap_with": round(r.gap_2025_26_with_recall, 1),
                                          "p_fwd": float(rg.iloc[0]["recall->sentiment_p"]), "p_rev": float(rg.iloc[0]["sentiment->recall_p"])}
    if len(sp):
        s = sp[sp.window == "2022–2026"].set_index("model")
        data["spend"] = {"labels": ["Macro only", "+ Sentiment", "+ Fundamentals-consistent sentiment", "+ Sentiment gap"],
                         "rmse": [round(float(s.loc[m, "rmse"]), 2) for m in ["S0 macro only", "S1 + ICS", "S2 + fundamentals-consistent ICS", "S3 + ICS gap"]]}
    if len(b1):
        t = b1.set_index("tone_measure").loc["tone_net"]; data["b1"] = {"good": round(t.b_good, 3), "bad": round(t.b_bad, 3), "p": round(t.p_equal, 3)}
    if len(b3) and "tone_num" in b3.index:
        data["b3"] = {"coef": round(b3.loc["tone_num", "slant_coef_right_x_DemPres"], 3), "p": round(b3.loc["tone_num", "p"], 3)}
    if len(cal):
        data["calib"] = {"n": int(cal.loc["ALL", "n"]), "share": round(100 * cal.loc["ALL", "calibrated"])}
    ta = T("transition_aggregate.csv"); did = T("transition_did.csv", index_col=0); ps = T("transition_party_sentiment.csv")
    if len(ta) and len(did):
        data["transition"] = {"admins": ["Trump-1", "Biden", "Trump-2"], "tone": ta["AI net tone"].round(2).tolist(), "ics": ta["Michigan ICS (mean)"].round(1).tolist(),
                              "price_share": (100 * ta["Share of headlines on rising prices"]).round(0).tolist(),
                              "right_swing": round(float(did.loc["Right outlets, Trump-2 vs Biden", "coef"]), 2),
                              "left_swing": round(float(did.loc["Left outlets, Trump-2 vs Biden", "coef"]), 2),
                              "party": ps.set_index("party")["sentiment_swing"].round(0).to_dict()}
    ex = T("experience_effects.csv"); yo = T("experience_young_vs_old.csv"); nec = T("necessities_vs_headline.csv")
    if len(ex) and len(yo):
        e = ex[ex.theta == 1.5].set_index("outcome")
        data["experience"] = {"exp_coef": round(float(e.loc["1-yr inflation expectation (median %)", "coef_per_pp_experienced"]), 2),
                              "ics_coef": round(float(e.loc["Sentiment (ICS, 3mma)", "coef_per_pp_experienced"]), 1),
                              "share": round(100 * float(yo.share_explained.iloc[0]))}
    if len(nec):
        n = nec.set_index("series")["Jan 2021 → Sep 2026 (%)"]
        data["nec"] = {"cpi": round(float(n.iloc[0])), "wages": round(float(n.iloc[4]))}
    rr = T("relevance_robustness.csv"); ms = T("media_sensitivity.csv"); ha = T("human_agreement.csv")
    if len(rr) and len(ms):
        slope = float(ms[(ms.measure == "tone_net") & (ms.timing == "t-1") & (ms["sample"] == "2017–2026")].coef.iloc[0])
        worst = float((rr.aggregate_tone_Trump2 - rr.aggregate_tone_Biden).min())
        data["left_broad"] = round(float(rr.left_outlets_T2_vs_Biden.iloc[1]), 2)
        data["magnitude"] = {"tone_change": round(worst, 3), "implied": round(abs(worst * slope), 1), "slope": round(slope)}
    if len(ha):
        data["retest"] = {"tone_agree": round(100 * float(ha.set_index("dimension").loc["tone", "pct_agree"]))}
    rg = T("decline_by_region.csv"); inc = T("decline_by_income.csv"); yo2 = T("experience_young_vs_old.csv")
    if len(rg):
        data["region"] = {"labels": rg.region.str.replace(" (Midwest)", "", regex=False).tolist(), "lost": rg.change.abs().round(1).tolist(),
                          "pct": rg["pct_change"].abs().round(0).tolist()}
    if len(inc):
        data["income"] = {"labels": inc.group.tolist(), "lost": inc.change.abs().round(1).tolist()}
    if len(nec):
        n2 = nec.set_index("series")["Jan 2021 → Sep 2026 (%)"]
        data["nec_full"] = {"labels": ["Headline CPI", "Groceries", "Shelter", "Gasoline", "Hourly wages"], "values": [round(float(v), 1) for v in n2.values]}
    if len(yo2):
        data["exp_rise"] = {"young": round(float(yo2.rise_in_experienced_inflation_18_34.iloc[0]), 2), "old": round(float(yo2.rise_55_plus.iloc[0]), 2),
                            "actual": round(float(yo2.actual_extra_decline_young_vs_old.iloc[0]), 1), "pred": round(float(yo2.predicted_by_experience.iloc[0]), 1)}
    data["levels"] = {}
    for key, f, col in [("age", "decline_by_age.csv", "group"), ("income", "decline_by_income.csv", "group"), ("region", "decline_by_region.csv", "region")]:
        t = T(f)
        if len(t):
            data["levels"][key] = {"labels": t[col].str.replace(" (Midwest)", "", regex=False).tolist(),
                                   "y2019": t.ICS_2019.round(0).tolist(), "now": t.ICS_2025_26.round(0).tolist()}
    a = T("decline_by_age.csv")
    if len(a):
        data["levels"]["age_weight"] = (100 * a.implied_weight_CLS).round(0).tolist()
    def clean(o):
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list): return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)): return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.integer): return int(o)
        return o
    data = clean(data)
    (ROOT / "presentation" / "deck_data.json").write_text(json.dumps(data, indent=1))
    print(json.dumps({k: v for k, v in data.items() if k != "chart_gap"}, indent=1, default=float)[:2500])


if __name__ == "__main__":
    main()

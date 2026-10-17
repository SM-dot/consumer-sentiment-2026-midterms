"""
10b_import_app_labels.py — Convert labels saved by the Headline Labeling Desk (artifact db, collection `labels`)
into labeling/annotator_A.xlsx / annotator_B.xlsx, the format 10_validation.py reads.

Export first (done by Claude via ArtifactData `list` with out_dir=labeling/app_export), then:
    python src/10b_import_app_labels.py
"""
import json, glob
import pandas as pd
from lib import ROOT

LAB = ROOT / "labeling"
DIMS = ["relevant", "tone", "emotional", "topic", "price_frame", "unit_frame", "time_frame", "attr_target", "attr_direction"]


def main():
    files = glob.glob(str(LAB / "app_export" / "**" / "*.json"), recursive=True)
    key = pd.read_csv(LAB / "_key_hidden.csv")[["item_id", "date", "source", "text"]]
    for f in files:
        d = json.load(open(f)); d = d.get("data", d)
        who = d.get("annotator") or "A"
        for part, fname in [("main", f"annotator_{who}.xlsx"), ("recheck", "recheck_A.xlsx")]:
            rows = []
            for item_id, lbl in (d.get(part) or {}).items():
                r = {"item_id": item_id, **{k: lbl.get(k) for k in DIMS}, "notes": lbl.get("notes", "")}
                if r["relevant"] == "0":
                    for k in DIMS[1:]: r[k] = None
                rows.append(r)
            if not rows: continue
            out = key.merge(pd.DataFrame(rows), on="item_id", how="inner" if part == "recheck" else "left")
            out.to_excel(LAB / fname, sheet_name="items", index=False)
            print(part, "labelled", out.relevant.notna().sum(), "of", len(out))


if __name__ == "__main__":
    main()

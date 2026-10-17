"""
07b_llm_code_api.py — OPTIONAL LLM coder (Claude) applying the same frozen codebook via prompts/llm_coding_prompt_v1.md.

Not run in the delivered analysis (no API credentials on the build machine). To run:
    pip install anthropic pydantic && export ANTHROPIC_API_KEY=...   (or `ant auth login`)
    python src/07b_llm_code_api.py --sample labeling          # the 300 validation items (~$1–2)
    python src/07b_llm_code_api.py --sample swap              # name-swap counterfactual pairs
Outputs data/processed/llm_codes.csv (picked up automatically by 10_validation.py) with model id, prompt hash, and
evidence excerpt per item. Reproducibility: Claude Opus 5.5 does not accept a temperature parameter, so we fix the
model id, the prompt (hash logged), low effort, and a strict JSON schema; re-runs may still differ slightly — report
the re-run agreement (run twice, compare) as a stability statistic.
"""
import argparse, hashlib, json, time
from typing import Literal
import pandas as pd
import anthropic
from pydantic import BaseModel
from lib import ROOT, PROC, TAB

MODEL = "claude-opus-5-5"
PROMPT = (ROOT / "prompts" / "llm_coding_prompt_v1.md").read_text()
PROMPT_HASH = hashlib.sha256(PROMPT.encode()).hexdigest()[:12]


class Codes(BaseModel):
    relevant: Literal[0, 1]
    tone: Literal["negative", "neutral", "positive"]
    emotional: Literal[0, 1, 2]
    topic: Literal["prices_rising", "inflation_falling", "layoffs", "hiring", "growth", "recession_risk",
                   "housing_rates", "trade_tariffs", "markets", "policy_fed", "other"]
    price_frame: Literal["level", "rate", "both", "none"]
    unit_frame: Literal["aggregate", "household", "both", "none"]
    time_frame: Literal["current", "forecast", "past", "none"]
    attr_target: Literal["none", "president_admin", "congress", "fed", "business", "foreign", "other"]
    attr_direction: Literal["none", "credit", "blame"]
    evidence: str


def code_one(client, text):
    r = client.messages.parse(
        model=MODEL, max_tokens=2000,
        system=[{"type": "text", "text": PROMPT, "cache_control": {"type": "ephemeral"}}],
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"ITEM:\n{text}"}],
        output_format=Codes,
    )
    if r.stop_reason == "refusal":
        return {"llm_status": "refusal"}
    return {"llm_status": "ok", **r.parsed_output.model_dump()}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sample", choices=["labeling", "swap"], default="labeling")
    a = ap.parse_args()
    client = anthropic.Anthropic()
    if a.sample == "labeling":
        items = pd.read_csv(ROOT / "labeling" / "_key_hidden.csv")[["item_id", "text"]]
    else:
        s = pd.read_csv(TAB / "swap_test_items.csv")
        items = pd.concat([s[["item_id", "orig"]].rename(columns={"orig": "text"}).assign(version="orig"),
                           s[["item_id", "swapped"]].rename(columns={"swapped": "text"}).assign(version="swapped")])
    rows = []
    for r in items.itertuples():
        try:
            out = code_one(client, r.text)
        except anthropic.RateLimitError:
            time.sleep(30); out = code_one(client, r.text)
        except anthropic.APIStatusError as e:
            out = {"llm_status": f"error_{e.status_code}"}
        rows.append({"item_id": r.item_id, "version": getattr(r, "version", "orig"), "model": MODEL,
                     "prompt_hash": PROMPT_HASH, **out})
    out = pd.DataFrame(rows)
    path = PROC / ("llm_codes.csv" if a.sample == "labeling" else "llm_swap_codes.csv")
    out.to_csv(path, index=False); print(out.llm_status.value_counts())


if __name__ == "__main__":
    main()

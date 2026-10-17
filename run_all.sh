#!/usr/bin/env bash
# Reproduce the full analysis. Fetch steps are cached: they only download what is missing.
# Usage: bash run_all.sh            (full refresh)
#        bash run_all.sh --no-fetch (rebuild from cached raw data only)
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip install -r requirements.txt; }

if [[ "${1:-}" != "--no-fetch" ]]; then
  echo "== fetch (cached, rate-limited)"
  $PY src/01b_fetch_gnews.py          # news headlines (Google News RSS)
  $PY src/02_fetch_social.py          # Hacker News + Mastodon
  $PY src/01_fetch_gdelt.py timelines # GDELT volume/tone (may be throttled; optional)
  # Macro sources (UMich, BLS, BEA, Philadelphia Fed, PMMS, EIA, FHFA, EPU): see docs/DATA_PROVENANCE.md for URLs;
  # re-download into data/raw/ before a refresh.
fi
cd src
echo "== economic baseline";      ../$PY 03_build_dataset.py
echo "== sentiment-gap models";   ../$PY 04_baseline_models.py
echo "== group heterogeneity";    ../$PY 05_heterogeneity.py
echo "== corpus";                 ../$PY 06_build_corpus.py
echo "== AI coding";              ../$PY 07_ai_code.py
echo "== swap test";              ../$PY 07_ai_code.py --swap
echo "== factual calibration";    ../$PY 08_factual_calibration.py
echo "== labeling sample";        [ -f ../labeling/annotator_A.xlsx ] || ../$PY 09_labeling_sample.py
echo "== validation";             [ -d ../labeling/app_export ] && ../$PY 10b_import_app_labels.py || true
                                  ../$PY 10_validation.py
                                  ../$PY 10c_reference_validation.py
echo "== media indices & bias";   ../$PY 11_media_indices.py
echo "== media models";           ../$PY 12_media_models.py
echo "== recall, components, spending"; ../$PY 16_news_heard_long.py; ../$PY 14_components.py; ../$PY 17_spending_implication.py
echo "== fresh angles (transition test, inflation memory)"; ../$PY 19_fresh_angles.py
echo "== experience effects and CPI necessities"; ../$PY 20_experience_cpi.py
echo "== relevance robustness"; ../$PY 21_relevance_robustness.py
echo "== region & seasonality"; ../$PY 22_region_seasonality.py
echo "== dashboard";              ../$PY 13_dashboard.py
echo "== report & deck";          ../$PY 15_build_report.py; ../$PY 18_deck_data.py
(cd ../presentation && { [ -d node_modules ] || npm install; } && NODE_PATH=$PWD/node_modules node build_deck.js)
echo "done -> dashboard/index.html, outputs/"

"""
13_dashboard.py — Build the updateable monitoring dashboard (dashboard/index.html, self-contained).

Run after any data refresh:  bash run_all.sh  (or: python src/13_dashboard.py)
Shows: sentiment vs real-time economic-model prediction with prediction intervals; the sentiment gap; media tone,
salience, framing and factual-calibration measures; Michigan news-heard (recall); sentiment by age/income;
economic releases & events; corpus composition, missingness and model-performance indicators.
"""
import json, datetime as dt
import numpy as np, pandas as pd
from lib import ROOT, PROC, TAB, load_panel

OUTD = ROOT / "dashboard"; OUTD.mkdir(exist_ok=True)
CUTOFF = "2026-10-16"; ELECTION = "2026-11-03"


def series(s, start="2015-01", nd=2):
    s = s.loc[start:] if s.index.dtype != object else s
    return [[str(k), None if pd.isna(v) else round(float(v), nd)] for k, v in s.items()]


def read(name, **kw):
    p = TAB / name
    return pd.read_csv(p, **kw) if p.exists() else pd.DataFrame()


def main():
    P = load_panel()
    g = read("gap_m1_ics.csv"); g["month"] = pd.PeriodIndex(g.month, freq="M"); g = g.set_index("month")
    gh = read("gap_m1h2_ics.csv")
    if len(gh): gh["month"] = pd.PeriodIndex(gh.month, freq="M"); gh = gh.set_index("month")
    M = pd.read_csv(PROC / "media_monthly.csv") if (PROC / "media_monthly.csv").exists() else pd.DataFrame()
    if len(M): M["month"] = pd.PeriodIndex(M.month, freq="M"); M = M.set_index("month")
    last = g.index.max(); L = g.loc[last]
    data = {
        "cutoff": CUTOFF, "election": ELECTION,
        "latest": {"month": str(last), "actual": round(L.actual, 1), "pred": round(L.pred, 1), "lo95": round(L.lo95, 1),
                   "hi95": round(L.hi95, 1), "gap": round(L.gap, 1), "z": round(L.z, 2),
                   "prev_actual": round(g.actual.iloc[-2], 1), "gap_mode_adj": round(L.gap_mode_adj, 1),
                   "pred_h2": round(gh.loc[last, "pred"], 1) if len(gh) and last in gh.index else None},
        "ics": series(g.actual, "2010-01", 1), "pred": series(g.pred, "2010-01", 1),
        "lo95": series(g.lo95, "2010-01", 1), "hi95": series(g.hi95, "2010-01", 1),
        "lo80": series(g.lo80, "2010-01", 1), "hi80": series(g.hi80, "2010-01", 1),
        "gap": series(g.gap, "2010-01", 1), "gap_adj": series(g.gap_mode_adj, "2010-01", 1),
        "pred_h2": series(gh.pred, "2010-01", 1) if len(gh) else [],
        "icc": series(P.icc, "2015-01", 1), "ice": series(P.ice, "2015-01", 1),
        "groups": {"18–34": series(P.ics_a1834.rolling(3).mean(), "2015-01", 1), "35–54": series(P.ics_a3554.rolling(3).mean(), "2015-01", 1),
                   "55+": series(P.ics_a5597.rolling(3).mean(), "2015-01", 1),
                   "Bottom third": series(P.ics_inc31.rolling(3).mean(), "2015-01", 1), "Middle third": series(P.ics_inc32.rolling(3).mean(), "2015-01", 1),
                   "Top third": series(P.ics_inc33.rolling(3).mean(), "2015-01", 1)},
        "news_heard": {"Heard unfavorable news (%)": series(P.news_u_all, "2015-01", 0), "Heard favorable news (%)": series(P.news_f_all, "2015-01", 0),
                       "Unfavorable: prices (%)": series(P.newsrn_u_pri_all, "2015-01", 0)},
        "hardship": {"Worse off because of higher prices (%)": series(P.pagorn_hp_all, "2015-01", 0)},
    }
    if len(M):
        sm = lambda c: series(M[c].rolling(3, min_periods=2).mean(), "2017-01", 3) if c in M else []
        data["tone"] = {"AI coder (NLI)": sm("tone_net"), "FinBERT": sm("tone_finbert"), "Dictionary": sm("tone_dict")}
        data["salience"] = {"Prices rising": sm("sal_prices_rising"), "Inflation falling": sm("sal_inflation_falling"),
                            "Layoffs + recession": sm("sal_labor_bad"), "Tariffs": sm("sal_trade_tariffs")}
        data["framing"] = {"Price-level frame (share of price items)": sm("level_frame_share"),
                           "Household frame": sm("household_frame_share"), "Emotional wording": sm("emotional_share")}
        data["items"] = series(M.n_items.fillna(0), "2017-01", 0) if "n_items" in M else []
        data["excess"] = sm("excess_negativity")
    cal = read("calibration_monthly.csv")
    if len(cal):
        cal["month"] = pd.PeriodIndex(cal.month, freq="M"); cal = cal.set_index("month").sort_index()
        data["calibration"] = series(cal.calibrated_share.rolling(6, min_periods=3).mean(), "2017-01", 3)
    tabs = {}
    for name, f in [("summary", "gap_summary.csv"), ("horse", "horse_race.csv"), ("composition", "corpus_composition.csv"),
                    ("calib", "calibration_summary.csv"), ("machine", "machine_agreement.csv"), ("decline_age", "decline_by_age.csv"),
                    ("decomp", "decomposition.csv"), ("agreement", "human_agreement.csv"), ("perf", "ai_performance.csv")]:
        t = read(f)
        tabs[name] = json.loads(t.round(3).to_json(orient="split")) if len(t) else None
    data["tables"] = tabs
    miss = read("corpus_missingness.csv")
    data["missing"] = json.loads(miss.to_json(orient="split")) if len(miss) else None
    data["events"] = EVENTS
    html = TEMPLATE.replace("/*__DATA__*/null", json.dumps(data, allow_nan=False, default=str).replace("NaN", "null"))
    (OUTD / "index.html").write_text(html)
    print("wrote", OUTD / "index.html", round(len(html) / 1024), "KB")


EVENTS = [
    {"date": "2024-04", "kind": "Method", "text": "Michigan begins phone→web transition (25% web; 100% web from July 2024). UMich estimates a 6.6-pt level effect."},
    {"date": "2025-01", "kind": "Politics", "text": "Presidential transition; partisan sentiment flips (Michigan: Democrats down, Republicans up)."},
    {"date": "2025-04", "kind": "Policy", "text": "Broad tariff announcements (early April 2025); sentiment falls to 52.2."},
    {"date": "2025-10", "kind": "Data", "text": "Federal shutdown (Oct 1 – Nov 12, 2025): no October 2025 household survey; BLS/BEA releases delayed."},
    {"date": "2026-05", "kind": "Survey", "text": "ICS 44.8 — lowest on record (also lowest in Michigan's parallel web series)."},
    {"date": "2026-09", "kind": "Data", "text": "BEA annual NIPA update (vintage 2026M10 revises GDP levels)."},
    {"date": "2026-10", "kind": "Survey", "text": "October preliminary ICS 46.3 (final due ~Oct 30)."},
    {"date": "2026-10", "kind": "Upcoming", "text": "Q3 2026 GDP advance estimate (late October). Not in the model's information set until published."},
    {"date": "2026-11", "kind": "Upcoming", "text": "Midterm election Nov 3. October jobs report (first Friday of Nov). November preliminary ICS (mid-Nov)."},
]

TEMPLATE = r"""<title>Midterm Sentiment Monitor</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;800&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a statistical-release desk — summary strip, then stacked evidence panels, two-up on wide screens. */
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#14171c; --ink2:#4a5260; --ink3:#7a8392; --rule:#dde1e7; --grid:#eceff3;
  --actual:#14171c; --model:#2a78d6; --band:#2a78d6; --neg:#c8433f; --pos:#1f8a5b; --s2:#eb6834; --s3:#1baf7a; --s4:#c98500;
  --chip:#eef1f5; --warn:#b26b00;
  --f-display:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif; --f-body:"Public Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#121417; --panel:#1a1d22; --ink:#eef0f3; --ink2:#b8bfca; --ink3:#8a93a1; --rule:#2c3138; --grid:#24282e;
  --actual:#eef0f3; --model:#5598e7; --band:#5598e7; --neg:#e66767; --pos:#3fb27f; --s2:#d95926; --s3:#199e70; --s4:#e0a12a; --chip:#232830; --warn:#e0a12a; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#121417; --panel:#1a1d22; --ink:#eef0f3; --ink2:#b8bfca; --ink3:#8a93a1; --rule:#2c3138; --grid:#24282e;
  --actual:#eef0f3; --model:#5598e7; --band:#5598e7; --neg:#e66767; --pos:#3fb27f; --s2:#d95926; --s3:#199e70; --s4:#e0a12a; --chip:#232830; --warn:#e0a12a; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:14px;line-height:1.5;margin:0}
.wrap{max-width:1240px;margin:0 auto;padding-block:28px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:20px}
header{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:end;gap:12px;border-bottom:2px solid var(--ink);padding-bottom:14px}
h1{font-family:var(--f-display);font-weight:800;font-size:clamp(24px,3.2vw,34px);letter-spacing:-.01em;margin:0;text-wrap:balance}
.meta{font-family:var(--f-mono);font-size:12px;color:var(--ink2);display:flex;flex-wrap:wrap;gap:6px 14px}
.meta b{color:var(--ink);font-weight:500}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.kpi{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px 16px;display:grid;gap:4px;align-content:start}
.kpi .lab{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);font-weight:600}
.kpi .val{font-family:var(--f-mono);font-size:28px;font-weight:500;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:12.5px;color:var(--ink2)}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;padding:2px 8px;border-radius:999px;background:var(--chip);color:var(--ink);width:max-content}
.pill i{width:8px;height:8px;border-radius:50%;display:inline-block}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:20px}
section.panel{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:16px 18px;min-width:0;display:grid;gap:10px;align-content:start}
section h2{font-size:15px;font-weight:700;margin:0;text-wrap:balance}
section .note{font-size:12.5px;color:var(--ink2);max-width:75ch;margin:0}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--ink2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:14px;height:3px;border-radius:2px;display:inline-block}
.chart{position:relative;width:100%}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
.axis text{fill:var(--ink3);font-family:var(--f-mono);font-size:10.5px}
.tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:6px 8px;font-size:12px;box-shadow:0 2px 8px rgba(0,0,0,.12);white-space:nowrap;font-family:var(--f-mono)}
.tip b{font-family:var(--f-body)}
.tbl{overflow-x:auto}
table{border-collapse:collapse;font-size:12.5px;width:100%}
th,td{padding:5px 8px;border-bottom:1px solid var(--rule);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
th{font-weight:600;color:var(--ink2);font-size:11.5px}
th:first-child,td:first-child{text-align:left;white-space:normal}
.events{display:grid;gap:0}
.ev{display:grid;grid-template-columns:76px 86px 1fr;gap:10px;padding:7px 0;border-bottom:1px solid var(--rule);font-size:13px}
.ev .d{font-family:var(--f-mono);color:var(--ink2)}
.ev .k{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--ink2)}
.ev.up .k{color:var(--warn)}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tabs button{font:inherit;font-size:12px;border:1px solid var(--rule);background:var(--panel);color:var(--ink);padding:3px 10px;border-radius:999px;cursor:pointer}
.tabs button[aria-pressed="true"]{background:var(--ink);color:var(--panel);border-color:var(--ink)}
.tabs button:focus-visible{outline:2px solid var(--model);outline-offset:2px}
footer{font-size:12.5px;color:var(--ink2);border-top:1px solid var(--rule);padding-top:12px;display:grid;gap:6px}
@media (max-width:560px){.ev{grid-template-columns:64px 1fr}.ev .k{grid-column:2}.ev .t{grid-column:1/-1}}
</style>

<div class="wrap">
<header>
  <div><h1>Midterm Sentiment Monitor</h1>
  <div class="note" style="color:var(--ink2)">University of Michigan consumer sentiment against what real-time U-3, PCE inflation and GDP predict, with media measures</div></div>
  <div class="meta" id="meta"></div>
</header>
<div class="kpis" id="kpis"></div>

<section class="panel">
  <h2>Sentiment vs. the economic-model prediction</h2>
  <p class="note">Out-of-sample, real-time forecasts: each month's prediction uses only data published before that survey and a model fit on prior months (1978 onward). Shaded: 80% and 95% prediction intervals. A negative gap is unexplained pessimism <em>under this model</em>, not proof of bias.</p>
  <div class="tabs" role="group" aria-label="Model"><button id="t-m1" aria-pressed="true">U-3 + PCE + GDP</button><button id="t-h2" aria-pressed="false">+ household pressures &amp; policy uncertainty</button></div>
  <div class="legend" id="lg-main"></div>
  <div class="chart" id="c-main"></div>
  <h2 style="margin-top:6px">Sentiment gap (actual − prediction)</h2>
  <div class="legend" id="lg-gap"></div>
  <div class="chart" id="c-gap"></div>
</section>

<div class="grid2">
  <section class="panel"><h2>Media tone in economic headlines</h2><p class="note">Net tone (share positive − share negative) of AI-coded US news headlines, 3-month average. Three coders on identical items.</p><div class="legend" id="lg-tone"></div><div class="chart" id="c-tone"></div></section>
  <section class="panel"><h2>Salience: what the coverage is about</h2><p class="note">Share of coded economic headlines by main topic (supply of content, not exposure).</p><div class="legend" id="lg-sal"></div><div class="chart" id="c-sal"></div></section>
  <section class="panel"><h2>Framing and factual calibration</h2><p class="note">Price-level framing ("prices are high") vs inflation-rate framing; household vs aggregate framing; loaded wording. Dashed: share of numeric claims matching official data public on that date (6-month average).</p><div class="legend" id="lg-frm"></div><div class="chart" id="c-frm"></div></section>
  <section class="panel"><h2>What respondents say they heard</h2><p class="note">Michigan Tables 23–24: recall of economic news, asked of the same respondents (recall, not verified exposure).</p><div class="legend" id="lg-heard"></div><div class="chart" id="c-heard"></div></section>
  <section class="panel"><h2>Sentiment by age</h2><p class="note">Monthly sub-indices, 3-month average. The decline is broad-based across groups.</p><div class="legend" id="lg-age"></div><div class="chart" id="c-age"></div></section>
  <section class="panel"><h2>Sentiment by income tercile</h2><p class="note">Monthly sub-indices, 3-month average.</p><div class="legend" id="lg-inc"></div><div class="chart" id="c-inc"></div></section>
</div>

<div class="grid2">
  <section class="panel"><h2>Releases and events</h2><div class="events" id="events"></div></section>
  <section class="panel"><h2>Model performance</h2><p class="note">Expanding-window out-of-sample comparison, 2020 onward. Clark–West p &lt; 0.05 means the larger model adds predictive information.</p><div class="tbl" id="tb-horse"></div>
  <h2>Gap by period</h2><div class="tbl" id="tb-sum"></div></section>
</div>

<div class="grid2">
  <section class="panel"><h2>Source composition</h2><div class="tbl" id="tb-comp"></div></section>
  <section class="panel"><h2>Coverage per month and AI validation status</h2><p class="note">Relevant, non-duplicate items per month entering the media indices. Gaps signal missingness.</p><div class="legend" id="lg-items"></div><div class="chart" id="c-items"></div><div id="valid"></div></section>
</div>

<footer>
  <div><b>Update plan.</b> Re-run <code>bash run_all.sh</code> after each Michigan release (preliminary ~2nd Friday, final ~last Friday), each BLS Employment Situation and CPI release, each BEA GDP/PCE release, and weekly for media. The next scheduled refreshes before and after the election: Q3 GDP advance (late Oct), Michigan October final (~Oct 30), Election Day (Nov 3), November preliminary (mid-Nov).</div>
  <div>Election-proximity caution: changes during the campaign are not attributed to the election without a design that isolates it.</div>
</footer>
</div>

<script>
const D=/*__DATA__*/null;
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const fmt=(v,d=1)=>v==null?"–":(+v).toFixed(d);
const toDate=s=>{const [y,m]=s.split("-").map(Number);return y+(m-1)/12};
const monthName=s=>{const [y,m]=s.split("-");return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+m-1]+" "+y};

function meta(){
  const days=Math.round((new Date(D.election)-new Date(D.cutoff))/864e5);
  document.getElementById("meta").innerHTML=`<span>Data through <b>${D.cutoff}</b></span><span>October ICS <b>preliminary</b></span><span>Election <b>${D.election}</b> · ${days} days after cut-off</span>`;
  const L=D.latest, dz=L.z;
  const sev=dz<-3?["var(--neg)","Far below 95% interval"]:dz<-1.96?["var(--neg)","Below 95% interval"]:["var(--pos)","Within interval"];
  document.getElementById("kpis").innerHTML=`
   <div class="kpi"><div class="lab">Consumer sentiment, ${monthName(L.month)}</div><div class="val">${fmt(L.actual)}</div><div class="sub">Previous month ${fmt(L.prev_actual)} · 1966=100</div></div>
   <div class="kpi"><div class="lab">Predicted from U-3, PCE, GDP</div><div class="val">${fmt(L.pred)}</div><div class="sub">95% interval ${fmt(L.lo95)} – ${fmt(L.hi95)}${L.pred_h2!=null?` · with household controls ${fmt(L.pred_h2)}`:""}</div></div>
   <div class="kpi"><div class="lab">Sentiment gap</div><div class="val" style="color:${sev[0]}">${fmt(L.gap)}</div><div class="sub"><span class="pill"><i style="background:${sev[0]}"></i>${sev[1]} (z = ${fmt(dz,1)})</span></div><div class="sub">After adding back the web-mode effect: ${fmt(L.gap_mode_adj)}</div></div>
   <div class="kpi"><div class="lab">What the gap is not</div><div class="sub">Not proof of media bias or irrational pessimism. See the household-pressure model, the partisan and survey-mode notes, and the media tests in the report.</div></div>`;
}

function lineChart(el, layers, opt={}){
  const host=document.getElementById(el); host.innerHTML="";
  const W=Math.max(300,Math.round(host.getBoundingClientRect().width)||900), H=opt.h||(W<600?220:260), m={l:44,r:14,t:10,b:24};
  const all=layers.flatMap(l=>(l.band? l.lo.concat(l.hi):l.data)).filter(d=>d[1]!=null);
  if(!all.length){host.innerHTML='<p class="note">No data yet.</p>';return}
  let x0=Math.min(...all.map(d=>toDate(d[0]))), x1=Math.max(...all.map(d=>toDate(d[0])));
  let y0=opt.y0!=null?opt.y0:Math.min(...all.map(d=>d[1])), y1=opt.y1!=null?opt.y1:Math.max(...all.map(d=>d[1]));
  const pad=(y1-y0)*.06||1; if(opt.y0==null)y0-=pad; if(opt.y1==null)y1+=pad;
  const X=v=>m.l+(v-x0)/(x1-x0)*(W-m.l-m.r), Y=v=>m.t+(1-(v-y0)/(y1-y0))*(H-m.t-m.b);
  const ns="http://www.w3.org/2000/svg"; const svg=document.createElementNS(ns,"svg"); svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
  const ticks=(a,b,n)=>{const st=Math.pow(10,Math.floor(Math.log10((b-a)/n)));const c=[1,2,2.5,5,10].map(k=>k*st).find(k=>(b-a)/k<=n)||st*10;const out=[];for(let v=Math.ceil(a/c)*c;v<=b+1e-9;v+=c)out.push(+v.toFixed(6));return out};
  let g='<g class="axis">';
  for(const t of ticks(y0,y1,5)){g+=`<line x1="${m.l}" x2="${W-m.r}" y1="${Y(t)}" y2="${Y(t)}" stroke="${css('--grid')}"/><text x="${m.l-6}" y="${Y(t)+3.5}" text-anchor="end">${opt.pct?Math.round(t*100)+"%":t}</text>`}
  for(let yr=Math.ceil(x0);yr<=x1;yr+=(x1-x0>8?2:1)){g+=`<text x="${X(yr)}" y="${H-6}" text-anchor="middle">${yr}</text>`}
  if(opt.zero)g+=`<line x1="${m.l}" x2="${W-m.r}" y1="${Y(0)}" y2="${Y(0)}" stroke="${css('--ink3')}"/>`;
  g+='</g>';
  for(const l of layers){
    if(l.band){const pts=l.hi.filter(d=>d[1]!=null).map(d=>`${X(toDate(d[0]))},${Y(d[1])}`).concat(l.lo.filter(d=>d[1]!=null).reverse().map(d=>`${X(toDate(d[0]))},${Y(d[1])}`));
      g+=`<polygon points="${pts.join(" ")}" fill="${css(l.color)}" fill-opacity="${l.op||.15}" stroke="none"/>`;continue}
    if(l.bars){const bw=Math.max(1.5,(W-m.l-m.r)/l.data.length-1.2);
      for(const d of l.data){if(d[1]==null)continue;const x=X(toDate(d[0]))-bw/2,y=Y(Math.max(0,d[1])),h=Math.abs(Y(d[1])-Y(0));g+=`<rect x="${x}" y="${y}" width="${bw}" height="${Math.max(.5,h)}" fill="${css(d[1]<0?'--neg':'--pos')}" rx="1"/>`}continue}
    let path="",pen=false;for(const d of l.data){if(d[1]==null){pen=false;continue}path+=(pen?"L":"M")+X(toDate(d[0])).toFixed(1)+","+Y(d[1]).toFixed(1);pen=true}
    g+=`<path d="${path}" fill="none" stroke="${css(l.color)}" stroke-width="${l.w||2}" ${l.dash?`stroke-dasharray="${l.dash}"`:""} stroke-linejoin="round"/>`;
  }
  g+=`<line id="${el}-x" y1="${m.t}" y2="${H-m.b}" stroke="${css('--ink3')}" stroke-width="1" visibility="hidden"/>`;
  svg.innerHTML=g; host.appendChild(svg);
  const tip=document.createElement("div");tip.className="tip";tip.hidden=true;host.appendChild(tip);
  const named=layers.filter(l=>l.name&&!l.band);
  const months=[...new Set(named.flatMap(l=>l.data.map(d=>d[0])))].sort();
  svg.addEventListener("pointermove",ev=>{const r=svg.getBoundingClientRect();const vx=(ev.clientX-r.left)/r.width*W;
    let best=months[0],bd=1e9;for(const mo of months){const dd=Math.abs(X(toDate(mo))-vx);if(dd<bd){bd=dd;best=mo}}
    const xl=svg.querySelector(`#${el}-x`);xl.setAttribute("x1",X(toDate(best)));xl.setAttribute("x2",X(toDate(best)));xl.setAttribute("visibility","visible");
    let h=`<b>${monthName(best)}</b>`;for(const l of named){const d=l.data.find(z=>z[0]===best);if(d&&d[1]!=null)h+=`<br><span style="color:${css(l.color)}">■</span> ${l.name}: ${opt.pct?(d[1]*100).toFixed(1)+"%":fmt(d[1],opt.dp??1)}`}
    tip.innerHTML=h;tip.hidden=false;const px=(ev.clientX-r.left);tip.style.left=Math.min(px+12,r.width-tip.offsetWidth-4)+"px";tip.style.top="8px"});
  svg.addEventListener("pointerleave",()=>{tip.hidden=true;svg.querySelector(`#${el}-x`).setAttribute("visibility","hidden")});
}
function legend(el,items){document.getElementById(el).innerHTML=items.map(([n,c,dash])=>`<span><i style="background:${dash?`repeating-linear-gradient(90deg,var(${c}) 0 4px,transparent 4px 7px)`:`var(${c})`}"></i>${n}</span>`).join("")}

let mode="m1";
function drawMain(){
  const L=[{band:1,lo:D.lo95,hi:D.hi95,color:"--band",op:.12},{band:1,lo:D.lo80,hi:D.hi80,color:"--band",op:.14},
           {data:D.pred,color:"--model",name:"Predicted (U-3+PCE+GDP)"},{data:D.ics,color:"--actual",name:"Actual ICS",w:2.2}];
  if(mode==="h2"&&D.pred_h2.length)L.push({data:D.pred_h2,color:"--s2",name:"Predicted (+ household & policy)",dash:"5 3"});
  lineChart("c-main",L,{h:300});
  legend("lg-main",[["Actual ICS","--actual"],["Predicted: U-3 + PCE + GDP","--model"]].concat(mode==="h2"?[["Predicted: + household pressures & policy uncertainty","--s2",1]]:[]));
}
function tbl(el,t,cols,rename={},dp={}){const host=document.getElementById(el);if(!t){host.innerHTML='<p class="note">Not yet computed.</p>';return}
  const idx=cols.map(c=>t.columns.indexOf(c)).filter(i=>i>=0);
  const pctCols=new Set(["share_below_95PI"]);
  host.innerHTML=`<table><thead><tr>${idx.map(i=>`<th>${rename[t.columns[i]]||t.columns[i]}</th>`).join("")}</tr></thead><tbody>${t.data.map(r=>`<tr>${idx.map(i=>{const v=r[i],c=t.columns[i];return `<td>${typeof v==="number"?(pctCols.has(c)?Math.round(v*100)+"%":Number.isInteger(v)?v.toLocaleString():fmt(v,dp[c]??2)):(v??"–")}</td>`}).join("")}</tr>`).join("")}</tbody></table>`}

function render(){
  meta(); drawMain();
  lineChart("c-gap",[{data:D.gap,bars:1},{data:D.gap,name:"Gap",color:"--neg",w:0},{data:D.gap_adj,color:"--ink2",name:"Gap after adding back web-mode effect",w:1.2}],{h:160,zero:1});
  legend("lg-gap",[["Negative gap (more pessimistic than predicted)","--neg"],["Positive gap","--pos"],["After adding back UMich's 6.6-pt web-mode effect","--ink2"]]);
  if(D.tone){lineChart("c-tone",[{data:D.tone["AI coder (NLI)"],color:"--model",name:"AI coder"},{data:D.tone["FinBERT"],color:"--s2",name:"FinBERT"},{data:D.tone["Dictionary"],color:"--s3",name:"Dictionary"}],{zero:1,dp:2});
    legend("lg-tone",[["AI coder (zero-shot NLI)","--model"],["FinBERT","--s2"],["Dictionary baseline","--s3"]]);
    const S=D.salience;lineChart("c-sal",[{data:S["Prices rising"],color:"--neg",name:"Prices rising"},{data:S["Inflation falling"],color:"--pos",name:"Inflation falling"},{data:S["Layoffs + recession"],color:"--model",name:"Layoffs + recession"},{data:S["Tariffs"],color:"--s4",name:"Tariffs"}],{pct:1,y0:0});
    legend("lg-sal",[["Prices rising","--neg"],["Inflation falling","--pos"],["Layoffs + recession","--model"],["Tariffs","--s4"]]);
    const F=D.framing;const fl=[{data:F["Price-level frame (share of price items)"],color:"--s2",name:"Price-level frame"},{data:F["Household frame"],color:"--model",name:"Household frame"},{data:F["Emotional wording"],color:"--s3",name:"Emotional wording"}];
    if(D.calibration)fl.push({data:D.calibration,color:"--ink2",name:"Factually calibrated",dash:"4 3"});
    lineChart("c-frm",fl,{pct:1,y0:0,y1:1});legend("lg-frm",[["Price-level frame","--s2"],["Household frame","--model"],["Emotional wording","--s3"]].concat(D.calibration?[["Claims calibrated to official data","--ink2",1]]:[]));
    lineChart("c-items",[{data:D.items,color:"--model",name:"Coded items"}],{h:140,y0:0,dp:0});legend("lg-items",[["Coded items per month","--model"]]);}
  const H=D.news_heard;lineChart("c-heard",[{data:H["Heard unfavorable news (%)"],color:"--neg",name:"Unfavorable"},{data:H["Heard favorable news (%)"],color:"--pos",name:"Favorable"},{data:H["Unfavorable: prices (%)"],color:"--s2",name:"Unfavorable: prices"}],{y0:0,dp:0});
  legend("lg-heard",[["Heard unfavorable news","--neg"],["Heard favorable news","--pos"],["Unfavorable news about prices","--s2"]]);
  const G=D.groups;lineChart("c-age",[{data:G["18–34"],color:"--model",name:"18–34"},{data:G["35–54"],color:"--s2",name:"35–54"},{data:G["55+"],color:"--s3",name:"55+"}],{});
  legend("lg-age",[["18–34","--model"],["35–54","--s2"],["55+","--s3"]]);
  lineChart("c-inc",[{data:G["Bottom third"],color:"--model",name:"Bottom third"},{data:G["Middle third"],color:"--s2",name:"Middle third"},{data:G["Top third"],color:"--s3",name:"Top third"}],{});
  legend("lg-inc",[["Bottom third","--model"],["Middle third","--s2"],["Top third","--s3"]]);
  document.getElementById("events").innerHTML=D.events.map(e=>`<div class="ev ${e.kind==="Upcoming"?"up":""}"><span class="d">${e.date}</span><span class="k">${e.kind}</span><span class="t">${e.text}</span></div>`).join("");
  tbl("tb-horse",D.tables.horse,["target","model","n_oos","rmse","CW_p"],{target:"Target",model:"Model",n_oos:"N",rmse:"RMSE",CW_p:"CW p"});
  tbl("tb-sum",D.tables.summary,["period","months","mean_actual","mean_pred","mean_gap","mean_gap_mode_adj","share_below_95PI"],{period:"Period",months:"N",mean_actual:"Actual",mean_pred:"Predicted",mean_gap:"Gap",mean_gap_mode_adj:"Gap (mode-adj.)",share_below_95PI:"Share < 95% PI"},{mean_actual:1,mean_pred:1,mean_gap:1,mean_gap_mode_adj:1});
  tbl("tb-comp",D.tables.composition,["platform","unit","source_tier","items","relevant","duplicates","bot","sources"],{platform:"Platform",unit:"Unit",source_tier:"Tier",items:"Items",relevant:"Relevant",duplicates:"Dupes",bot:"Bot-flagged",sources:"Sources"},{items:0,relevant:0,duplicates:0,bot:0,sources:0});
  const v=document.getElementById("valid");
  const perf=D.tables.perf;let ai=null;if(perf){const ci=perf.columns.indexOf("coder"),di=perf.columns.indexOf("dimension"),si=perf.columns.indexOf("subset"),ai_=perf.columns.indexOf("accuracy"),ki=perf.columns.indexOf("kappa_vs_gold");
    const r=perf.data.find(x=>x[ci]==="AI (NLI zero-shot)"&&x[di]==="tone"&&x[si]==null);if(r)ai=[r[ai_],r[ki]]}
  v.innerHTML=ai?`<p class="note"><span class="pill"><i style="background:var(--pos)"></i>Validated</span> AI tone coder vs 300 human labels: ${Math.round(ai[0]*100)}% accurate, κ = ${ai[1].toFixed(2)} (one annotator; test–retest on the 30 hardest items in report Table 6a).</p>`:'<p class="note"><span class="pill"><i style="background:var(--warn)"></i>Partial</span> One human annotator (test–retest design) is labelling 300 items; a clearly marked LLM reference set covers all 300 meanwhile. See report Tables 7b–7c.</p>';
}
document.getElementById("t-m1").onclick=()=>{mode="m1";document.getElementById("t-m1").setAttribute("aria-pressed","true");document.getElementById("t-h2").setAttribute("aria-pressed","false");drawMain()};
document.getElementById("t-h2").onclick=()=>{mode="h2";document.getElementById("t-h2").setAttribute("aria-pressed","true");document.getElementById("t-m1").setAttribute("aria-pressed","false");drawMain()};
render();
let rz;addEventListener("resize",()=>{clearTimeout(rz);rz=setTimeout(render,150)});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",render);
new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});
</script>
"""

if __name__ == "__main__":
    main()

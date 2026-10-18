// build_deck.js — 12-slide plain-language narrative deck (~7.5 min). Numbers from deck_data.json (src/18_deck_data.py).
// Each slide: title = the claim in plain words; one chart labelled in everyday terms; a dark "what this means" bar.
// Usage: NODE_PATH=$PWD/node_modules node build_deck.js
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const SKILL = "/Users/syonamehra/.claude/skills/synced/e183f3b8-97e6-437c-86ea-ec53bc9110b6_d12b188e-c4b1-4aad-9b93-1850c0d747db/pptx";
const { applyTheme } = require(path.join(SKILL, "scripts/apply_theme.js"));
const D = JSON.parse(fs.readFileSync(path.join(__dirname, "deck_data.json"), "utf8"));

const THEME = {
  name: "Sentiment Gap", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B1F27", lt1: "FFFFFF", dk2: "3A4150", lt2: "F2F4F7", accent1: "C8433F", accent2: "2A78D6",
            accent3: "1F8A5B", accent4: "D99A1E", accent5: "7A8392", accent6: "6A5ACD", hlink: "2A78D6", folHlink: "6A5ACD" },
};
const HEX = THEME.colors;
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Why do Americans feel this bad about the economy?";
pres.author = "AI Applications in Finance — Final Project";
const C = pres.SchemeColor;

pres.defineSlideMaster({
  title: "TITLE_DARK", background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.9, w: 11.7, h: 2.0, fontFace: THEME.headFontFace, fontSize: 44, bold: true, color: C.background1, valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.1, w: 11.7, h: 1.8, fontFace: THEME.bodyFontFace, fontSize: 18, color: "CBD2DC", valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: HEX.lt1 }, margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontFace: THEME.headFontFace, fontSize: 30, bold: true, color: C.text1, valign: "top" }, text: "" } },
    { text: { text: "Data: University of Michigan consumer survey, BLS, BEA, Philadelphia Fed; 247k news headlines & posts. Data up to 16 Oct 2026 (election 3 Nov 2026).", options: { x: 0.6, y: 7.0, w: 10.5, h: 0.3, fontSize: 9, color: "7A8392", fontFace: THEME.bodyFontFace } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 9, color: "7A8392" },
});

const card = (s, x, y, w, h, fill) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || HEX.lt2 }, line: { color: fill || HEX.lt2 } });
const txt = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, margin: 0, fontFace: THEME.bodyFontFace, color: C.text1, valign: "top" }, o));
const axis = () => ({ catAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt", valAxisHidden: true,
  valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false,
  dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt", showValue: true, dataLabelPosition: "outEnd" });
const legendOn = () => ({ showLegend: true, legendPos: "b", legendFontSize: 11, legendFontFace: "+mn-lt", legendColor: HEX.dk2 });
const chartTitle = t => ({ showTitle: true, title: t, titleFontSize: 12, titleColor: HEX.dk2, titleFontFace: "+mn-lt" });
const bullets = (s, items, o) => txt(s, items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 7 } })), Object.assign({ fontSize: 14, color: HEX.dk1 }, o));
const means = (s, t) => { card(s, 0.6, 6.25, 12.1, 0.6, HEX.dk1); txt(s, [{ text: "What this means:  ", options: { bold: true, color: "F2B8B5" } }, { text: t, options: { bold: true, color: "FFFFFF" } }], { x: 0.85, y: 6.33, w: 11.6, h: 0.45, fontSize: 15, valign: "middle" }); };
const stat = (s, x, y, w, big, small, col) => { card(s, x, y, w, 1.35); txt(s, big, { x: x + 0.25, y: y + 0.1, w: w - 0.5, h: 0.65, fontSize: 32, bold: true, color: col || HEX.dk1, fontFace: THEME.headFontFace }); txt(s, small, { x: x + 0.25, y: y + 0.78, w: w - 0.5, h: 0.52, fontSize: 12, color: HEX.dk2 }); };
const pct = (a, b) => Math.round(100 * (b / a - 1));
const L = D.levels;

// ================================================================ 1. TITLE
pres.addSection({ title: "Question" });
let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Question" });
s.addText("Americans feel worse than the economy says they should. Why?", { placeholder: "title" });
s.addText([
  { text: "Short answer: not media bias. High prices, how the survey is done, and what people lived through.", options: { breakLine: true, bold: true, color: "FFFFFF" } },
  { text: "Consumer sentiment before the 2026 midterm elections · AI Applications in Finance · Final project", options: { fontSize: 14 } },
], { placeholder: "body" });
s.addNotes("(20 s) Three weeks before the midterms, Americans feel worse about the economy than almost ever. We asked why — and whether the media is to blame. Short answer: it isn't. High prices, a change in how the survey is done, and what people have lived through explain most of it.");

// ================================================================ 2. THE PUZZLE
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Question" });
s.addText("On paper the economy is fine. People feel terrible.", { placeholder: "title" });
const E = D.econ_now;
[[`${E.u3}%`, "Unemployment", `Low — the 1978–2019 average was ${E.u3_avg}%`],
 [`+${E.gdp}%`, "Economic growth (GDP, yearly pace)", "Normal, healthy growth — no recession"],
 [`${E.pce}%`, "Inflation (PCE, latest)", `Above the 2% goal, but far below the ${E.pce_2022_peak}% peak of 2022`]].forEach(([big, lab, sub], i) => {
  const x = 0.6 + i * 4.1; card(s, x, 1.35, 3.85, 1.25, "EAF2FC");
  txt(s, big, { x: x + 0.25, y: 1.42, w: 1.6, h: 0.65, fontSize: 30, bold: true, color: HEX.accent2, fontFace: THEME.headFontFace });
  txt(s, lab, { x: x + 1.85, y: 1.48, w: 1.9, h: 0.55, fontSize: 13, bold: true });
  txt(s, sub, { x: x + 0.25, y: 2.08, w: 3.4, h: 0.45, fontSize: 11.5, color: HEX.dk2 });
});
s.addChart(pres.charts.LINE, [
  { name: "How people actually feel", labels: D.chart_gap.labels, values: D.chart_gap.actual },
  { name: "How they 'should' feel, given jobs, inflation and growth", labels: D.chart_gap.labels, values: D.chart_gap.pred },
], { x: 0.6, y: 2.75, w: 8.2, h: 3.4, chartColors: [HEX.dk1, HEX.accent2], lineSize: 2.5, lineDataSymbol: "none", ...legendOn(),
     catAxisLabelColor: "7A8392", valAxisLabelColor: "7A8392", catAxisLabelFontSize: 9, valAxisLabelFontSize: 9, catAxisLabelFontFace: "+mn-lt",
     valAxisLabelFontFace: "+mn-lt", catAxisLabelFrequency: 4, valAxisMinVal: 30, valAxisMaxVal: 110, valGridLine: { color: "E6E9EE", size: 0.5 },
     catGridLine: { style: "none" }, ...chartTitle("Sentiment score, 2015–2026 (100 = how people felt in 1966; 50s = very gloomy)") });
stat(s, 9.2, 2.8, 3.5, `${Math.round(D.latest.pred)} vs ${D.latest.actual}`, "'Should feel' vs actually feel, October 2026", HEX.accent1);
stat(s, 9.2, 4.35, 3.5, "2×", "the gap is twice as big as in the 2008 crisis; May 2026 (44.8) was the lowest ever", HEX.dk1);
means(s, "These numbers say people should feel fine (~83). They feel near the worst ever recorded (~46).");
s.addNotes("(40 s) Start with the economy. Unemployment is 4.2% — low; the long-run average is about 6. The economy is growing at a normal 2.2% pace. Inflation is about 3.4% — above the 2% goal but far below the 7% of 2022. Put those into a model trained on history and people 'should' feel around 83 on this scale, where 100 is 1966 and the 50s are very gloomy. They actually feel 46. That gap is twice the size of 2008, and May 2026 was the lowest reading ever. That's the mismatch we set out to explain.");

// ================================================================ 3. THREE EXPLANATIONS
pres.addSection({ title: "Approach" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
s.addText("Three possible explanations — we tested all three", { placeholder: "title" });
[["1", "Real pain the numbers miss", "Prices stayed high, loans got expensive, rent and food went up.", "Biggest piece", HEX.accent3],
 ["2", "Media and psychology", "Negative or biased news coverage; how people's minds process shocks.", "Media: no.  Lived experience: yes.", HEX.accent4],
 ["3", "Measurement", "The survey changed how it asks; old models miss new kinds of shocks.", "Yes, a real part", HEX.accent2]].forEach(([n, h, b, verdict, col], i) => {
  const x = 0.6 + i * 4.1; card(s, x, 1.45, 3.85, 4.55);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: 1.7, w: 0.8, h: 0.8, fill: { color: HEX.dk1 }, line: { color: HEX.dk1 } });
  txt(s, n, { x: x + 0.3, y: 1.7, w: 0.8, h: 0.8, fontSize: 22, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, h, { x: x + 0.3, y: 2.7, w: 3.3, h: 0.8, fontSize: 20, bold: true });
  txt(s, b, { x: x + 0.3, y: 3.5, w: 3.3, h: 1.2, fontSize: 14, color: HEX.dk2 });
  txt(s, "Our verdict", { x: x + 0.3, y: 4.62, w: 3.3, h: 0.3, fontSize: 11, color: HEX.accent5, bold: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.3, y: 4.95, w: 3.25, h: 0.8, rectRadius: 0.1, fill: { color: col }, line: { color: col } });
  txt(s, verdict, { x: x + 0.4, y: 4.95, w: 3.05, h: 0.8, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
});
means(s, "We didn't assume people are irrational or that the news is biased — each explanation had to prove itself with data.");
s.addNotes("(35 s) The professor gave us three possible explanations. One: real pain that the official numbers miss. Two: media and psychology. Three: measurement — the survey or the model is off. We tested each. Here are our verdicts up front: real pain is the biggest piece, measurement is a real part, and the media is not the cause — but people's lived experience of inflation is.");

// ================================================================ 4. DATA CHECKS
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Approach" });
s.addText("First, we made sure the data was right", { placeholder: "title" });
[["1", "Wrong inflation number", "The file's inflation column left out food and gas. We used the full number."],
 ["2", "A number from the future", "It included a GDP figure not published until late October. We removed it."],
 ["3", "Missing month", "The 2025 government shutdown meant October 2025 jobs data was never collected."],
 ["4", "Survey changed", "Michigan moved from phone to online in 2024. Online answers are ~6.6 points gloomier."]].forEach(([n, head, body], i) => {
  const col = i % 2, row = Math.floor(i / 2), x = 0.6 + col * 6.15, y = 1.45 + row * 2.3;
  card(s, x, y, 5.95, 2.1);
  s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.4, w: 0.8, h: 0.8, fill: { color: HEX.dk1 }, line: { color: HEX.dk1 } });
  txt(s, n, { x: x + 0.3, y: y + 0.4, w: 0.8, h: 0.8, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, head, { x: x + 1.35, y: y + 0.3, w: 4.4, h: 0.55, fontSize: 18, bold: true });
  txt(s, body, { x: x + 1.35, y: y + 0.9, w: 4.4, h: 1.1, fontSize: 14, color: HEX.dk2 });
});
means(s, "Our rule: only use numbers that were actually available at the time — no hindsight.");
s.addNotes("(20 s) Before analysing anything we checked the data and found four problems. The inflation column we were given left out food and gas — the things people notice most. It included a GDP number that hadn't been published yet. The 2025 shutdown left a month of jobs data missing. And the survey moved online, which makes answers gloomier by itself. We fixed all four.");

// ================================================================ 5. WHO — AGE
pres.addSection({ title: "Who" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Who" });
s.addText("Who feels worst? Everyone fell — young adults the most", { placeholder: "title" });
s.addChart(pres.charts.BAR, [
  { name: "2019", labels: L.age.labels, values: L.age.y2019 },
  { name: "2025–26", labels: L.age.labels, values: L.age.now },
], { x: 0.6, y: 1.35, w: 7.0, h: 4.75, barDir: "col", barGrouping: "clustered", chartColors: ["9EC5F4", HEX.accent1], barGapWidthPct: 60,
     dataLabelFormatCode: "0", ...axis(), ...legendOn(), valAxisMinVal: 0, ...chartTitle("Sentiment score by age: before (2019) vs now (2025–26)") });
card(s, 8.0, 1.45, 4.7, 2.2);
bullets(s, [
  `18–34: ${L.age.y2019[0]} → ${L.age.now[0]} (fell ${L.age.y2019[0] - L.age.now[0]}) — went from most optimistic to as gloomy as everyone.`,
  `55+: ${L.age.y2019[2]} → ${L.age.now[2]} (fell ${L.age.y2019[2] - L.age.now[2]}) — smallest drop.`,
  `But 55+ is ${L.age_weight[2]}% of the national score (young: ${L.age_weight[0]}%), so older people still move it most.`,
], { x: 8.2, y: 1.6, w: 4.3, h: 2.0, fontSize: 12.5 });
card(s, 8.0, 3.8, 4.7, 2.3, "EAF2FC");
txt(s, [
  { text: "How we got this data", options: { bold: true, fontSize: 14, color: HEX.accent2, breakLine: true, paraSpaceAfter: 5 } },
  { text: "University of Michigan's monthly consumer survey (~1,000 adults a month) publishes the sentiment score separately for each age group. We averaged 2019 vs Jan 2025–Aug 2026. Each group's share of the national score was found by matching the three age scores to the national score, 2015–2026.", options: { fontSize: 12.5 } },
], { x: 8.2, y: 3.95, w: 4.3, h: 2.05, color: HEX.dk1 });
means(s, "This isn't one generation's problem — everyone got gloomier; young adults fell furthest.");
s.addNotes("(45 s) Light blue is 2019, red is now. Every age group dropped by roughly half. Young adults were the most optimistic group in 2019 — 101 — and fell the furthest, 47 points, to 54. People over 55 fell the least, 37 points. But because people over 55 are 44% of the national score, they still pull the national number down the most. Young adults also report more lost income and trouble affording a home. Where the data comes from: Michigan's survey of about a thousand adults a month publishes the score separately by age; we compared 2019 with the 2025–26 average, and worked out each group's share of the national score by matching the three age scores to the national score.");

// ================================================================ 6. WHO — REGION & INCOME
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Who" });
s.addText("It's not one part of the country or one income group", { placeholder: "title" });
s.addChart(pres.charts.BAR, [
  { name: "2019", labels: L.region.labels, values: L.region.y2019 }, { name: "2025–26", labels: L.region.labels, values: L.region.now },
], { x: 0.6, y: 1.35, w: 6.0, h: 4.75, barDir: "col", barGrouping: "clustered", chartColors: ["9EC5F4", HEX.accent2], barGapWidthPct: 50,
     dataLabelFormatCode: "0", ...axis(), ...legendOn(), valAxisMinVal: 0, ...chartTitle("By region: before vs now") });
s.addChart(pres.charts.BAR, [
  { name: "2019", labels: L.income.labels, values: L.income.y2019 }, { name: "2025–26", labels: L.income.labels, values: L.income.now },
], { x: 6.8, y: 1.35, w: 5.9, h: 4.75, barDir: "col", barGrouping: "clustered", chartColors: ["C9C2F0", HEX.accent6], barGapWidthPct: 50,
     dataLabelFormatCode: "0", ...axis(), ...legendOn(), valAxisMinVal: 0, ...chartTitle("By income: before vs now") });
means(s, "Every region and every income level lost about 40 points — a nationwide shock, not a local one.");
s.addNotes("(30 s) Next we asked: is one region or one income group driving this? No. The Northeast, Midwest, South and West all fell by about 40 points. Low, middle and high earners all fell by about 40 points too. Since everyone fell together, the cause must be something national that hit everyone — which brings us to prices.");

// ================================================================ 7a. IN THEIR OWN WORDS
pres.addSection({ title: "Why" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
s.addText("In their own words: people say it's prices and borrowing costs", { placeholder: "title" });
const RS = D.reasons;
s.addChart(pres.charts.BAR, [
  { name: "2019", labels: ["Worse off because of higher prices", "Bad time to buy a home: interest rates", "Bad time to buy big items: prices high"], values: [RS.pagorn_hp_all.y2019, RS.homrn_hr_all.y2019, RS.durrn_hp_all.y2019] },
  { name: "2022 (inflation peak)", labels: ["Worse off because of higher prices", "Bad time to buy a home: interest rates", "Bad time to buy big items: prices high"], values: [RS.pagorn_hp_all.y2022, RS.homrn_hr_all.y2022, RS.durrn_hp_all.y2022] },
  { name: "2025–26", labels: ["Worse off because of higher prices", "Bad time to buy a home: interest rates", "Bad time to buy big items: prices high"], values: [RS.pagorn_hp_all.now, RS.homrn_hr_all.now, RS.durrn_hp_all.now] },
], { x: 0.6, y: 1.35, w: 7.6, h: 4.75, barDir: "col", barGrouping: "clustered", chartColors: ["C9D3E0", "F2B8B5", HEX.accent1], barGapWidthPct: 50,
     dataLabelFormatCode: "0\"%\"", ...axis(), ...legendOn(), dataLabelFontSize: 11, catAxisLabelFontSize: 11.5,
     ...chartTitle("% of Michigan respondents giving each reason (they answer in their own words)") });
card(s, 8.5, 1.45, 4.2, 4.6);
txt(s, [
  { text: "It's about today, not the future", options: { bold: true, fontSize: 16, breakLine: true, paraSpaceAfter: 6 } },
  { text: `The gap in how people rate their situation right now (${D.icc_ice_gap_2026.icc} points) is much bigger than in what they expect for the future (${D.icc_ice_gap_2026.ice}).`, options: { fontSize: 13.5, breakLine: true, paraSpaceAfter: 12 } },
  { text: "Worse than 2022 — even though inflation was higher then", options: { bold: true, fontSize: 16, breakLine: true, paraSpaceAfter: 6 } },
  { text: `${Math.round(RS.pagorn_hp_all.now)}% now blame higher prices vs ${Math.round(RS.pagorn_hp_all.y2022)}% at the 2022 peak. Expected inflation is ${RS.px1_med_all.now}% (2019: ${RS.px1_med_all.y2019}%).`, options: { fontSize: 13.5 } },
], { x: 8.75, y: 1.65, w: 3.75, h: 4.3, color: HEX.dk1 });
means(s, "People tell us directly what hurts: the cost of living today — and it hurts more now than at the 2022 peak.");
s.addNotes("(35 s) Michigan doesn't just ask how people feel — it asks why, in their own words. In 2019, 7% said they were worse off because of higher prices. Today it's 45% — more than at the 2022 inflation peak. 44% say it's a bad time to buy a home because of interest rates, up from 8%. And the gap is mostly about today's situation, not the future. So people are telling us directly: it's the cost of living.");

// ================================================================ 7. INFLATION
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
s.addText("Why 'inflation is down' doesn't feel like it", { placeholder: "title" });
card(s, 0.6, 1.45, 5.6, 4.6, "EAF2FC");
txt(s, [
  { text: "The egg example", options: { bold: true, fontSize: 18, color: HEX.accent2, breakLine: true, paraSpaceAfter: 8 } },
  { text: "2021: eggs cost $2.", options: { fontSize: 15, breakLine: true, paraSpaceAfter: 4 } },
  { text: "2023: eggs cost $4. Inflation was high.", options: { fontSize: 15, breakLine: true, paraSpaceAfter: 4 } },
  { text: "2026: eggs cost $4.12. The government says inflation is 'low' (3%).", options: { fontSize: 15, breakLine: true, paraSpaceAfter: 12 } },
  { text: "Official inflation measures how fast prices are rising now — not whether they came back down. People remember $2.", options: { fontSize: 15, bold: true, breakLine: true, paraSpaceAfter: 12 } },
  { text: "It also leaves out loan costs: a 7% mortgage instead of 3% doesn't count as 'inflation'.", options: { fontSize: 14, color: HEX.dk2 } },
], { x: 0.85, y: 1.65, w: 5.1, h: 4.3 });
if (D.nec_full) s.addChart(pres.charts.BAR, [{ name: "% increase since January 2021", labels: D.nec_full.labels, values: D.nec_full.values }], {
  x: 6.5, y: 1.35, w: 6.2, h: 4.75, barDir: "bar", chartColors: [HEX.accent5, HEX.accent1, HEX.accent1, HEX.accent1, HEX.accent3], varyColors: true,
  barGapWidthPct: 40, dataLabelFormatCode: "0\"%\"", catAxisOrientation: "maxMin", ...axis(), ...chartTitle("How much more things cost vs how much more people earn (Jan 2021 → Sep 2026)"),
});
means(s, `Prices up ${D.nec.cpi}%, paychecks up ${D.nec.wages}% — people aren't imagining it.`);
s.addNotes("(45 s) This is the key idea. Eggs were 2 dollars in 2021, 4 dollars in 2023. Today they rise slowly — 4 dollars 12 — so the government says inflation is low. But it measures how fast prices rise now, not whether they came back down; people remember 2 dollars. It also doesn't count loan costs — a 7% mortgage isn't 'inflation'. On the right: since 2021 prices rose 28%, rent and housing 32%, gas 68%, but paychecks only 26%. So people really are worse off.");

// ================================================================ 8. WHAT EXPLAINS IT (ranked)
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
const total = Math.abs(D.actual_change);
D.ranked = D.ranked.slice(0, 5).sort((a, b) => a[1] - b[1]).concat([D.ranked[5]]);
s.addText(`What's causing the ${Math.round(total)}-point drop, ranked`, { placeholder: "title" });
s.addChart(pres.charts.BAR, [{ name: "Points of the drop", labels: D.ranked.map(r => r[0]), values: D.ranked.map(r => Math.abs(r[1])) }], {
  x: 0.6, y: 1.35, w: 7.9, h: 4.75, barDir: "bar", chartColors: [HEX.accent1, HEX.accent2, HEX.accent4, HEX.accent6, HEX.accent5, "C9CED6"], varyColors: true,
  barGapWidthPct: 40, dataLabelFormatCode: "0.0", catAxisOrientation: "maxMin", ...axis(), catAxisLabelFontSize: 12.5,
  ...chartTitle(`Points of the ${Math.round(total)}-point drop since 2019 explained by each cause`),
});
card(s, 8.8, 1.45, 3.9, 4.6);
const sh = D.ranked.map(r => Math.round(100 * Math.abs(r[1]) / total));
bullets(s, [`Prices & cost of living: the #1 cause (${sh[0]}% of the drop) — prices ~11% above normal, food, gas.`,
            `The survey moving online: ${sh[1]}%.`, `Tariff and shutdown uncertainty: ${sh[2]}%.`,
            `The official 'headline' numbers (jobs, growth) explain very little.`,
            `About ${Math.round(Math.abs(D.ranked[5][1]))} points remain unexplained — we say so honestly.`], { x: 9.05, y: 1.6, w: 3.45, h: 4.4, fontSize: 13 });
means(s, `High prices, the survey change and policy uncertainty: ${Math.round(Math.abs(D.ranked[0][1]+D.ranked[1][1]+D.ranked[2][1]))} of the ${Math.round(total-Math.abs(D.ranked[5][1]))} points we can explain.`);
s.addNotes("(40 s) Now we rank the causes of the 41-point drop. Number one is the cost of living — prices about 11% above normal, plus food and gas — about 11 points. Number two is the survey moving online, about 7. Number three is uncertainty from tariffs and the shutdown, about 6. Jobs, income and growth explain only about 2 and a half, and the mix of who answers the survey politically about 2. Roughly 12 points we can't explain with any measure, and we report that honestly. One caution: the uncertainty index is built from newspapers, so it reflects real policy shocks as reported in the news.");

// ================================================================ 9. WHY THE YOUNG
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
s.addText("Why young adults fell furthest: it was their first big inflation", { placeholder: "title" });
const ratio = D.exp_rise ? Math.round(D.exp_rise.young / D.exp_rise.old) : 0;
if (D.exp_rise) s.addChart(pres.charts.BAR, [{ name: "Increase in 'lived-through' inflation", labels: ["18–34", "55+"], values: [D.exp_rise.young, D.exp_rise.old] }], {
  x: 0.6, y: 1.35, w: 5.4, h: 4.75, barDir: "col", chartColors: [HEX.accent1, HEX.accent5], varyColors: true, barGapWidthPct: 70, dataLabelFormatCode: "0.00", ...axis(),
  ...chartTitle("How much 2021–23 raised each group's lifetime inflation memory"),
});
card(s, 6.4, 1.45, 6.3, 4.6);
txt(s, [
  { text: "The idea", options: { bold: true, fontSize: 17, breakLine: true, paraSpaceAfter: 6 } },
  { text: "People learn about inflation from what they have lived through. For a 26-year-old, two years of high inflation is a big share of their whole life. For a 66-year-old who lived through the 1970s, it's a small blip.", options: { fontSize: 14, breakLine: true, paraSpaceAfter: 12 } },
  { text: "What we found", options: { bold: true, fontSize: 17, breakLine: true, paraSpaceAfter: 6 } },
  { text: `The 2021–23 shock raised young adults' inflation memory about ${ratio}× more than older adults'.`, options: { fontSize: 14, breakLine: true, paraSpaceAfter: 6 } },
  { text: D.exp_rise ? `Young adults fell ${Math.abs(D.exp_rise.actual)} points more than 55+. This effect explains about ${Math.abs(D.exp_rise.pred)} of those ${Math.abs(D.exp_rise.actual)} points.` : "", options: { fontSize: 14, bold: true } },
], { x: 6.65, y: 1.65, w: 5.85, h: 4.3, color: HEX.dk1 });
means(s, "Young people aren't irrational — they're learning from the only big inflation they've ever seen.");
s.addNotes("(45 s) Why did young adults fall furthest? Economists have shown that people learn about inflation from what they've lived through. For a 26-year-old, two years of high inflation is a big chunk of their life; for a 66-year-old who remembers the 1970s, it's a blip. We measured this: the recent shock raised young adults' inflation memory about ten times more than older adults'. Young adults fell about 10 points more than people over 55 — and this effect explains about 8 of those 10 points, comparing groups in the same month so the news is identical for everyone.");

// ================================================================ 9b. POLITICS
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
s.addText("Party matters — but independents are gloomy too", { placeholder: "title" });
if (D.transition) {
  const PT = D.transition.party;
  s.addChart(pres.charts.BAR, [
    { name: "June 2022 (Biden)", labels: ["Democrats", "Independents", "Republicans"], values: [66.4, 48.5, 33.0] },
    { name: "May 2026 (Trump)", labels: ["Democrats", "Independents", "Republicans"], values: [32.8, 40.6, 84.6] },
  ], { x: 0.6, y: 1.35, w: 7.2, h: 4.75, barDir: "col", barGrouping: "clustered", chartColors: ["9EC5F4", HEX.accent1], barGapWidthPct: 50,
       dataLabelFormatCode: "0", ...axis(), ...legendOn(), ...chartTitle("Sentiment by party at the two lowest points (University of Michigan reports)") });
}
card(s, 8.2, 1.45, 4.5, 4.6);
bullets(s, ["People whose party holds the White House feel much better. This flips every election — Michigan has seen it since the 1980s.",
            "Independents — the middle — are the best guide to the national mood. They are at 41: very gloomy too.",
            "Since 2025, fewer people call themselves Republican in the survey. That alone lowers the national score by about 2 points."],
        { x: 8.45, y: 1.65, w: 4.05, h: 4.3, fontSize: 13.5 });
means(s, "Party colors how people judge the economy, but the gloom is real across the political middle.");
s.addNotes("(35 s) Politics matters, as the brief warned. Michigan's own reports show that people whose party is in power feel much better — Democrats were at 66 in 2022 and are at 33 now; Republicans went from 33 to 85. That flips every election. But independents — the middle — track the national number, and they're at 41, very gloomy. And fewer people now identify as Republican in the survey, which lowers the headline by about 2 points. So politics changes who feels bad, but it doesn't make the gloom fake.");

// ================================================================ 10. MEDIA — HOW WE CHECKED
pres.addSection({ title: "Media" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Media" });
s.addText("Is the media to blame? How we checked", { placeholder: "title" });
[["1  Collected", `${Math.round(D.corpus_items / 1000)}k news headlines and social posts, 2010–2026, from ${D.corpus_sources.toLocaleString()}+ outlets`],
 ["2  Rulebook", "Wrote clear rules first: is this good or bad news for households? Is it slanted?"],
 ["3  AI reader", "An AI read every headline. A human checked 300: the AI agreed 70% of the time — better than word lists (43%) or other AI (50%)"],
 ["4  Fair tests", "Negative isn't biased if the news is bad. We compared coverage to the real data and to other outlets in the same month"]].forEach(([h, b], i) => {
  const x = 0.6 + i * 3.1; card(s, x, 1.4, 2.85, 2.65);
  txt(s, h, { x: x + 0.2, y: 1.55, w: 2.45, h: 0.45, fontSize: 17, bold: true, color: HEX.accent2 });
  txt(s, b, { x: x + 0.2, y: 2.05, w: 2.45, h: 1.9, fontSize: 13, color: HEX.dk2 });
});
card(s, 0.6, 4.25, 12.1, 1.85, "EAF2FC");
const mRMSE = D.horse ? D.horse.rmse : null;
bullets(s, [
  "Yes, there is political slant: right-leaning outlets sound much more negative when a Democrat is president (and vice versa).",
  "No, the news isn't overly negative: bad news isn't covered more than equally big good news, and 'inflation falling' stories rise when inflation falls.",
  mRMSE ? `Adding news data to our forecast made it ${pct(mRMSE["M1 econ only"], mRMSE["M2 + media"])}% worse. Adding everyday-cost data made it ${-pct(mRMSE["M1 econ only"], mRMSE["M3b econ + controls (no media)"])}% better.` : "",
], { x: 0.85, y: 4.38, w: 11.6, h: 1.65, fontSize: 14 });
means(s, "The news has a political tilt, but it isn't driving the mood — knowing the news doesn't help predict it.");
s.addNotes("(45 s) To test the media explanation we collected about 247,000 headlines and posts, wrote rules first, and had an AI read every one. A human checked 300 of them; the AI matched the human 70% of the time, better than simpler tools. Then we ran fair tests — negative news isn't biased if the news really is bad. Findings: yes, there's political slant. But coverage isn't overly negative, and adding news data actually made our sentiment forecasts worse, while adding everyday-cost data made them better.");

// ================================================================ 11. THE TEST
if (D.transition) {
  const T = D.transition;
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Media" });
  s.addText("The test: moods kept falling, but the news didn't get worse", { placeholder: "title" });
  s.addChart(pres.charts.BAR, [{ name: "Average sentiment score", labels: T.admins, values: T.ics }], {
    x: 0.6, y: 1.35, w: 5.9, h: 4.75, barDir: "col", chartColors: [HEX.accent1], barGapWidthPct: 55, dataLabelFormatCode: "0", ...axis(),
    ...chartTitle("Average sentiment score under each president"),
  });
  card(s, 6.9, 1.45, 5.8, 4.6);
  txt(s, [
    { text: "What should have happened if media caused it", options: { bold: true, fontSize: 16, breakLine: true, paraSpaceAfter: 6 } },
    { text: "Sentiment fell another 14.5 points after January 2025. If the news drove that, news coverage should have turned much more negative.", options: { fontSize: 14, breakLine: true, paraSpaceAfter: 12 } },
    { text: "What actually happened", options: { bold: true, fontSize: 16, breakLine: true, paraSpaceAfter: 6 } },
    { text: `Overall news tone barely changed. Even in the worst case, that change explains about ${D.magnitude ? D.magnitude.implied : 1} point of the 14.5-point drop.`, options: { fontSize: 14, breakLine: true, paraSpaceAfter: 12 } },
    { text: "Right-leaning outlets did turn more positive under Trump — slant follows whoever is in power — but the total news mood stayed the same.", options: { fontSize: 13, color: HEX.dk2 } },
  ], { x: 7.15, y: 1.65, w: 5.35, h: 4.3, color: HEX.dk1 });
  means(s, "The news can amplify the mood, but it didn't cause the collapse.");
  s.addNotes("(45 s) This is our own test. When the presidency changed in January 2025, sentiment fell another 14 and a half points. If the media were causing that, the news should have turned much more negative. It didn't: overall news tone barely moved — even in the worst case, that explains about one point of the fourteen-and-a-half. Right-leaning outlets did turn more positive, as they always do when their side is in power, but the total news mood stayed flat. So the news may amplify the mood, but it didn't cause the collapse.");
}

// ================================================================ 11b. THE ANSWER
pres.addSection({ title: "So what" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "So what" });
s.addText("So what is causing the mismatch?", { placeholder: "title" });
const R = D.ranked;
const rv = k => Math.abs(R.find(r => r[0].startsWith(k))[1]);
const realPts = rv("High prices") + rv("Policy") + rv("Jobs"), measPts = rv("Survey") + rv("Partisan");
[["Real costs the headline numbers miss", `${Math.round(realPts)} points`, ["Prices ~11% above normal; paychecks behind", "Mortgage rates: 44% say it's a bad time to buy a home", "Tariff & shutdown uncertainty"], HEX.accent1],
 ["How it's measured", `${Math.round(measPts)} points`, ["Survey moved from phone to online (−6.6)", "Fewer Republicans answering (−2.4)", "Old models never saw a shock like this"], HEX.accent2],
 ["How people interpret it", "who is hit hardest", [`Young adults: first big inflation (~${D.experience ? D.experience.share : 78}% of their extra drop)`, "Party in power feels better", `Media: ~${D.magnitude ? D.magnitude.implied : 1} point — not the cause`], HEX.accent4]].forEach(([h, big, items, col], i) => {
  const x = 0.6 + i * 4.1; card(s, x, 1.45, 3.85, 4.6);
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: 1.65, w: 3.35, h: 0.55, rectRadius: 0.1, fill: { color: col }, line: { color: col } });
  txt(s, h, { x: x + 0.35, y: 1.65, w: 3.15, h: 0.55, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle" });
  txt(s, big, { x: x + 0.3, y: 2.35, w: 3.3, h: 0.6, fontSize: 26, bold: true, fontFace: THEME.headFontFace, color: HEX.dk1 });
  bullets(s, items, { x: x + 0.3, y: 3.05, w: 3.3, h: 2.9, fontSize: 15 });
});
means(s, `Of ${Math.round(total)} points: ~${Math.round(realPts)} real costs, ~${Math.round(measPts)} measurement, ~${Math.round(rv("Not explained"))} unexplained — and media explains about 1.`);
s.addNotes("(35 s) Putting it all together. About 20 of the 41 points are real costs the headline numbers miss — prices, borrowing costs and policy uncertainty. About 9 points are how it's measured — the online survey and who answers. Then interpretation shapes who is hit hardest: young adults living through their first big inflation, and partisanship. The media explains about one point. Roughly 12 points remain unexplained, which we report rather than hide.");

// ================================================================ 12. FOR INVESTORS
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "So what" });
s.addText("What this means for investors and forecasters", { placeholder: "title" });
if (D.spend) {
  const r = D.spend.rmse;
  s.addChart(pres.charts.BAR, [{ name: "Forecast error", labels: ["Economy data only", "+ how people say they feel", "+ only the 'economy part' of feelings", "+ only the 'gloom gap'"], values: r }], {
    x: 0.6, y: 1.35, w: 7.3, h: 4.75, barDir: "bar", chartColors: [HEX.accent5, HEX.accent1, HEX.accent3, HEX.accent1], varyColors: true,
    barGapWidthPct: 45, dataLabelFormatCode: "0.00", catAxisOrientation: "maxMin", ...axis(),
    ...chartTitle("Error when predicting consumer spending, 2022–26 (shorter bar = better forecast)"),
  });
  card(s, 8.2, 1.45, 4.5, 4.6, HEX.dk1);
  txt(s, [
    { text: "The lesson", options: { bold: true, fontSize: 18, color: C.background1, breakLine: true, paraSpaceAfter: 8 } },
    { text: "Since 2022 people said they felt awful — and kept spending about 2.5% more each year.", options: { fontSize: 14, color: C.background1, breakLine: true, paraSpaceAfter: 8 } },
    { text: `Using the survey as-is made spending forecasts ${pct(r[0], r[1])}% worse. Using only the part that matches the economy made them ${-pct(r[0], r[2])}% better.`, options: { fontSize: 14, color: C.background1, breakLine: true, paraSpaceAfter: 8 } },
    { text: "So: separate real economic worry from the 'gloom gap' before betting on a recession.", options: { fontSize: 14, color: "F2B8B5", bold: true } },
  ], { x: 8.45, y: 1.7, w: 4.0, h: 4.3 });
}
means(s, "Bottom line: high prices, the survey change and lived experience — not media bias — explain the gloom.");
s.addNotes("(40 s) Why this matters for finance. Since 2022 people said they felt terrible but kept spending — about 2.5% more each year. When we tried to predict spending, using the survey as-is made forecasts about 20% worse. Using only the part of sentiment that matches the economy made them about 17% better. So investors and risk managers should separate real economic worry from the gloom gap before betting on a recession. Bottom line: high prices, the survey change and lived experience — not media bias — explain the gloom.");

// ================================================================ 13. THANK YOU
s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "So what" });
s.addText("Thank you", { placeholder: "title" });
s.addText([
  { text: "Key takeaway", options: { breakLine: true, bold: true, color: "F2B8B5", fontSize: 20 } },
  { text: "Americans aren't gloomy because of biased news. Prices stayed high, the survey changed, and young people lived through their first big inflation.", options: { breakLine: true, color: "FFFFFF", fontSize: 20 } },
  { text: "Questions?", options: { bold: true, color: "CBD2DC", fontSize: 18 } },
], { placeholder: "body" });
s.addNotes("(10 s) Thank you. The key takeaway: Americans aren't gloomy because of biased news — prices stayed high, the survey changed, and young people lived through their first big inflation. Happy to take questions.");

// ================================================================ BACKUP 1: SIX QUESTIONS
pres.addSection({ title: "Backup" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup: answers to the six required questions", { placeholder: "title" });
const qa = [["1. How can we measure media bias?", "Against benchmarks: equal good vs bad news, the real data, the same month across outlets, official numbers. AI coder checked against 300 human labels (70% agreement)."],
  ["2. Is bias depressing sentiment?", "No evidence: news adds no forecasting power; in 2025 tone barely changed while sentiment fell 14.5 points (~1 point explained)."],
  ["3. How much do jobs, inflation, GDP explain?", "Only ~13% of the 41-point drop."],
  ["4. Which mental biases can we measure?", "Anchoring to old prices and learning from lived inflation: yes. Partisanship: indirectly. Availability/confirmation bias in readers: no (no exposure data)."],
  ["5. Does media data improve predictions?", "No — forecasts get ~25% worse; everyday-cost data makes them ~24% better."],
  ["6. What would contradict a media story?", "Seven tests written in advance; most came out against it (see report Table 11)."]];
s.addTable(qa.map(([q, a]) => [{ text: q, options: { bold: true } }, { text: a }]), { x: 0.6, y: 1.4, w: 12.1, colW: [3.6, 8.5], fontSize: 12.5, fontFace: THEME.bodyFontFace, color: HEX.dk1, border: { type: "solid", pt: 0.5, color: "D9DEE5" }, rowH: 0.72 });
s.addNotes("Backup for questions: one-line answers to the six research questions the brief requires.");

// ================================================================ BACKUP 2: CAUSE & LIMITS
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
s.addText("Backup: how we would prove cause — and our limits", { placeholder: "title" });
card(s, 0.6, 1.45, 5.95, 4.6, "EAF2FC");
bullets(s, ["Experiment (needs ethics approval): show 2,400 people the same inflation facts framed four ways — balanced, as a rate, as a price level, as household cost — and measure their sentiment.",
            "Quasi-experiment: compare places that watch different TV channels (channel position is close to random), using survey data with locations.",
            "Linking a lab result to the national number needs exposure data, matching the survey's population, and decay estimates."], { x: 0.85, y: 1.65, w: 5.5, h: 4.3, fontSize: 13.5 });
card(s, 6.75, 1.45, 5.95, 4.6);
bullets(s, ["One human labeler (re-check used instead of a second person).",
            "AI coder reacts slightly to party names (7% of labels flip) — reported.",
            "Google News ranking and short social-media history limit the corpus.",
            "No data on what each survey respondent actually read.",
            "About 12 points of the drop remain unexplained."], { x: 7.0, y: 1.65, w: 5.5, h: 4.3, fontSize: 13.5 });
s.addNotes("Backup for questions: our causal-design proposal (the brief's third option) and the honest limits of the study.");

(async () => {
  const out = path.join(__dirname, "Sentiment_Midterms_Summary.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();

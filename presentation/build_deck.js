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
s.addText("The economy looks OK. People feel terrible.", { placeholder: "title" });
s.addChart(pres.charts.LINE, [
  { name: "How people actually feel", labels: D.chart_gap.labels, values: D.chart_gap.actual },
  { name: "How they 'should' feel, given jobs, inflation and growth", labels: D.chart_gap.labels, values: D.chart_gap.pred },
], { x: 0.6, y: 1.35, w: 8.2, h: 4.75, chartColors: [HEX.dk1, HEX.accent2], lineSize: 2.5, lineDataSymbol: "none", ...legendOn(),
     catAxisLabelColor: "7A8392", valAxisLabelColor: "7A8392", catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, catAxisLabelFontFace: "+mn-lt",
     valAxisLabelFontFace: "+mn-lt", catAxisLabelFrequency: 4, valAxisMinVal: 30, valAxisMaxVal: 110, valGridLine: { color: "E6E9EE", size: 0.5 },
     catGridLine: { style: "none" }, ...chartTitle("Consumer sentiment score, 2015–2026 (100 = how people felt in 1966; 50s = very gloomy)") });
stat(s, 9.2, 1.45, 3.5, `${Math.round(D.latest.pred)} vs ${D.latest.actual}`, "'Should be' vs actual, October 2026", HEX.accent1);
stat(s, 9.2, 2.95, 3.5, "2×", "the gap is twice as big as in the 2008 financial crisis", HEX.dk1);
stat(s, 9.2, 4.45, 3.5, "44.8", "May 2026: lowest reading since the survey began in 1952", HEX.dk2);
means(s, "Official numbers say people should feel fine (~83). They feel near the worst ever (~46).");
s.addNotes("(45 s) How to read this: the survey score is 100 when people feel like they did in 1966; in the 50s people are very gloomy. The blue line is how people 'should' feel based on unemployment, inflation and growth — using only data available at each moment. The black line is how they actually feel. Today they should be around 83; they're at 46. That gap is twice as big as in the 2008 financial crisis, and May 2026 was the lowest reading ever recorded. That's the puzzle.");

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
s.addNotes("(30 s) Before analysing anything we checked the data and found four problems. The inflation column we were given left out food and gas — the things people notice most. It included a GDP number that hadn't been published yet. The 2025 shutdown left a month of jobs data missing. And the survey moved online, which makes answers gloomier by itself. We fixed all four.");

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

// ================================================================ 7. INFLATION
pres.addSection({ title: "Why" });
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

// ================================================================ 8. WHAT EXPLAINS IT
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Why" });
const total = Math.abs(D.actual_change);
s.addText(`So what explains the ${Math.round(total)}-point drop since 2019?`, { placeholder: "title" });
const decLabels = ["Jobs, inflation, growth (official numbers)", "Everyday costs: high prices, food, loans, job worries", "Survey moved online", "Fewer Republicans answering (estimate)", "Not explained"];
s.addChart(pres.charts.BAR, [{ name: "Points of the drop", labels: decLabels, values: D.decomp.map(d => Math.abs(d[1])) }], {
  x: 0.6, y: 1.35, w: 7.9, h: 4.75, barDir: "bar", chartColors: [HEX.accent5, HEX.accent1, HEX.accent2, HEX.accent6, "B8BEC8"], varyColors: true,
  barGapWidthPct: 45, dataLabelFormatCode: "0", catAxisOrientation: "maxMin", ...axis(), catAxisLabelFontSize: 12.5,
  ...chartTitle(`How many of the ${Math.round(total)} points each cause explains`),
});
card(s, 8.8, 1.45, 3.9, 4.6);
const sh = D.decomp.map(d => Math.round(100 * Math.abs(d[1]) / total));
bullets(s, [`Official numbers: only ${sh[0]}% of the drop.`, `Everyday costs: the biggest piece (${sh[1]}%).`, `Survey change: ${sh[2]}%.`,
            `The rest (~${Math.round(Math.abs(D.decomp[4][1]))} points) is the most the media could possibly explain.`], { x: 9.05, y: 1.65, w: 3.45, h: 4.3, fontSize: 14 });
means(s, "Most of the drop is real everyday pain plus a change in how the survey is done.");
s.addNotes("(40 s) Here we split the 41-point drop into pieces. The official numbers — jobs, inflation, growth — explain only about 5 points. Everyday costs — high prices, food, loans and job worries — explain about 15, the biggest piece. The survey moving online explains about 7. Fewer Republicans answering explains about 2. About 12 points are left unexplained — that's the most any media story could account for.");

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

// ================================================================ 12. FOR INVESTORS
pres.addSection({ title: "So what" });
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

(async () => {
  const out = path.join(__dirname, "Sentiment_Midterms_Summary.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();

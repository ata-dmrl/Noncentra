"use strict";
// Noncentra web UI. Two interchangeable engines return the same JSON documents:
//   pyodide: the noncentra package running in the browser (web/noncentra.zip)
//   api:     the FastAPI server (noncentra/http_api.py), when this page is served by it

const PYODIDE_PACKAGES = ["numpy", "scipy"];

const CONVENTIONS = { d: [0.2, 0.5, 0.8], dz: [0.2, 0.5, 0.8], f: [0.1, 0.25, 0.4], f2: [0.02, 0.15, 0.35] };
const EFFECT_LABEL = { d: "Etki büyüklüğü d", dz: "Etki büyüklüğü dz", f: "Etki büyüklüğü f", f2: "Etki büyüklüğü f²" };
const ANALYSIS_NAME = {
  a_priori: "A priori", post_hoc: "Post hoc", sensitivity: "Sensitivity",
  criterion: "Criterion", compromise: "Compromise",
};
const NEEDS = {
  a_priori: ["effect_size", "alpha", "power"],
  post_hoc: ["effect_size", "alpha", "sizes"],
  sensitivity: ["alpha", "power", "sizes"],
  criterion: ["effect_size", "power", "sizes"],
  compromise: ["effect_size", "beta_alpha_ratio", "sizes"],
};
const DEFAULTS = {
  effect_size: { d: 0.5, dz: 0.5, f: 0.25, f2: 0.15 }, alpha: 0.05, power: 0.8, beta_alpha_ratio: 1,
  tails: 2, ratio: 1, groups: 3, predictors: 5, tested: 2, n: 60, n1: 30, n2: 30,
};
const OPTION_LABEL = {
  tails: "Kuyruk sayısı", ratio: "Grup oranı n2/n1", groups: "Grup sayısı",
  predictors: "Toplam yordayıcı sayısı", tested: "Test edilen yordayıcı sayısı",
};
const SIZE_LABEL = { n: "Toplam örneklem büyüklüğü", n1: "Grup 1 örneklem büyüklüğü", n2: "Grup 2 örneklem büyüklüğü" };

const $ = (id) => document.getElementById(id);
const state = { engine: null, tests: [], last: null, lastRequest: null };

// ---------- engines ----------

class ApiEngine {
  async init() {
    const r = await fetch("/api/health");
    if (!r.ok) throw new Error("API yanıt vermiyor");
  }
  async call(name, req) {
    const r = name === "tests"
      ? await fetch("/api/tests")
      : await fetch(`/api/${name}`, {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req),
        });
    return r.json();
  }
}

class PyodideEngine {
  async init(onStatus) {
    if (typeof loadPyodide !== "function") throw new Error("Pyodide yüklenemedi (internet bağlantısı?)");
    onStatus("Python yükleniyor…");
    this.py = await loadPyodide();
    onStatus("scipy yükleniyor…");
    await this.py.loadPackage(PYODIDE_PACKAGES);
    onStatus("Noncentra yükleniyor…");
    const build = document.querySelector('meta[name="build"]')?.content ?? "dev";
    const zip = await fetch(`noncentra.zip?v=${encodeURIComponent(build)}`);
    if (!zip.ok) throw new Error("noncentra.zip bulunamadı; önce: python web/build_bundle.py");
    this.py.unpackArchive(await zip.arrayBuffer(), "zip");
    this.bridge = this.py.pyimport("noncentra.web_bridge");
  }
  async call(name, req) {
    return JSON.parse(this.bridge.call(name, JSON.stringify(req || {})));
  }
}

const engines = { api: new ApiEngine(), pyodide: new PyodideEngine() };
const ready = {};

function setStatus(text, kind = "") {
  const el = $("engine-status");
  el.textContent = text;
  el.className = `status ${kind}`;
}

async function useEngine(name) {
  $("calc").disabled = true;
  try {
    ready[name] ??= engines[name].init((t) => setStatus(t));
    await ready[name];
    state.engine = engines[name];
    setStatus(name === "api" ? "sunucu hazır" : "tarayıcıda hazır", "ok");
    const doc = await state.engine.call("tests");
    state.tests = doc.tests;
    renderTestSelect();
    $("calc").disabled = false;
  } catch (err) {
    delete ready[name];
    setStatus(err.message, "bad");
  }
}

async function apiAvailable() {
  try {
    return (await fetch("/api/health")).ok;
  } catch {
    return false;
  }
}

// ---------- form ----------

function currentTest() {
  return state.tests.find((t) => t.name === $("test").value);
}

// The test a finished request was for (the form may have changed since).
function testOf(req) {
  return state.tests.find((t) => t.name === req.test);
}

function renderTestSelect() {
  const sel = $("test");
  const keep = sel.value;
  sel.innerHTML = "";
  const groups = { t: "t testleri", f: "F testleri" };
  for (const [prefix, label] of Object.entries(groups)) {
    const og = document.createElement("optgroup");
    og.label = label;
    for (const t of state.tests.filter((t) => t.name.startsWith(prefix + "."))) {
      og.append(new Option(t.title, t.name));
    }
    if (og.children.length) sel.append(og);
  }
  if (keep && state.tests.some((t) => t.name === keep)) sel.value = keep;
  renderFields();
}

function numberField(key, label, value, attrs = {}) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  const id = `f-${key}`;
  wrap.innerHTML = `<label for="${id}">${label}</label>`;
  const input = document.createElement("input");
  // A text field, not type="number": a number field silently empties "0,95" (Turkish decimal
  // comma) in some browsers, which then failed validation. num() accepts both comma and dot.
  Object.assign(input, { id, name: key, type: "text", inputMode: "decimal", value, autocomplete: "off",
                         spellcheck: false, ...attrs });
  wrap.append(input);
  return wrap;
}

function renderFields(values = {}) {
  const test = currentTest();
  if (!test) return;
  const analysis = $("analysis").value;
  const needs = NEEDS[analysis];
  // Test options (tails, groups, …) go to the settings card, numbers to the values card.
  const settings = $("settings-fields");
  const box = $("value-fields");
  const old = Object.fromEntries([...settings.querySelectorAll("input, select"), ...box.querySelectorAll("input, select")]
    .map((e) => [e.name, e.value]));
  const val = (k, d) => values[k] ?? old[k] ?? d;
  settings.innerHTML = "";
  box.innerHTML = "";

  for (const opt of test.options) {
    if (opt === "ratio" && analysis !== "a_priori") continue;  // sizes given directly otherwise
    if (opt === "tails") {
      const wrap = document.createElement("div");
      wrap.className = "field";
      wrap.innerHTML = `<label for="f-tails">${OPTION_LABEL.tails}</label>
        <select id="f-tails" name="tails"><option value="2">İki yönlü</option><option value="1">Tek yönlü</option></select>`;
      settings.append(wrap);
      wrap.querySelector("select").value = String(val("tails", DEFAULTS.tails));
    } else {
      const integer = opt !== "ratio";
      settings.append(numberField(opt, OPTION_LABEL[opt], val(opt, DEFAULTS[opt]),
        integer ? { step: 1, min: 1, inputMode: "numeric" } : { min: 0 }));
    }
  }
  if (needs.includes("effect_size")) {
    const f = numberField("effect_size", EFFECT_LABEL[test.effect_size] ?? "Etki büyüklüğü",
      val("effect_size", DEFAULTS.effect_size[test.effect_size]), { min: 0 });
    const conv = document.createElement("div");
    conv.className = "conventions";
    ["küçük", "orta", "büyük"].forEach((name, i) => {
      const v = CONVENTIONS[test.effect_size][i];
      const b = document.createElement("button");
      Object.assign(b, { type: "button", className: "chip", textContent: `${name} ${v}` });
      b.title = "Cohen (1988) kuralları";
      b.onclick = () => { f.querySelector("input").value = v; };
      conv.append(b);
    });
    f.append(conv);
    box.append(f);
  }
  const pair = document.createElement("div");
  pair.className = "row2";
  if (needs.includes("alpha")) pair.append(numberField("alpha", "α hata olasılığı", val("alpha", DEFAULTS.alpha), { min: 0, max: 1 }));
  if (needs.includes("power")) pair.append(numberField("power", "Güç (1−β)", val("power", DEFAULTS.power), { min: 0, max: 1 }));
  if (needs.includes("beta_alpha_ratio")) pair.append(numberField("beta_alpha_ratio", "β/α oranı", val("beta_alpha_ratio", DEFAULTS.beta_alpha_ratio), { min: 0 }));
  if (pair.children.length) box.append(pair);
  if (needs.includes("sizes")) {
    const sizes = document.createElement("div");
    sizes.className = test.sizes.length > 1 ? "row2" : "";
    for (const k of test.sizes) {
      sizes.append(numberField(k, SIZE_LABEL[k], val(k, DEFAULTS[k]), { step: 1, min: 2, inputMode: "numeric" }));
    }
    box.append(sizes);
  }
}

function buildRequest() {
  const test = currentTest();
  const analysis = $("analysis").value;
  const get = (k) => $(`f-${k}`);
  const num = (k, integer) => {
    const el = get(k);
    const text = el.value.trim().replace(",", ".");   // "0,95" and "0.95" both mean 0.95
    const v = /^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(text) ? Number(text) : NaN;
    const bad = text === "" || !Number.isFinite(v) || (integer && !Number.isInteger(v));
    el.setAttribute("aria-invalid", String(bad));
    if (bad) throw new Error(`${el.labels[0].textContent} geçerli bir sayı olmalı`);
    return v;
  };
  const options = {};
  for (const opt of test.options) if (get(opt)) options[opt] = num(opt, opt !== "ratio");
  const params = {};
  for (const k of NEEDS[analysis]) {
    if (k === "sizes") params.sizes = Object.fromEntries(test.sizes.map((s) => [s, num(s, true)]));
    else params[k] = num(k, false);
  }
  return { test: test.name, analysis, options, params };
}

// ---------- results ----------

const fmt = (v) => (Number.isInteger(v) ? String(v) : Number(v).toFixed(7));

function outputRows(req, out) {
  const isF = "df_num" in out;
  const given = new Set(Object.keys(req.params).filter((k) => k !== "sizes"));
  const sizeGiven = "sizes" in req.params;
  const rows = [];
  const add = (label, v, input = false) => v !== undefined && rows.push({ label, value: fmt(v), input });
  if (out.tails) add(OPTION_LABEL.tails, out.tails, true);
  for (const k of ["groups", "predictors", "tested"]) add(OPTION_LABEL[k], out[k], true);
  add(EFFECT_LABEL[testOf(req).effect_size], out.effect_size, given.has("effect_size"));
  add("α hata olasılığı", out.alpha, given.has("alpha"));
  if (given.has("power")) add("İstenen güç (1−β)", req.params.power, true);
  if (out.beta_alpha_ratio !== undefined) add("β/α oranı", out.beta_alpha_ratio, true);
  add(isF ? "Merkezdışılık parametresi λ" : "Merkezdışılık parametresi δ", out.noncentrality);
  add(isF ? "Kritik F" : "Kritik t", out.critical_value);
  if (isF) add("Pay sd", out.df_num);
  add(isF ? "Payda sd" : "Sd", out.df);
  for (const [k, v] of Object.entries(out.sizes)) add(SIZE_LABEL[k], v, sizeGiven);
  if (Object.keys(out.sizes).length > 1) add("Toplam örneklem büyüklüğü", out.n_total, sizeGiven);
  add(req.analysis === "a_priori" ? "Gerçekleşen güç" : "Güç (1−β)", out.power);
  return rows;
}

function headline(req, out) {
  const m = (label, value) => `<div class="metric"><div class="value">${value}</div><div class="label">${label}</div></div>`;
  switch (req.analysis) {
    case "a_priori": return m("toplam örneklem", out.n_total) + m("gerçekleşen güç", out.power.toFixed(4));
    case "post_hoc": return m("güç (1−β)", out.power.toFixed(4)) + m("toplam örneklem", out.n_total);
    case "sensitivity": return m(EFFECT_LABEL[testOf(req).effect_size].toLowerCase(), out.effect_size.toFixed(4));
    case "criterion": return m("gerekli α", out.alpha.toPrecision(4));
    default: return m("α", out.alpha.toPrecision(4)) + m("güç (1−β)", out.power.toFixed(4));
  }
}

function protocolText(req, out) {
  const test = testOf(req);
  const rows = outputRows(req, out);
  const line = (r) => `\t${r.label.padEnd(34)}= ${r.value}`;
  return [
    `Noncentra — ${test.title}`,
    `Analiz:\t${ANALYSIS_NAME[req.analysis]}`,
    "Girdi:", ...rows.filter((r) => r.input).map(line),
    "Çıktı:", ...rows.filter((r) => !r.input).map(line),
  ].join("\n");
}

const pct = (v) => `%${(v * 100).toFixed(1).replace(/\.0$/, "")}`;

// One plain-language sentence that says what the result means.
function summaryText(req, out) {
  const e = testOf(req).effect_size.replace("f2", "f²");
  const sizes = Object.values(out.sizes);
  const n = sizes.length > 1 ? `toplam ${out.n_total} (${sizes.join(" + ")})` : `${out.n_total}`;
  const tails = out.tails ? (out.tails === 2 ? "İki yönlü testte, " : "Tek yönlü testte, ") : "";
  switch (req.analysis) {
    case "a_priori":
      return `${tails}${e} = ${out.effect_size} büyüklüğündeki bir etkiyi α = ${out.alpha} ile en az ${pct(req.params.power)} güçle saptamak için ${n} katılımcı gerekir (gerçekleşen güç ${pct(out.power)}).`;
    case "post_hoc":
      return `${tails}${n} katılımcı ve α = ${out.alpha} ile ${e} = ${out.effect_size} büyüklüğündeki bir etkiyi saptama gücü ${pct(out.power)}.`;
    case "sensitivity":
      return `${tails}${n} katılımcı, α = ${out.alpha} ve ${pct(out.power)} güçle saptanabilecek en küçük etki ${e} = ${out.effect_size.toFixed(4)}.`;
    case "criterion":
      return `${tails}${n} katılımcıyla ${e} = ${out.effect_size} etkisine ${pct(out.power)} güç için α = ${out.alpha.toPrecision(4)} olmalı.`;
    default:
      return `${tails}β/α = ${out.beta_alpha_ratio} oranında α = ${out.alpha.toPrecision(4)} ve güç = ${pct(out.power)} olur (${n} katılımcı, ${e} = ${out.effect_size}).`;
  }
}

function showResult(req, doc) {
  const out = doc.output;
  const rows = outputRows(req, out);
  const table = (list) => list.map((r) => `<tr><td>${r.label}</td><td>${r.value}</td></tr>`).join("");
  $("summary").textContent = summaryText(req, out);
  $("summary").classList.remove("muted");
  $("headline").innerHTML = headline(req, out);
  $("in-table").innerHTML = table(rows.filter((r) => r.input));
  $("out-table").innerHTML = table(rows.filter((r) => !r.input));
  $("protocol").textContent = protocolText(req, out);
  for (const id of ["copy-protocol", "download-json", "share"]) $(id).disabled = false;
}

function showError(message) {
  const el = $("error");
  el.textContent = message;
  el.hidden = !message;
}

// ---------- chart ----------

function minBase(req) {
  const o = req.options;
  if (req.test === "f.anova_oneway") return o.groups + 1;
  if (req.test.startsWith("f.regression")) return o.predictors + 2;
  return 2;
}

async function drawCurve(req, out) {
  const effect = out.effect_size;
  const conv = CONVENTIONS[testOf(req).effect_size];
  const effects = [effect, ...conv.filter((c) => Math.abs(c - effect) > 1e-9)].slice(0, 3).sort((a, b) => a - b);
  const base = out.sizes.n1 ?? out.sizes.n;
  const lo = minBase(req);
  const hi = Math.max(Math.ceil(base * 2), lo + 20);
  const options = { ...req.options };
  delete options.ratio;
  if (req.test === "t.two_sample" && req.options.ratio) options.ratio = req.options.ratio;
  const doc = await state.engine.call("curve", {
    test: req.test, options, effect_sizes: effects, alpha: out.alpha, n_from: lo, n_to: hi, points: 60,
  });
  if (doc.error) {
    // Error messages can echo user input (e.g. a test name from the URL), so never as HTML.
    const span = Object.assign(document.createElement("span"), { className: "muted", textContent: doc.error.message });
    $("chart").replaceChildren(span);
    $("legend").replaceChildren();
    return;
  }
  renderChart(doc, out, req.params.power ?? out.power, effect);
}

function niceStep(range, target) {
  const raw = range / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  return [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw);
}

function renderChart(doc, out, target, effect) {
  const W = 640, H = 300, L = 44, R = 16, T = 12, B = 34;
  const all = doc.series.flatMap((s) => s.points);
  const xMin = Math.min(...all.map((p) => p.n_total)), xMax = Math.max(...all.map((p) => p.n_total));
  const x = (v) => L + ((v - xMin) / (xMax - xMin || 1)) * (W - L - R);
  const y = (v) => T + (1 - v) * (H - T - B);
  const colors = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Güç eğrisi">`;
  for (let v = 0; v <= 1.0001; v += 0.2) {
    svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/>`;
    svg += `<text class="tick" x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(1)}</text>`;
  }
  const step = niceStep(xMax - xMin, 6);
  for (let v = Math.ceil(xMin / step) * step; v <= xMax; v += step) {
    svg += `<line class="axis" x1="${x(v)}" x2="${x(v)}" y1="${H - B}" y2="${H - B + 4}"/>`;
    svg += `<text class="tick" x="${x(v)}" y="${H - B + 18}" text-anchor="middle">${v}</text>`;
  }
  svg += `<text class="tick" x="${(L + W - R) / 2}" y="${H - 2}" text-anchor="middle">toplam örneklem büyüklüğü</text>`;
  svg += `<line class="axis" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>`;
  svg += `<line class="target" x1="${L}" x2="${W - R}" y1="${y(target)}" y2="${y(target)}"/>`;
  doc.series.forEach((s, i) => {
    const d = s.points.map((p, j) => `${j ? "L" : "M"}${x(p.n_total).toFixed(1)},${y(p.power).toFixed(1)}`).join("");
    const width = Math.abs(s.effect_size - effect) < 1e-9 ? 3 : 1.8;
    svg += `<path d="${d}" fill="none" stroke="${colors[i]}" stroke-width="${width}" stroke-linejoin="round"/>`;
  });
  const idx = doc.series.findIndex((s) => Math.abs(s.effect_size - effect) < 1e-9);
  if (out.n_total >= xMin && out.n_total <= xMax) {
    svg += `<circle class="marker" cx="${x(out.n_total)}" cy="${y(out.power)}" r="5" stroke="${colors[idx]}">
      <title>N = ${out.n_total}, güç = ${out.power.toFixed(4)}</title></circle>`;
  }
  $("chart").innerHTML = svg + "</svg>";
  const name = EFFECT_LABEL[currentTest().effect_size].replace("Etki büyüklüğü ", "");
  $("legend").innerHTML = doc.series
    .map((s, i) => `<span><i style="background:${colors[i]}"></i>${name} = ${s.effect_size}</span>`).join("")
    + `<span><i style="background:var(--target)"></i>hedef güç ${Number(target).toFixed(2)}</span>`;
}

// ---------- distribution plot (G*Power's "Central and noncentral distributions") ----------

async function drawDistribution(req) {
  const doc = await state.engine.call("distribution", req);
  if (doc.error) {
    const span = Object.assign(document.createElement("span"), { className: "muted", textContent: doc.error.message });
    $("dist").replaceChildren(span);
    $("dist-legend").replaceChildren();
    return;
  }
  renderDistribution(doc);
}

function renderDistribution(doc) {
  const W = 640, H = 300, L = 40, R = 16, T = 30, B = 30;
  const xs = doc.x, n = xs.length;
  const xMin = xs[0], xMax = xs[n - 1];
  // With df_num = 1 the F density goes to infinity at 0; then scale y to the rest of
  // the curve (the spike is clipped) instead of flattening everything else.
  const peak = (from, to) => Math.max(...[...doc.central.slice(from, to), ...doc.noncentral.slice(from, to)]
    .filter((v) => v !== null));
  const edge = Math.ceil(n * 0.02);
  const rest = peak(edge, n);
  const yMax = (doc.family === "F" && peak(0, edge) > 3 * rest ? rest : peak(0, n)) * 1.08;
  const px = (v) => L + ((v - xMin) / (xMax - xMin)) * (W - L - R);
  const py = (v) => T + (1 - Math.min(v, yMax) / yMax) * (H - T - B);
  const valAt = (series, v) => {
    const i = Math.min(n - 2, Math.max(0, Math.floor(((v - xMin) / (xMax - xMin)) * (n - 1))));
    const a = series[i] ?? 0, b = series[i + 1] ?? 0, t = (v - xs[i]) / (xs[i + 1] - xs[i]);
    return a + (b - a) * Math.min(1, Math.max(0, t));
  };
  const line = (series) => {
    let d = "", pen = false;
    series.forEach((v, i) => {
      if (v === null) { pen = false; return; }
      d += `${pen ? "L" : "M"}${px(xs[i]).toFixed(1)},${py(v).toFixed(1)}`;
      pen = true;
    });
    return d;
  };
  const area = (series, [a, b]) => {
    a = Math.max(a, xMin); b = Math.min(b, xMax);
    if (b <= a) return "";
    const pts = [[a, valAt(series, a)], ...xs.map((x, i) => [x, series[i]]).filter(([x, v]) => x > a && x < b && v !== null), [b, valAt(series, b)]];
    return `M${px(a)},${py(0)}` + pts.map(([x, v]) => `L${px(x).toFixed(1)},${py(v).toFixed(1)}`).join("") + `L${px(b)},${py(0)}Z`;
  };

  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Merkezi ve merkezi olmayan dağılımlar">
    <defs><clipPath id="dist-clip"><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/></clipPath>
      <marker id="arrow-h0" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="var(--h0)"/></marker>
      <marker id="arrow-h1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0L10,5L0,10z" fill="var(--h1)"/></marker></defs>`;
  const yStep = niceStep(yMax, 4);
  for (let v = 0; v <= yMax; v += yStep) {
    svg += `<line class="grid" x1="${L}" x2="${W - R}" y1="${py(v)}" y2="${py(v)}"/>`;
    svg += `<text class="tick" x="${L - 6}" y="${py(v) + 4}" text-anchor="end">${+v.toFixed(3)}</text>`;
  }
  const xStep = niceStep(xMax - xMin, 8);
  for (let v = Math.ceil(xMin / xStep) * xStep; v <= xMax + 1e-9; v += xStep) {
    svg += `<line class="axis" x1="${px(v)}" x2="${px(v)}" y1="${H - B}" y2="${H - B + 4}"/>`;
    svg += `<text class="tick" x="${px(v)}" y="${H - B + 17}" text-anchor="middle">${+v.toFixed(2)}</text>`;
  }
  svg += `<line class="axis" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/>`;
  svg += `<g clip-path="url(#dist-clip)">`;
  svg += `<path class="beta-area" d="${area(doc.noncentral, doc.beta_region)}"/>`;
  for (const r of doc.alpha_regions) svg += `<path class="alpha-area" d="${area(doc.central, r)}"/>`;
  svg += `<path class="h0" d="${line(doc.central)}"/><path class="h1" d="${line(doc.noncentral)}"/>`;
  for (const c of doc.critical) svg += `<line class="crit" x1="${px(c)}" x2="${px(c)}" y1="${T}" y2="${H - B}"/>`;
  svg += `</g>`;

  const out = doc.result.output;
  const crit = Math.max(...doc.critical);
  svg += `<text class="title" x="${(L + W - R) / 2}" y="16" text-anchor="middle">critical ${doc.statistic} = ${crit.toFixed(5)}</text>`;
  // Label each shaded area: inside it when it is tall enough to hold the text,
  // otherwise from outside with an arrow pointing into it (as G*Power does for α/2).
  const range = xMax - xMin;
  const annotate = (text, kind, series, [a, b]) => {
    a = Math.max(a, xMin); b = Math.min(b, xMax);
    if (b <= a) return "";
    // Areas are tallest where they touch a critical value; start there, pointing inward.
    const touches = (x) => doc.critical.some((c) => Math.abs(c - x) < 1e-9);
    const edge = touches(a) && touches(b)
      ? (valAt(series, a) > valAt(series, b) ? a : b)
      : (touches(a) ? a : b);
    const dir = edge === a ? 1 : -1;  // +1: area extends to the right of the critical value
    const height = (x) => py(0) - py(valAt(series, x));
    const inside = edge + dir * Math.min(range * 0.07, (b - a) / 2);
    if (height(inside) >= 34) {
      return `<text class="label-${kind}" x="${px(inside)}" y="${py(valAt(series, inside) / 2) + 6}" text-anchor="middle">${text}</text>`;
    }
    const tx = edge + dir * Math.min(range * 0.025, (b - a) / 2);
    const ty = py(0) - Math.max(height(tx) / 2, 2);
    const lx = px(tx) + dir * 38, ly = Math.max(T + 16, ty - 48);
    return `<line class="lead-${kind}" x1="${lx - dir * 2}" y1="${ly + 5}" x2="${px(tx)}" y2="${ty}" marker-end="url(#arrow-${kind})"/>`
      + `<text class="label-${kind}" x="${lx}" y="${ly}" text-anchor="${dir > 0 ? "start" : "end"}">${text}</text>`;
  };
  svg += annotate("β", "h1", doc.noncentral, doc.beta_region);
  for (const r of doc.alpha_regions) svg += annotate(doc.tails === 2 ? "α/2" : "α", "h0", doc.central, r);
  $("dist").innerHTML = svg + "</svg>";

  $("dist-legend").innerHTML =
    `<span><i style="background:var(--h0)"></i>H0: merkezi ${doc.statistic}</span>` +
    `<span><i style="background:var(--h1)"></i>H1: merkezi olmayan ${doc.statistic} (${doc.family === "F" ? "λ" : "δ"} = ${out.noncentrality.toFixed(4)})</span>` +
    `<span><i style="background:var(--crit)"></i>kritik değer</span>` +
    `<span>β = ${out.beta.toFixed(4)} · güç = ${out.power.toFixed(4)}</span>`;
}

// ---------- report ----------

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Light theme and chart styles for the standalone report (it must not depend on style.css).
const REPORT_CSS = `
:root { --ink:#0F172A; --muted:#64748B; --line:#E2E8F0; --panel:#fff; --accent:#2563EB; --accent-soft:#EFF6FF;
  --axis:#CBD5E1; --grid:#F1F5F9;
  --series-1:#2563EB; --series-2:#D97706; --series-3:#0D9488; --target:#DC2626; --h0:#EF4444; --h1:#2563EB; --crit:#10B981; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--ink); font: 14px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 28px 32px; }
header { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; border-bottom: 2px solid var(--accent); padding-bottom: 12px; margin-bottom: 18px; }
h1 { margin: 0; font-size: 22px; } h2 { font-size: 15px; margin: 22px 0 8px; } .muted { color: var(--muted); }
.meta { text-align: right; font-size: 12px; color: var(--muted); }
.summary { font-size: 15px; background: var(--accent-soft); border-radius: 10px; padding: 12px 16px; margin: 0 0 12px; }
.metrics { display: flex; gap: 12px; flex-wrap: wrap; }
.metric { border: 1px solid var(--line); border-radius: 10px; padding: 8px 14px; min-width: 150px; }
.metric .value { font-size: 22px; font-weight: 650; } .metric .label { font-size: 12px; color: var(--muted); }
.cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
td { padding: 5px 0; border-top: 1px solid var(--line); vertical-align: top; } td:last-child { text-align: right; font-family: ui-monospace, Consolas, monospace; }
table.text td:first-child { width: 42%; color: var(--muted); } table.text td:last-child { text-align: left; font-family: inherit; padding-left: 10px; }
.charts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
figure { margin: 0; border: 1px solid var(--line); border-radius: 10px; padding: 12px; break-inside: avoid; }
figcaption { font-weight: 600; margin-bottom: 6px; } svg { width: 100%; height: auto; display: block; }
.axis { stroke: var(--axis); } .tick { fill: var(--muted); font-size: 11px; } .grid { stroke: var(--grid); }
.target { stroke: var(--target); stroke-dasharray: 5 4; } .marker { fill: #fff; stroke-width: 2.5; }
.h0 { stroke: var(--h0); fill: none; stroke-width: 2.2; } .h1 { stroke: var(--h1); fill: none; stroke-width: 2.2; stroke-dasharray: 7 5; }
.alpha-area { fill: var(--h0); opacity: .18; } .beta-area { fill: var(--h1); opacity: .2; } .crit { stroke: var(--crit); stroke-width: 2; }
.label-h0 { fill: var(--h0); font-size: 18px; font-style: italic; } .label-h1 { fill: var(--h1); font-size: 18px; font-style: italic; }
.label-h0, .label-h1 { paint-order: stroke; stroke: #fff; stroke-width: 4px; stroke-linejoin: round; }
.lead-h0 { stroke: var(--h0); stroke-width: 1.4; } .lead-h1 { stroke: var(--h1); stroke-width: 1.4; }
.title { fill: var(--ink); font-size: 13px; }
.legend { display: flex; flex-wrap: wrap; gap: 4px 12px; font-size: 11px; color: var(--muted); margin-top: 6px; }
.legend i { display: inline-block; width: 14px; height: 3px; border-radius: 2px; vertical-align: middle; margin-right: 5px; }
pre { white-space: pre-wrap; font-size: 12px; background: #f6f8fa; border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
footer { margin-top: 24px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 10px; }
@media (max-width: 760px) { .cols, .charts { grid-template-columns: 1fr; } main { padding: 16px; } }
@media print { @page { size: A4; margin: 14mm; } main { padding: 0; max-width: none; } h2 { break-after: avoid; } }
`;

function reportHtml() {
  const req = state.lastRequest, doc = state.last, out = doc.output, test = testOf(req);
  const rows = outputRows(req, out);
  const kv = (list, cls = "") => `<table class="${cls}">${list.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}</table>`;
  const settings = [
    ["Test", test.title],
    ["Analiz türü", $("analysis").querySelector(`option[value="${req.analysis}"]`).textContent],
  ];
  if (req.options.tails) settings.push([OPTION_LABEL.tails, req.options.tails === 2 ? "İki yönlü" : "Tek yönlü"]);
  for (const k of ["ratio", "groups", "predictors", "tested"]) {
    if (req.options[k] !== undefined) settings.push([OPTION_LABEL[k], req.options[k]]);
  }
  settings.push(["Hesaplama motoru", $("engine").value === "api" ? "Sunucu (FastAPI)" : "Tarayıcı (Pyodide)"]);
  const now = new Date();
  // Chart markup and legends are generated by this page from numbers and fixed labels.
  return `<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Noncentra raporu – ${esc(test.title)}</title><style>${REPORT_CSS}</style></head><body><main>
<header><div><h1>Güç analizi raporu</h1><div class="muted">${esc(test.title)} · ${esc(ANALYSIS_NAME[req.analysis])}</div></div>
<div class="meta">Noncentra<br>${esc(now.toLocaleString("tr-TR"))}</div></header>
<p class="summary">${esc(summaryText(req, out))}</p>
<div class="metrics">${headline(req, out)}</div>
<div class="cols">
  <section><h2>Ayarlar</h2>${kv(settings, "text")}</section>
  <section><h2>Girdiler</h2>${kv(rows.filter((r) => r.input).map((r) => [r.label, r.value]))}</section>
  <section><h2>Sonuçlar</h2>${kv(rows.filter((r) => !r.input).map((r) => [r.label, r.value]))}</section>
</div>
<h2>Grafikler</h2>
<div class="charts">
  <figure><figcaption>Merkezi ve merkezi olmayan dağılımlar</figcaption>${$("dist").innerHTML}<div class="legend">${$("dist-legend").innerHTML}</div></figure>
  <figure><figcaption>Güç eğrisi</figcaption>${$("chart").innerHTML}<div class="legend">${$("legend").innerHTML}</div></figure>
</div>
<h2>Protokol</h2><pre>${esc(protocolText(req, out))}</pre>
<footer>Noncentra ile hesaplandı. Formüller yayınlanmış kaynaklardan (Faul vd. 2007, 2009; Cohen 1988);
sonuçlar G*Power 3.1.9.7 çıktılarıyla doğrulandı. Paylaşım bağlantısı: ${esc(location.href)}</footer>
</main></body></html>`;
}

function reportFileName() {
  const req = state.lastRequest;
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
  return `noncentra-rapor-${req.test}-${req.analysis}-${stamp}.html`;
}

function downloadReport() {
  const blob = new Blob([reportHtml()], { type: "text/html;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: reportFileName() });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// Print the report from a hidden frame; the browser's print dialog offers "Save as PDF".
function printReport() {
  const frame = Object.assign(document.createElement("iframe"), { title: "rapor" });
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  frame.srcdoc = reportHtml();
  frame.onload = () => {
    frame.contentWindow.focus();
    frame.contentWindow.print();
    setTimeout(() => frame.remove(), 60_000);
  };
  document.body.append(frame);
}

// ---------- URL state ----------

function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const values = Object.fromEntries([...p].filter(([k]) => !["test", "analysis"].includes(k)));
  return { test: p.get("test"), analysis: p.get("analysis"), values };
}

function applyHash() {
  const h = readHash();
  if (!h.test || !state.tests.some((t) => t.name === h.test)) return false;
  if (h.analysis in NEEDS) $("analysis").value = h.analysis;
  $("test").value = h.test;
  renderFields(h.values);
  return true;
}

function writeHash(req) {
  const p = new URLSearchParams({ test: req.test, analysis: req.analysis });
  for (const [k, v] of Object.entries(req.options)) p.set(k, v);
  for (const [k, v] of Object.entries(req.params)) {
    if (k === "sizes") for (const [s, n] of Object.entries(v)) p.set(s, n);
    else p.set(k, v);
  }
  history.replaceState(null, "", `#${p}`);
}

// ---------- wiring ----------

async function calculate(ev) {
  ev?.preventDefault();
  showError("");
  let req;
  try {
    req = buildRequest();
  } catch (err) {
    showError(err.message);
    return;
  }
  $("calc").disabled = true;
  try {
    const doc = await state.engine.call("analyze", req);
    if (doc.error) {
      showError(`${doc.error.message} (${doc.error.code})`);
      return;
    }
    state.last = doc;
    state.lastRequest = req;
    writeHash(req);
    showResult(req, doc);
    for (const id of ["download-report", "print-report"]) $(id).disabled = true;
    await Promise.all([drawDistribution(req), drawCurve(req, doc.output)]);
    // The report embeds both charts, so it becomes available once they are drawn.
    for (const id of ["download-report", "print-report"]) $(id).disabled = false;
  } catch (err) {
    showError(err.message);
  } finally {
    $("calc").disabled = false;
  }
}

function flash(button, text) {
  const old = button.textContent;
  button.textContent = text;
  setTimeout(() => { button.textContent = old; }, 1500);
}

async function main() {
  $("form").addEventListener("submit", calculate);
  // writeHash uses replaceState (no event); this fires for pasted or edited links only.
  window.addEventListener("hashchange", () => { if (state.engine && applyHash()) calculate(); });
  $("test").addEventListener("change", () => renderFields());
  $("analysis").addEventListener("change", () => renderFields());
  $("copy-protocol").onclick = async (e) => {
    await navigator.clipboard.writeText($("protocol").textContent);
    flash(e.target, "Kopyalandı");
  };
  $("download-json").onclick = () => {
    const blob = new Blob([JSON.stringify(state.last, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(blob), download: `noncentra-${state.last.test}-${state.last.analysis}.json`,
    });
    a.click();
    URL.revokeObjectURL(a.href);
  };
  $("download-report").onclick = downloadReport;
  $("print-report").onclick = printReport;
  $("share").onclick = async (e) => {
    await navigator.clipboard.writeText(location.href);
    flash(e.target, "Bağlantı kopyalandı");
  };

  const hasApi = await apiAvailable();
  const sel = $("engine");
  if (!hasApi) {
    sel.querySelector('option[value="api"]').disabled = true;
  } else {
    $("api-docs").hidden = false;
  }
  sel.value = hasApi ? "api" : "pyodide";
  sel.addEventListener("change", () => useEngine(sel.value));
  await useEngine(sel.value);
  // Calculate right away (from the link, or with the default values) so the
  // results and both plots are visible without pressing the button first.
  if (state.engine) {
    applyHash();
    calculate();
  }
}

main();

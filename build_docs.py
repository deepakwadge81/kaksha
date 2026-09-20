"""Generate the GitHub Pages replay of the recorded session: docs/index.html.

Reads the same personas.py and demo_fallback.json the app itself uses, so the
published page cannot drift from the real simulation. Self-contained output —
no build step, no external assets, no API key.

    python build_docs.py
"""
import json
import pathlib

from personas import CHILDREN, LESSON

ROOT = pathlib.Path(__file__).resolve().parent

demo = json.loads((ROOT / "demo_fallback.json").read_text(encoding="utf-8"))

payload = {
    "lesson": LESSON,
    "children": [
        {k: c[k] for k in ("id", "name", "avatar", "aser_band", "public_profile",
                           "hidden_level", "hidden_misconception")}
        for c in CHILDREN
    ],
    "transcript": demo["transcript"],
    "report": demo["report"],
}

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KAKSHA — a flight simulator for teachers</title>
<meta name="description" content="Claude plays five Grade 3 children with hidden learning levels and hidden misconceptions. Teach blind, then the X-ray turns on.">
<style>
:root{
  --bg:#faf9f7; --panel:#fff; --ink:#1b1a18; --muted:#6a6560; --line:#e3ddd6;
  --engaged:#2e9e5b; --drifting:#c98a12; --lost:#b03636; --xray:#7b5cd6;
  --accent:#1b1a18;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#15140f; --panel:#1e1c17; --ink:#f2efe9; --muted:#a09a91; --line:#33302a;
    --engaged:#4cc97c; --drifting:#e0a734; --lost:#e06767; --xray:#a68bf0;
    --accent:#f2efe9;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:860px;margin:0 auto;padding:0 20px;padding-block:44px 64px}
h1{font-size:clamp(2rem,6vw,2.9rem);line-height:1.08;margin:0 0 .3em;letter-spacing:-.02em}
h2{font-size:1.32rem;margin:2.6em 0 .7em;letter-spacing:-.01em}
h3{font-size:1rem;margin:1.6em 0 .4em}
p{margin:0 0 1em}
a{color:inherit;text-decoration:underline;text-underline-offset:2px;
  text-decoration-color:color-mix(in srgb,var(--ink) 35%,transparent)}
.lede{font-size:1.12rem;color:var(--muted);max-width:62ch}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:1.4em 0 0}
.badge{font-size:.76rem;border:1px solid var(--line);border-radius:999px;
  padding:.3em .8em;color:var(--muted);background:var(--panel)}
.rule{height:1px;background:var(--line);border:0;margin:2.6em 0}

.kids{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:1.2em 0}
@media (max-width:640px){.kids{grid-template-columns:repeat(2,1fr)}}
.kid{border:1px solid var(--line);border-radius:14px;padding:.7rem .55rem;
  text-align:center;background:var(--panel);transition:border-color .25s,opacity .25s}
.kid .face{font-size:1.85rem;line-height:1.2}
.kid .nm{font-weight:650;margin-top:.15rem;font-size:.95rem}
.kid .bd{font-size:.68rem;color:var(--muted);margin-top:.1rem}
.kid .st{font-size:.63rem;text-transform:uppercase;letter-spacing:.06em;
  font-weight:700;margin-top:.45rem}
.kid[data-eng="engaged"]{border-color:color-mix(in srgb,var(--engaged) 55%,var(--line))}
.kid[data-eng="engaged"] .st{color:var(--engaged)}
.kid[data-eng="drifting"]{border-color:color-mix(in srgb,var(--drifting) 55%,var(--line))}
.kid[data-eng="drifting"] .st{color:var(--drifting)}
.kid[data-eng="lost"]{border-color:color-mix(in srgb,var(--lost) 55%,var(--line));opacity:.66}
.kid[data-eng="lost"] .st{color:var(--lost)}

.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:1.4em 0}
button{font:inherit;font-size:.92rem;font-weight:600;cursor:pointer;
  border:1px solid var(--line);border-radius:10px;padding:.62em 1.1em;
  background:var(--panel);color:var(--ink)}
button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
button:disabled{opacity:.42;cursor:not-allowed}
.progress{font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums}

.turn{margin:1.5em 0}
.tline{background:color-mix(in srgb,var(--ink) 6%,transparent);
  border-left:3px solid color-mix(in srgb,var(--ink) 42%,transparent);
  padding:.6rem .85rem;border-radius:0 8px 8px 0;margin-bottom:.7em}
.tline b{letter-spacing:.02em}
.resp{padding:.15rem 0 .15rem .3rem;margin-bottom:.5em}
.says{margin:0}
.says .who{font-weight:650}
.beh{font-size:.85rem;color:var(--muted);font-style:italic}
.silent{font-size:.87rem;color:var(--muted);font-style:italic}
.xr{display:none;font-size:.85rem;font-style:italic;margin-top:.25rem;
  padding:.25rem .6rem;border-left:2px solid var(--xray);border-radius:0 6px 6px 0;
  background:color-mix(in srgb,var(--xray) 12%,transparent)}
body.xray .xr{display:block}
.note{font-size:.88rem;color:var(--muted);margin:.5em 0 0}

.reveal{border:1px solid color-mix(in srgb,var(--xray) 45%,var(--line));
  background:color-mix(in srgb,var(--xray) 9%,var(--panel));
  border-radius:14px;padding:1rem 1.1rem;margin:1.6em 0}
.reveal h3{margin-top:0}
.hidden{display:none}

.scores{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:1.2em 0}
@media (max-width:640px){.scores{grid-template-columns:1fr}}
.score{border:1px solid var(--line);border-radius:12px;padding:.8rem .9rem;background:var(--panel)}
.score .v{font-size:1.9rem;font-weight:700;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.score .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.meter{height:5px;border-radius:99px;background:color-mix(in srgb,var(--ink) 12%,transparent);
  margin-top:.5rem;overflow:hidden}
.meter i{display:block;height:100%;border-radius:99px;background:var(--lost)}
.headline{font-size:1.12rem;font-weight:600;margin:.2em 0 1em;line-height:1.45}

table{width:100%;border-collapse:collapse;font-size:.9rem;margin:.6em 0 1em}
.tw{overflow-x:auto}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:700}
td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
ul{margin:.3em 0 1em;padding-left:1.15em}
li{margin-bottom:.4em}
.tag{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
  padding:.16em .5em;border-radius:5px;white-space:nowrap}
.tag.yes{color:var(--engaged);background:color-mix(in srgb,var(--engaged) 15%,transparent)}
.tag.no{color:var(--lost);background:color-mix(in srgb,var(--lost) 15%,transparent)}
footer{margin-top:3.4em;padding-top:1.4em;border-top:1px solid var(--line);
  font-size:.87rem;color:var(--muted)}
</style>
</head>
<body>
<div class="wrap">

<h1>KAKSHA <span aria-hidden="true">🪑</span></h1>
<p class="lede"><strong>Five children. Each has a hidden learning level and a hidden
misconception.</strong> You get six turns. You teach blind — then the X-ray turns on and
you see what you walked past.</p>
<div class="badges">
  <span class="badge">Recorded session — no API key needed</span>
  <span class="badge">Grade 3 · two-digit subtraction</span>
  <span class="badge"><a href="play/">Teach a live class yourself →</a></span>
  <span class="badge"><a href="https://github.com/deepakwadge81/kaksha">Source on GitHub</a></span>
</div>

<hr class="rule">

<p>A trainee teacher can fail this classroom a hundred times before ever meeting a real
child. Reading levels use the <strong>ASER 2024</strong> bands, and the spread across
these five is the documented finding that learning levels inside one nominal grade span
about <strong>seven grade-equivalents</strong>. The maths bugs are the classic documented
subtraction errors: smaller-from-larger, and borrowing across a zero.</p>
<p class="note">This page replays one recorded lesson so you can see the whole arc with
no setup and no API key. To teach a class of your own — where Claude improvises all five
children in response to whatever you actually say — <a href="play/">open the live
version</a> (needs your own Anthropic key).</p>

<h2>The class</h2>
<div class="kids" id="kids"></div>
<p class="note" id="pubnote"></p>

<h2>The lesson</h2>
<div class="controls">
  <button class="primary" id="next">Teach the next turn →</button>
  <button id="skip">Skip to the end</button>
  <span class="progress" id="prog"></span>
</div>
<div id="turns"></div>

<div id="endzone" class="hidden">
  <div class="reveal">
    <h3>🔍 X-ray on</h3>
    <p style="margin:0">The lesson is replayed above with what each child was actually
    thinking — the thing a real teacher never gets to see. Their hidden profiles are
    below, and the coaching report follows.</p>
  </div>

  <h2>What was hidden from you</h2>
  <div class="tw"><table id="hidden-table"></table></div>

  <h2>Coaching report</h2>
  <p class="headline" id="headline"></p>
  <div class="scores" id="scores"></div>
  <h3>Attention</h3>
  <div class="tw"><table id="attention"></table></div>
  <h3>Misconceptions</h3>
  <div class="tw"><table id="misconceptions"></table></div>
  <h3>Moments</h3>
  <div id="moments"></div>
  <h3>Next time</h3>
  <ul id="nexttime"></ul>
</div>

<footer>
  <p><strong>KAKSHA</strong> — built for the AI for Foundational Learning hackathon
  (ShikshaNext × Anthropic × Central Square Foundation), Theme 3: Teacher Support &amp;
  Training.</p>
  <p>No real child data, no recording, no consent problem — the children are calibrated
  to published distributions, not observed from any classroom. It's a practice
  environment, not an evidence claim.</p>
  <p><a href="https://github.com/deepakwadge81/kaksha">Source, tests and the live
  Streamlit app →</a></p>
</footer>

</div>

<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const byId = Object.fromEntries(D.children.map(c => [c.id, c]));
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,
  m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));

// Pair the flat transcript into [teacher line, class response] turns.
const turns = [];
for (let i = 0; i < D.transcript.length; i++) {
  if (D.transcript[i].role === "teacher") {
    const next = D.transcript[i + 1];
    turns.push({ line: D.transcript[i].content,
                 responses: (next && next.role === "class") ? next.content.responses : [],
                 note: (next && next.role === "class") ? next.content.class_note : null });
  }
}

const kidsEl = document.getElementById("kids");
function paintKids(state) {
  kidsEl.innerHTML = D.children.map(c => `
    <div class="kid" data-eng="${esc(state[c.id] || "engaged")}">
      <div class="face" aria-hidden="true">${c.avatar}</div>
      <div class="nm">${esc(c.name)}</div>
      <div class="bd">${esc(c.aser_band)}</div>
      <div class="st">● ${esc(state[c.id] || "engaged")}</div>
    </div>`).join("");
}
const engagement = {};
D.children.forEach(c => engagement[c.id] = "engaged");
paintKids(engagement);
document.getElementById("pubnote").textContent =
  "All you are told up front — " +
  D.children.map(c => c.name + ": " + c.public_profile).join("  ·  ");

let shown = 0;
const turnsEl = document.getElementById("turns");
const progEl = document.getElementById("prog");
const nextBtn = document.getElementById("next");
const skipBtn = document.getElementById("skip");

function renderTurn(t, i) {
  const rows = t.responses.map(r => {
    const c = byId[r.child_id] || { name: r.child_id, avatar: "" };
    const body = (r.speaks && r.says)
      ? `<p class="says"><span class="who">${c.avatar} ${esc(c.name)}:</span>
           “${esc(r.says)}”</p>
         ${r.behaviour ? `<div class="beh">${esc(r.behaviour)}</div>` : ""}`
      : `<div class="silent">${c.avatar} ${esc(c.name)} — ${esc(r.behaviour || "no reaction")}</div>`;
    return `<div class="resp">${body}
      ${r.internal_state ? `<div class="xr">thinking: ${esc(r.internal_state)}</div>` : ""}
    </div>`;
  }).join("");
  return `<div class="turn">
    <div class="tline"><b>You</b> — ${esc(t.line)}</div>
    ${rows}
    ${t.note ? `<div class="note">${esc(t.note)}</div>` : ""}
  </div>`;
}

function step() {
  if (shown >= turns.length) return;
  const t = turns[shown];
  turnsEl.insertAdjacentHTML("beforeend", renderTurn(t, shown));
  t.responses.forEach(r => { if (r.engagement) engagement[r.child_id] = r.engagement; });
  paintKids(engagement);
  shown++;
  sync();
}

function sync() {
  progEl.textContent = `Turn ${Math.min(shown, turns.length)} of ${turns.length}`;
  if (shown >= turns.length) {
    nextBtn.disabled = true;
    skipBtn.disabled = true;
    nextBtn.textContent = "Lesson over";
    document.body.classList.add("xray");
    document.getElementById("endzone").classList.remove("hidden");
  }
}

nextBtn.addEventListener("click", step);
skipBtn.addEventListener("click", () => { while (shown < turns.length) step(); });
sync();

// ---- the reveal ----
const hid = D.children.map(c => `<tr>
    <td><strong>${c.avatar} ${esc(c.name)}</strong><br><span class="beh">${esc(c.aser_band)}</span></td>
    <td>${esc(c.hidden_level)}</td>
    <td>${esc(c.hidden_misconception)}</td>
  </tr>`).join("");
document.getElementById("hidden-table").innerHTML =
  `<thead><tr><th>Child</th><th>Actual level</th><th>Hidden misconception</th></tr></thead>
   <tbody>${hid}</tbody>`;

const rep = D.report;
document.getElementById("headline").textContent = rep.headline;

const SCORE_LABELS = {
  attention_equity: "Attention equity",
  question_quality: "Question quality",
  misconception_diagnosis: "Misconception diagnosis",
};
document.getElementById("scores").innerHTML =
  Object.entries(SCORE_LABELS).map(([k, label]) => {
    const v = rep.scores[k];
    return `<div class="score">
      <div class="k">${label}</div>
      <div class="v">${esc(v)}<span style="font-size:.9rem;font-weight:400;color:var(--muted)">/100</span></div>
      <div class="meter"><i style="width:${Math.max(0, Math.min(100, Number(v) || 0))}%"></i></div>
    </div>`;
  }).join("");

document.getElementById("attention").innerHTML =
  `<thead><tr><th>Child</th><th>Addressed</th><th>Spoke</th><th>Note</th></tr></thead><tbody>` +
  rep.attention.map(a => {
    const c = byId[a.child_id] || { name: a.child_id, avatar: "" };
    return `<tr><td><strong>${c.avatar} ${esc(c.name)}</strong></td>
      <td class="n">${esc(a.times_addressed)}</td>
      <td class="n">${esc(a.times_spoke)}</td>
      <td>${esc(a.note)}</td></tr>`;
  }).join("") + `</tbody>`;

document.getElementById("misconceptions").innerHTML =
  `<thead><tr><th>Child</th><th>Surfaced?</th><th>Evidence</th></tr></thead><tbody>` +
  rep.misconceptions.map(m => {
    const c = byId[m.child_id] || { name: m.child_id, avatar: "" };
    return `<tr><td><strong>${c.avatar} ${esc(c.name)}</strong><br>
        <span class="beh">${esc(m.hidden_misconception)}</span></td>
      <td><span class="tag ${m.surfaced ? "yes" : "no"}">${m.surfaced ? "surfaced" : "missed"}</span></td>
      <td>${esc(m.evidence)}</td></tr>`;
  }).join("") + `</tbody>`;

document.getElementById("moments").innerHTML = rep.moments.map(m => `
  <div class="turn">
    <div class="tline"><b>Turn ${esc(m.turn)}</b> — ${esc(m.what_happened)}</div>
    <div class="resp"><p class="says"><span class="who">What to try:</span>
      ${esc(m.what_to_try)}</p></div>
  </div>`).join("");

document.getElementById("nexttime").innerHTML =
  rep.next_time.map(n => `<li>${esc(n)}</li>`).join("");
</script>
</body>
</html>
"""

out = ROOT / "docs"
out.mkdir(exist_ok=True)
html = HTML.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
(out / "index.html").write_text(html, encoding="utf-8")
print("wrote docs/index.html  (%d bytes, %d turns)" % (
    len(html), sum(1 for e in demo["transcript"] if e["role"] == "teacher")))

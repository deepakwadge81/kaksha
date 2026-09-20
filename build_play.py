"""Generate docs/play/index.html — the live, playable browser build.

No backend. The page calls the Claude API directly from the visitor's own browser
with the visitor's own key (the documented `anthropic-dangerous-direct-browser-access`
header), so there is no server to host, no cold start, and no key of ours on the wire.

The prompts are the simulation contract — determinism, the silence rule, engagement
decay, the no-narrator rule — so they are extracted byte-exactly from prompts.py by
splitting the real rendered output around sentinels, never retyped. The two transcript
formatters have to be ported to JS; build_play_verify.py proves the port is byte-identical
to the Python on the recorded session.

    python build_play.py
"""
import json
import pathlib

from personas import CHILDREN, LESSON
from prompts import report_prompt, turn_system_prompt, turn_user_message

ROOT = pathlib.Path(__file__).resolve().parent

# --- byte-exact prompt extraction -------------------------------------------------
# turn_user_message([], LINE) renders the template with the empty-transcript history
# and our sentinel line; split on both to recover the three literal segments.
EMPTY_HISTORY = "(the lesson has not started yet)"
LINE_SENTINEL = "\x01TEACHER_LINE\x01"
_tum = turn_user_message([], LINE_SENTINEL)
assert EMPTY_HISTORY in _tum and LINE_SENTINEL in _tum, "turn_user_message shape changed"
_pre_hist, _rest = _tum.split(EMPTY_HISTORY, 1)
_mid, _post = _rest.split(LINE_SENTINEL, 1)

# report_prompt([]) renders with an empty transcript block, so the text before and
# after that block is exactly the literal prose plus the schema.
_rp = report_prompt([])
_MARK = "FULL TRANSCRIPT\n"
assert _MARK in _rp, "report_prompt shape changed"
_rep_pre, _rep_post = _rp.split(_MARK, 1)
_rep_pre = _rep_pre + _MARK

PAYLOAD = {
    "lesson": LESSON,
    "children": [
        {k: c[k] for k in ("id", "name", "avatar", "aser_band", "public_profile",
                           "hidden_level", "hidden_misconception")}
        for c in CHILDREN
    ],
    "prompts": {
        "turnSystem": {
            "Hinglish": turn_system_prompt("Hinglish"),
            "English": turn_system_prompt("English"),
        },
        "turnUser": {"preHistory": _pre_hist, "mid": _mid, "post": _post},
        "report": {"pre": _rep_pre, "post": _rep_post},
    },
    "demo": json.loads((ROOT / "demo_fallback.json").read_text(encoding="utf-8")),
}

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KAKSHA — teach a live class</title>
<meta name="description" content="Claude plays five Grade 3 children with hidden learning levels and hidden misconceptions. Teach them for six turns, then the X-ray turns on.">
<style>
:root{
  --bg:#faf9f7; --panel:#fff; --ink:#1b1a18; --muted:#6a6560; --line:#e3ddd6;
  --engaged:#2e9e5b; --drifting:#c98a12; --lost:#b03636; --xray:#7b5cd6; --accent:#1b1a18;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#15140f; --panel:#1e1c17; --ink:#f2efe9; --muted:#a09a91; --line:#33302a;
    --engaged:#4cc97c; --drifting:#e0a734; --lost:#e06767; --xray:#a68bf0; --accent:#f2efe9;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-text-size-adjust:100%}
.wrap{max-width:860px;margin:0 auto;padding:0 20px;padding-block:40px 64px}
h1{font-size:clamp(1.9rem,5.5vw,2.7rem);line-height:1.08;margin:0 0 .3em;letter-spacing:-.02em}
h2{font-size:1.3rem;margin:2.4em 0 .6em;letter-spacing:-.01em}
h3{font-size:1rem;margin:1.6em 0 .4em}
p{margin:0 0 1em}
a{color:inherit;text-underline-offset:2px;
  text-decoration-color:color-mix(in srgb,var(--ink) 35%,transparent)}
.lede{font-size:1.1rem;color:var(--muted);max-width:62ch}
.badges{display:flex;flex-wrap:wrap;gap:8px;margin:1.3em 0 0}
.badge{font-size:.76rem;border:1px solid var(--line);border-radius:999px;
  padding:.3em .8em;color:var(--muted);background:var(--panel)}
.rule{height:1px;background:var(--line);border:0;margin:2.4em 0}

.keybox{border:1px solid var(--line);background:var(--panel);border-radius:14px;
  padding:1rem 1.1rem;margin:1.4em 0}
.keybox h3{margin:0 0 .4em}
.keyrow{display:flex;gap:8px;flex-wrap:wrap;margin:.6em 0 .4em}
input[type=password],input[type=text]{font:inherit;font-size:.92rem;flex:1 1 280px;
  min-width:0;padding:.6em .8em;border:1px solid var(--line);border-radius:9px;
  background:var(--bg);color:var(--ink)}
.privacy{font-size:.82rem;color:var(--muted);margin:.4em 0 0}
.status{font-size:.85rem;font-weight:600;margin-top:.5em}
.status.ok{color:var(--engaged)} .status.bad{color:var(--lost)}

.kids{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:1.1em 0}
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

.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:1.2em 0}
button{font:inherit;font-size:.92rem;font-weight:600;cursor:pointer;
  border:1px solid var(--line);border-radius:10px;padding:.62em 1.1em;
  background:var(--panel);color:var(--ink)}
button.primary{background:var(--accent);color:var(--bg);border-color:var(--accent)}
button:disabled{opacity:.42;cursor:not-allowed}
.progress{font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums}
.sayrow{display:flex;gap:8px;flex-wrap:wrap;margin:1em 0}
.err{border:1px solid color-mix(in srgb,var(--lost) 50%,var(--line));
  background:color-mix(in srgb,var(--lost) 10%,transparent);border-radius:10px;
  padding:.7rem .9rem;margin:1em 0;font-size:.9rem}
.spin{font-size:.9rem;color:var(--muted);font-style:italic;margin:1em 0}

.turn{margin:1.4em 0}
.tline{background:color-mix(in srgb,var(--ink) 6%,transparent);
  border-left:3px solid color-mix(in srgb,var(--ink) 42%,transparent);
  padding:.6rem .85rem;border-radius:0 8px 8px 0;margin-bottom:.7em}
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
  border-radius:14px;padding:1rem 1.1rem;margin:1.5em 0}
.reveal h3{margin-top:0}
.hidden{display:none}
.scores{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:1.1em 0}
@media (max-width:640px){.scores{grid-template-columns:1fr}}
.score{border:1px solid var(--line);border-radius:12px;padding:.8rem .9rem;background:var(--panel)}
.score .v{font-size:1.9rem;font-weight:700;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.score .k{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.meter{height:5px;border-radius:99px;background:color-mix(in srgb,var(--ink) 12%,transparent);
  margin-top:.5rem;overflow:hidden}
.meter i{display:block;height:100%;border-radius:99px;background:var(--lost)}
.headline{font-size:1.1rem;font-weight:600;margin:.2em 0 1em;line-height:1.45}
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
footer{margin-top:3.2em;padding-top:1.4em;border-top:1px solid var(--line);
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
  <span class="badge">Live — Claude plays the class</span>
  <span class="badge">Runs in your browser, no server</span>
  <span class="badge"><a href="../">Watch a recorded lesson instead →</a></span>
  <span class="badge"><a href="https://github.com/deepakwadge81/kaksha">Source</a></span>
</div>

<div class="keybox">
  <h3>Your Anthropic API key</h3>
  <p class="note" style="margin:0">Needed because the class is generated live. A six-turn
  lesson plus the coaching report costs roughly <strong>$0.05–0.15</strong> on Claude
  Sonnet 5.</p>
  <div class="keyrow">
    <input id="key" type="password" placeholder="sk-ant-..." autocomplete="off" spellcheck="false">
    <button id="savekey" class="primary">Use this key</button>
    <button id="clearkey">Forget</button>
  </div>
  <p class="privacy">Your key is sent <strong>only</strong> to <code>api.anthropic.com</code>,
  directly from this browser tab. It is held in <code>sessionStorage</code> — gone when you
  close the tab — and is never transmitted to this site's author, never logged, and never
  placed in a URL. This page is static; there is no server to receive it.
  <a href="https://github.com/deepakwadge81/kaksha/blob/main/docs/play/index.html">Read the
  source</a> if you'd rather check than trust.</p>
  <div id="keystatus" class="status"></div>
</div>

<hr class="rule">

<h2>The class</h2>
<div class="kids" id="kids"></div>
<p class="note" id="pubnote"></p>

<h2>The lesson</h2>
<p class="note" id="lessonnote"></p>
<div id="err"></div>
<div id="turns"></div>
<div id="spin" class="spin hidden">the class responds…</div>

<div class="sayrow">
  <input id="say" type="text" placeholder="Say or do something as the teacher…" maxlength="2000">
  <button id="send" class="primary">Say it</button>
  <span class="progress" id="prog"></span>
</div>
<div class="controls">
  <button id="end">End lesson &amp; see the X-ray →</button>
  <button id="reset">New lesson</button>
</div>

<div id="endzone" class="hidden">
  <div class="reveal">
    <h3>🔍 X-ray on</h3>
    <p style="margin:0">The lesson is replayed above with what each child was actually
    thinking — the thing a real teacher never gets to see.</p>
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
  <p>Reading levels follow the ASER 2024 bands; the spread across these five is the
  documented within-grade dispersion of about seven grade-equivalents. No real child data,
  no recording, no consent problem — the children are calibrated to published
  distributions, not observed from any classroom.</p>
  <p><a href="https://github.com/deepakwadge81/kaksha">Source, tests and the Streamlit
  app →</a></p>
</footer>

</div>

<script id="data" type="application/json">__PAYLOAD__</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const CHILDREN = D.children, byId = Object.fromEntries(CHILDREN.map(c => [c.id, c]));
const CHILD_ORDER = CHILDREN.map(c => c.id);
const VALID_IDS = new Set(CHILD_ORDER);
const VALID_ENG = new Set(["engaged", "drifting", "lost"]);
const MODEL = "claude-sonnet-5", MAX_TURNS = 6;
const TURN_MAX_TOKENS = 8000, REPORT_MAX_TOKENS = 16000;   // thinking counts against these
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,
  m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m]));

// ---------- core.py, ported ----------
class TruncatedOutput extends Error {}          // deterministic: never retried

function parseJson(text) {                       // tolerant of fences/preamble/commentary
  if (typeof text !== "string") throw new Error("model output was not text");
  let t = text.trim().replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "").trim();
  const start = t.indexOf("{"), end = t.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("no JSON object found in model output");
  return JSON.parse(t.slice(start, end + 1));
}

function normaliseTurn(data) {                   // guarantee one clean entry per child
  if (!data || typeof data !== "object") data = {};
  const seen = {};
  for (const r of (data.responses || [])) {
    if (!r || typeof r !== "object") continue;
    const cid = r.child_id;
    if (VALID_IDS.has(cid) && !(cid in seen)) {
      seen[cid] = {
        child_id: cid,
        speaks: Boolean(r.speaks) && Boolean(r.says),
        says: r.says ? r.says : null,
        behaviour: r.behaviour || "",
        internal_state: r.internal_state || "",
        engagement: VALID_ENG.has(r.engagement) ? r.engagement : "engaged",
      };
    }
  }
  for (const cid of CHILD_ORDER) {
    if (!(cid in seen)) seen[cid] = { child_id: cid, speaks: false, says: null,
      behaviour: "no reaction", internal_state: "", engagement: "engaged" };
  }
  const note = data.class_note;
  return { responses: CHILD_ORDER.map(c => seen[c]),
           class_note: (typeof note === "string" && note.trim()) ? note : null };
}

async function callAndParse(fetchRaw, attempts = 2) {
  let lastErr = null;
  for (let i = 0; i < attempts; i++) {
    const raw = await fetchRaw();                // a fresh call each attempt
    try { return [parseJson(raw), raw]; }
    catch (e) { if (e instanceof TruncatedOutput) throw e; lastErr = e; }
  }
  throw lastErr;
}

// ---------- the API call ----------
function getKey() { try { return sessionStorage.getItem("kaksha_key") || ""; } catch (e) { return ""; } }

async function callClaude(system, user, maxTokens) {
  const key = getKey();
  if (!key) throw new Error("No API key set — add one above.");
  const r = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: MODEL, max_tokens: maxTokens,
      system: [{ type: "text", text: system, cache_control: { type: "ephemeral" } }],
      messages: [{ role: "user", content: user }],
    }),
  });
  const j = await r.json().catch(() => null);
  if (!r.ok) {
    const msg = (j && j.error && j.error.message) || ("HTTP " + r.status);
    throw new Error(r.status === 401 ? "That key was rejected (401). Check it and try again."
                  : r.status === 429 ? "Rate limited (429). Wait a moment and retry."
                  : msg);
  }
  if (j.stop_reason === "refusal") throw new Error("The model declined this request.");
  if (j.stop_reason === "max_tokens") {
    const th = j.usage && j.usage.output_tokens_details && j.usage.output_tokens_details.thinking_tokens;
    throw new TruncatedOutput("hit the " + maxTokens.toLocaleString() + "-token cap"
      + (th ? " (" + th.toLocaleString() + " spent thinking)" : ""));
  }
  return (j.content || []).filter(b => b.type === "text").map(b => b.text).join("");
}

// ---------- prompt assembly (segments extracted byte-exactly from prompts.py) ----------
const P = D.prompts;

function turnUserMessage(transcript, teacherLine) {
  const history = [];
  for (const entry of transcript) {
    if (entry.role === "teacher") history.push("TEACHER: " + entry.content);
    else for (const r of (entry.content.responses || [])) {
      if (r.speaks && r.says) history.push("  " + r.child_id.toUpperCase() + ": " + r.says);
      else if (r.behaviour) history.push("  (" + r.child_id + " — " + r.behaviour + ")");
    }
  }
  const historyText = history.length ? history.join("\n") : "(the lesson has not started yet)";
  return P.turnUser.preHistory + historyText + P.turnUser.mid + teacherLine + P.turnUser.post;
}

function reportPrompt(transcript) {
  const lines = [];
  let turn = 0;
  for (const entry of transcript) {
    if (entry.role === "teacher") {
      turn += 1;
      lines.push("\n[Turn " + turn + "] TEACHER: " + entry.content);
    } else {
      for (const r of (entry.content.responses || [])) {
        const c = r.child_id;
        if (r.speaks && r.says) lines.push('    ' + c + ': "' + r.says + '"  (' + (r.behaviour || "") + ')');
        else lines.push("    " + c + ": [silent] (" + (r.behaviour || "") + ")");
        lines.push("       thinking: " + (r.internal_state || ""));
      }
    }
  }
  return P.report.pre + lines.map(l => l + "\n").join("") + P.report.post;
}

// ---------- state + rendering ----------
let transcript = [], engagement = {}, report = null, busy = false;
CHILDREN.forEach(c => engagement[c.id] = "engaged");

const $ = id => document.getElementById(id);
const kidsEl = $("kids"), turnsEl = $("turns");

function paintKids() {
  kidsEl.innerHTML = CHILDREN.map(c => `
    <div class="kid" data-eng="${esc(engagement[c.id])}">
      <div class="face" aria-hidden="true">${c.avatar}</div>
      <div class="nm">${esc(c.name)}</div>
      <div class="bd">${esc(c.aser_band)}</div>
      <div class="st">● ${esc(engagement[c.id])}</div>
    </div>`).join("");
}

function renderTurn(line, data) {
  const rows = (data.responses || []).map(r => {
    const c = byId[r.child_id] || { name: r.child_id, avatar: "" };
    const body = (r.speaks && r.says)
      ? `<p class="says"><span class="who">${c.avatar} ${esc(c.name)}:</span> &ldquo;${esc(r.says)}&rdquo;</p>
         ${r.behaviour ? `<div class="beh">${esc(r.behaviour)}</div>` : ""}`
      : `<div class="silent">${c.avatar} ${esc(c.name)} — ${esc(r.behaviour || "no reaction")}</div>`;
    return `<div class="resp">${body}
      ${r.internal_state ? `<div class="xr">thinking: ${esc(r.internal_state)}</div>` : ""}</div>`;
  }).join("");
  turnsEl.insertAdjacentHTML("beforeend", `<div class="turn">
    <div class="tline"><b>You</b> — ${esc(line)}</div>${rows}
    ${data.class_note ? `<div class="note">${esc(data.class_note)}</div>` : ""}</div>`);
}

function taught() { return transcript.filter(e => e.role === "teacher").length; }

function sync() {
  const n = taught(), atCap = n >= MAX_TURNS, key = getKey();
  $("prog").textContent = `Turn ${Math.min(n + (atCap ? 0 : 1), MAX_TURNS)} of ${MAX_TURNS}`;
  $("say").disabled = busy || atCap || !!report || !key;
  $("send").disabled = busy || atCap || !!report || !key;
  $("end").disabled = busy || n < 1 || !!report;
  $("reset").disabled = busy;
  $("keystatus").className = "status " + (key ? "ok" : "");
  $("keystatus").textContent = key ? "🟢 Key set for this tab" : "";
  $("lessonnote").textContent = !key
    ? "Add a key above to teach a live class — or watch the recorded lesson instead."
    : atCap ? "You're out of turns. End the lesson to see the X-ray."
    : "Open the lesson however you like. A good first move is a question — but watch who answers it.";
  $("spin").classList.toggle("hidden", !busy);
}

function showErr(msg) {
  $("err").innerHTML = msg ? `<div class="err">${esc(msg)}</div>` : "";
}

async function say() {
  const line = $("say").value.trim().slice(0, 2000);
  if (!line || busy) return;
  busy = true; showErr(""); sync();
  transcript.push({ role: "teacher", content: line });
  try {
    const [parsed] = await callAndParse(() => callClaude(
      P.turnSystem[document.querySelector("body").dataset.lang || "Hinglish"],
      turnUserMessage(transcript.slice(0, -1), line), TURN_MAX_TOKENS));
    const data = normaliseTurn(parsed);
    transcript.push({ role: "class", content: data });
    data.responses.forEach(r => engagement[r.child_id] = r.engagement);
    renderTurn(line, data);
    paintKids();
    $("say").value = "";
  } catch (e) {
    transcript.pop();
    showErr(e instanceof TruncatedOutput
      ? "The reply was cut off — " + e.message + ". Try a shorter instruction."
      : "Turn failed — " + e.message);
  }
  busy = false; sync();
}

async function endLesson() {
  if (busy || taught() < 1) return;
  busy = true; showErr(""); $("spin").textContent = "your coach is reviewing the lesson…"; sync();
  try {
    const [parsed] = await callAndParse(() => callClaude(
      "You are a rigorous, specific instructional coach. Return JSON only.",
      reportPrompt(transcript), REPORT_MAX_TOKENS));
    report = parsed;
    document.body.classList.add("xray");
    renderReport();
    $("endzone").classList.remove("hidden");
  } catch (e) {
    showErr("Report failed — " + e.message);
  }
  busy = false; $("spin").textContent = "the class responds…"; sync();
}

function renderReport() {
  document.getElementById("hidden-table").innerHTML =
    `<thead><tr><th>Child</th><th>Actual level</th><th>Hidden misconception</th></tr></thead><tbody>` +
    CHILDREN.map(c => `<tr>
      <td><strong>${c.avatar} ${esc(c.name)}</strong><br><span class="beh">${esc(c.aser_band)}</span></td>
      <td>${esc(c.hidden_level)}</td><td>${esc(c.hidden_misconception)}</td></tr>`).join("") + `</tbody>`;

  $("headline").textContent = report.headline || "";
  const LABELS = { attention_equity: "Attention equity", question_quality: "Question quality",
                   misconception_diagnosis: "Misconception diagnosis" };
  $("scores").innerHTML = Object.entries(LABELS).map(([k, label]) => {
    const v = (report.scores || {})[k];
    return `<div class="score"><div class="k">${label}</div>
      <div class="v">${esc(v)}<span style="font-size:.9rem;font-weight:400;color:var(--muted)">/100</span></div>
      <div class="meter"><i style="width:${Math.max(0, Math.min(100, Number(v) || 0))}%"></i></div></div>`;
  }).join("");

  $("attention").innerHTML = `<thead><tr><th>Child</th><th>Addressed</th><th>Spoke</th><th>Note</th></tr></thead><tbody>` +
    (report.attention || []).map(a => {
      const c = byId[a.child_id] || { name: a.child_id, avatar: "" };
      return `<tr><td><strong>${c.avatar} ${esc(c.name)}</strong></td>
        <td class="n">${esc(a.times_addressed)}</td><td class="n">${esc(a.times_spoke)}</td>
        <td>${esc(a.note)}</td></tr>`;
    }).join("") + `</tbody>`;

  $("misconceptions").innerHTML = `<thead><tr><th>Child</th><th>Surfaced?</th><th>Evidence</th></tr></thead><tbody>` +
    (report.misconceptions || []).map(m => {
      const c = byId[m.child_id] || { name: m.child_id, avatar: "" };
      return `<tr><td><strong>${c.avatar} ${esc(c.name)}</strong><br>
          <span class="beh">${esc(m.hidden_misconception)}</span></td>
        <td><span class="tag ${m.surfaced ? "yes" : "no"}">${m.surfaced ? "surfaced" : "missed"}</span></td>
        <td>${esc(m.evidence)}</td></tr>`;
    }).join("") + `</tbody>`;

  $("moments").innerHTML = (report.moments || []).map(m => `<div class="turn">
    <div class="tline"><b>Turn ${esc(m.turn)}</b> — ${esc(m.what_happened)}</div>
    <div class="resp"><p class="says"><span class="who">What to try:</span> ${esc(m.what_to_try)}</p></div>
  </div>`).join("");

  $("nexttime").innerHTML = (report.next_time || []).map(n => `<li>${esc(n)}</li>`).join("");
}

// ---------- wiring ----------
$("savekey").addEventListener("click", () => {
  const v = $("key").value.trim();
  try { if (v) sessionStorage.setItem("kaksha_key", v); } catch (e) {}
  $("key").value = "";
  showErr(""); sync();
});
$("clearkey").addEventListener("click", () => {
  try { sessionStorage.removeItem("kaksha_key"); } catch (e) {}
  sync();
});
$("send").addEventListener("click", say);
$("say").addEventListener("keydown", e => { if (e.key === "Enter") say(); });
$("end").addEventListener("click", endLesson);
$("reset").addEventListener("click", () => {
  transcript = []; report = null; CHILDREN.forEach(c => engagement[c.id] = "engaged");
  turnsEl.innerHTML = ""; $("endzone").classList.add("hidden");
  document.body.classList.remove("xray"); showErr(""); paintKids(); sync();
});

$("pubnote").textContent = "All you are told up front — " +
  CHILDREN.map(c => c.name + ": " + c.public_profile).join("  ·  ");
paintKids();
sync();
</script>
</body>
</html>
"""

out = ROOT / "docs" / "play"
out.mkdir(parents=True, exist_ok=True)
html = HTML.replace("__PAYLOAD__", json.dumps(PAYLOAD, ensure_ascii=False))
(out / "index.html").write_text(html, encoding="utf-8")
print("wrote docs/play/index.html  (%d bytes)" % len(html))
print("  turn system prompt (Hinglish): %d chars" % len(PAYLOAD["prompts"]["turnSystem"]["Hinglish"]))
print("  report pre/post: %d / %d chars"
      % (len(PAYLOAD["prompts"]["report"]["pre"]), len(PAYLOAD["prompts"]["report"]["post"])))

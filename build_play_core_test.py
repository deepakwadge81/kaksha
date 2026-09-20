"""Run the browser port of core.py against the same fixtures as test_offline.py.

parseJson / normaliseTurn / callAndParse were reimplemented in JS for docs/play. This
drives the JS versions over the offline suite's cases and checks they behave the same —
free, no API key, no network.

    python build_play_core_test.py
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
page = (ROOT / "docs" / "play" / "index.html").read_text(encoding="utf-8")
payload = json.loads(
    re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1))

# Pull the ported functions straight out of the shipped page so we test what ships.
start = page.index("// ---------- core.py, ported ----------")
end = page.index("// ---------- the API call ----------")
ported = page[start:end]
assert "function parseJson" in ported and "function normaliseTurn" in ported

js = r"""
const CHILDREN = %(children)s;
const CHILD_ORDER = CHILDREN.map(c => c.id);
const VALID_IDS = new Set(CHILD_ORDER);
const VALID_ENG = new Set(["engaged", "drifting", "lost"]);

%(ported)s

const GOOD = '{"responses": [], "class_note": "hi"}';
const out = [];
const check = (name, fn) => {
  try { const r = fn(); out.push([r === false ? "FAIL" : "PASS", name, ""]); }
  catch (e) { out.push(["FAIL", name, e.name + ": " + e.message]); }
};
const raises = (fn) => { try { fn(); return false; } catch (e) { return true; } };

// --- parseJson, same fixtures as test_offline.py ---
check("clean JSON", () => !!parseJson(GOOD));
check("wrapped in ```json fences", () => !!parseJson("```json\n" + GOOD + "\n```"));
check("wrapped in bare ``` fences", () => !!parseJson("```\n" + GOOD + "\n```"));
check("preamble prose before the JSON", () => !!parseJson("Sure! Here is the classroom response:\n\n" + GOOD));
check("trailing commentary after the JSON", () => !!parseJson(GOOD + "\n\nLet me know if you'd like another turn."));
check("leading and trailing whitespace", () => !!parseJson("\n\n   " + GOOD + "   \n"));
check("nested braces survive the slice", () => parseJson('{"a": {"b": {"c": 1}}}').a.b.c === 1);
check("empty string raises", () => raises(() => parseJson("")));
check("prose with no JSON raises", () => raises(() => parseJson("I'm sorry, I can't do that.")));
check("truncated JSON raises", () => raises(() => parseJson('{"responses": [{"child_id":')));
check("non-string input raises", () => raises(() => parseJson(null)));

// --- normaliseTurn ---
const allFive = d => JSON.stringify(d.responses.map(r => r.child_id)) === JSON.stringify(CHILD_ORDER);
check("empty dict still yields five children", () => allFive(normaliseTurn({})));
check("null yields five children", () => allFive(normaliseTurn(null)));
check("missing responses key yields five children", () => allFive(normaliseTurn({class_note: "x"})));
check("only two children returned, three filled in", () => allFive(normaliseTurn({responses: [
  {child_id: "priya", speaks: true, says: "35!"}, {child_id: "rahul", speaks: false}]})));
check("hallucinated child_id is dropped", () => {
  const d = normaliseTurn({responses: [{child_id: "ravi_nope", speaks: true, says: "hi"},
    {child_id: "meera", speaks: true, says: "25"}]});
  return allFive(d) && !d.responses.some(r => r.child_id === "ravi_nope");
});
check("duplicate child entries are deduped", () => {
  const d = normaliseTurn({responses: [{child_id: "priya", speaks: true, says: "first"},
    {child_id: "priya", speaks: true, says: "second"}]});
  return allFive(d) && d.responses.find(r => r.child_id === "priya").says === "first";
});
check("invalid engagement enum falls back to engaged", () =>
  normaliseTurn({responses: [{child_id: "meera", engagement: "extremely bored indeed"}]})
    .responses.find(r => r.child_id === "meera").engagement === "engaged");
check("speaks=true with says=null is corrected", () =>
  normaliseTurn({responses: [{child_id: "imran", speaks: true, says: null}]})
    .responses.find(r => r.child_id === "imran").speaks === false);
check("non-object entries in responses are skipped", () =>
  allFive(normaliseTurn({responses: ["oops", 42, null, {child_id: "meera"}]})));
check("non-string class_note becomes null", () => normaliseTurn({class_note: {x: 1}}).class_note === null);
check("empty class_note becomes null", () => normaliseTurn({class_note: "   "}).class_note === null);

// --- callAndParse: retry, no-retry, exhaustion, truncation ---
const results = [];
(async () => {
  let n = 0;
  const [d1, raw1] = await callAndParse(() => { n++; return n === 1 ? '{"responses": [' : GOOD; });
  results.push(["retries once on broken JSON then succeeds", n === 2 && raw1 === GOOD && d1.class_note === "hi"]);

  n = 0;
  await callAndParse(() => { n++; return GOOD; });
  results.push(["does not retry a response that parses cleanly", n === 1]);

  n = 0;
  let raised = false;
  try { await callAndParse(() => { n++; return "still not JSON"; }, 3); } catch (e) { raised = true; }
  results.push(["raises after exhausting attempts", raised && n === 3]);

  n = 0;
  let trunc = false;
  try { await callAndParse(() => { n++; throw new TruncatedOutput("cap"); }, 3); }
  catch (e) { trunc = e instanceof TruncatedOutput; }
  results.push(["does not waste retries on a truncation", trunc && n === 1]);

  for (const [name, ok] of results) out.push([ok ? "PASS" : "FAIL", name, ""]);
  process.stdout.write(JSON.stringify(out));
})();
""" % {"children": json.dumps(payload["children"]), "ported": ported}

f = ROOT / "_coretest.mjs"
f.write_text(js, encoding="utf-8")
try:
    p = subprocess.run(["node", str(f)], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if p.returncode != 0:
        sys.exit("node failed:\n" + p.stderr)
    rows = json.loads(p.stdout)
finally:
    f.unlink(missing_ok=True)

bad = 0
for status, name, detail in rows:
    if status == "FAIL":
        bad += 1
    print("  %s  %s%s" % (status.ljust(4), name, ("   " + detail) if detail else ""))
print()
print("%d/%d browser-port core checks passed" % (len(rows) - bad, len(rows)))
sys.exit(1 if bad else 0)

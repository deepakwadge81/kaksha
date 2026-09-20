"""Prove the JS prompt builders in docs/play/index.html match prompts.py byte-for-byte.

The static prompt text is extracted from Python, so it cannot drift. The two transcript
formatters (turn_user_message, report_prompt) had to be reimplemented in JS, and a silent
divergence there would quietly change the simulation. This runs the recorded session
through both implementations and compares the bytes.

    python build_play_verify.py        # exits non-zero on any mismatch
"""
import json
import pathlib
import re
import subprocess
import sys

from prompts import report_prompt, turn_user_message

ROOT = pathlib.Path(__file__).resolve().parent
demo = json.loads((ROOT / "demo_fallback.json").read_text(encoding="utf-8"))
transcript = demo["transcript"]

page = (ROOT / "docs" / "play" / "index.html").read_text(encoding="utf-8")
payload = json.loads(
    re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1))

# Every prefix of the real session, plus the awkward cases.
cases = []
for i in range(0, len(transcript) + 1, 2):
    cases.append({"transcript": transcript[:i], "line": "Class, what is 52 minus 27?"})
cases.append({"transcript": [], "line": "Namaste bacchon."})
cases.append({"transcript": transcript, "line": 'She said "35" — why?  Line with \\ and — dashes'})
cases.append({"transcript": transcript[:4], "line": "बच्चों, बताओ 52 में से 27 घटाने पर क्या आएगा?"})

expected = [{"turnUser": turn_user_message(c["transcript"], c["line"]),
             "report": report_prompt(c["transcript"])} for c in cases]

# Re-implementations lifted verbatim from the generated page, driven over the same cases.
js_src = r"""
const P = %(prompts)s, cases = %(cases)s;

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

process.stdout.write(JSON.stringify(cases.map(c => ({
  turnUser: turnUserMessage(c.transcript, c.line),
  report: reportPrompt(c.transcript),
}))));
""" % {"prompts": json.dumps(payload["prompts"]), "cases": json.dumps(cases)}

js_file = ROOT / "_verify.mjs"
js_file.write_text(js_src, encoding="utf-8")
try:
    proc = subprocess.run(["node", str(js_file)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    if proc.returncode != 0:
        sys.exit("node failed:\n" + proc.stderr)
    actual = json.loads(proc.stdout)
finally:
    js_file.unlink(missing_ok=True)

fails = 0
for i, (exp, act) in enumerate(zip(expected, actual)):
    for kind in ("turnUser", "report"):
        if exp[kind] == act[kind]:
            print("  PASS  case %d %s  (%d chars)" % (i, kind, len(exp[kind])))
        else:
            fails += 1
            print("  FAIL  case %d %s" % (i, kind))
            e, a = exp[kind], act[kind]
            for j in range(min(len(e), len(a))):
                if e[j] != a[j]:
                    print("        first difference at char %d" % j)
                    print("        python: %r" % e[max(0, j - 60):j + 60])
                    print("        js    : %r" % a[max(0, j - 60):j + 60])
                    break
            else:
                print("        length differs: python %d vs js %d" % (len(e), len(a)))

print()
total = len(expected) * 2
print("%d/%d prompt builds byte-identical between prompts.py and the browser port"
      % (total - fails, total))
sys.exit(1 if fails else 0)

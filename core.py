"""Pure logic, no Streamlit. Extracted so the test suite can hammer it without a browser."""

import json
import os
import re
from statistics import mean

from personas import CHILDREN

VALID_IDS = {c["id"] for c in CHILDREN}
VALID_ENGAGEMENT = {"engaged", "drifting", "lost"}
CHILD_ORDER = [c["id"] for c in CHILDREN]


def parse_json(text: str) -> dict:
    """Tolerant of code fences, preamble prose and trailing commentary."""
    if not isinstance(text, str):
        raise ValueError("model output was not text")
    t = re.sub(r"^```(?:json)?\s*", "", text.strip())
    t = re.sub(r"\s*```$", "", t).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return json.loads(t[start : end + 1])


class TruncatedOutput(RuntimeError):
    """The model hit max_tokens before finishing the JSON.

    Deliberately NOT a ValueError, so `call_and_parse` lets it through instead of
    burning a retry: truncation is deterministic — the next attempt hits the same
    cap. On thinking-by-default models (Sonnet 5, Opus 5) thinking tokens count
    against max_tokens, so a cap sized for a non-thinking model silently starves
    the payload. The fix is a bigger cap, not another call.
    """


def call_and_parse(fetch_raw, attempts: int = 2):
    """Call `fetch_raw()` — which must hit the model afresh and return raw text —
    and parse the result as JSON, retrying the whole round-trip (not just the
    parse) if the model returns syntactically invalid JSON.

    Live testing found Claude occasionally emits broken JSON (a genuinely missing
    delimiter, not markdown fencing or prose, which `parse_json` already tolerates)
    at roughly a 10% rate. Re-parsing the same broken text can't fix that — only a
    fresh call can. Re-raises the last error if every attempt fails.

    Returns (parsed_dict, raw_text) from the attempt that succeeded.
    """
    last_err = None
    for i in range(attempts):
        raw = fetch_raw()
        try:
            return parse_json(raw), raw
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            if os.environ.get("KAKSHA_DUMP_FAILURES"):
                with open(f"failed_attempt{i}.txt", "w", encoding="utf-8") as f:
                    f.write(raw)
    raise last_err


def normalise_turn(data: dict) -> dict:
    """Guarantee exactly one well-formed entry per child, in roster order.

    The UI must never crash on a malformed turn: missing children, unknown child_ids,
    duplicate entries, a bad engagement enum, speaks=true with says=null, or a
    non-string class_note all get repaired here rather than rendered.
    """
    if not isinstance(data, dict):
        data = {}
    seen = {}
    for r in data.get("responses") or []:
        if not isinstance(r, dict):
            continue
        cid = r.get("child_id")
        if cid in VALID_IDS and cid not in seen:
            eng = r.get("engagement")
            seen[cid] = {
                "child_id": cid,
                "speaks": bool(r.get("speaks")) and bool(r.get("says")),
                "says": r.get("says") if r.get("says") else None,
                "behaviour": r.get("behaviour") or "",
                "internal_state": r.get("internal_state") or "",
                "engagement": eng if eng in VALID_ENGAGEMENT else "engaged",
            }
    for cid in VALID_IDS:
        seen.setdefault(cid, {
            "child_id": cid, "speaks": False, "says": None,
            "behaviour": "no reaction", "internal_state": "", "engagement": "engaged",
        })
    note = data.get("class_note")
    return {
        "responses": [seen[c] for c in CHILD_ORDER],
        "class_note": note if isinstance(note, str) and note.strip() else None,
    }


def overall(scores: dict) -> int:
    keys = ("attention_equity", "question_quality", "misconception_diagnosis")
    vals = [(scores or {}).get(k) for k in keys]
    vals = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return round(mean(vals)) if vals else 0


def validate_report(rep: dict) -> list[str]:
    """Returns a list of problems. Empty list means the report is renderable."""
    problems = []
    if not isinstance(rep, dict):
        return ["report is not an object"]

    if not isinstance(rep.get("headline"), str) or not rep["headline"].strip():
        problems.append("missing headline")

    scores = rep.get("scores")
    if not isinstance(scores, dict):
        problems.append("missing scores object")
    else:
        for k in ("attention_equity", "question_quality", "misconception_diagnosis"):
            v = scores.get(k)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                problems.append(f"score {k} is not a number")
            elif not 0 <= v <= 100:
                problems.append(f"score {k} out of range: {v}")

    for field in ("attention", "misconceptions", "moments", "next_time"):
        if not isinstance(rep.get(field), list) or not rep[field]:
            problems.append(f"{field} missing or empty")

    covered = {r.get("child_id") for r in rep.get("attention", []) if isinstance(r, dict)}
    missing = VALID_IDS - covered
    if missing:
        problems.append(f"attention missing children: {sorted(missing)}")

    for r in rep.get("attention", []) or []:
        if isinstance(r, dict) and r.get("child_id") not in VALID_IDS:
            problems.append(f"unknown child_id in attention: {r.get('child_id')}")

    for m in rep.get("misconceptions", []) or []:
        if isinstance(m, dict) and not isinstance(m.get("surfaced"), bool):
            problems.append(f"misconception.surfaced not a bool for {m.get('child_id')}")

    return problems

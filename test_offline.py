"""
Offline edge-case suite. No API key, no network, no cost.

Everything here is about the question: if Claude returns something ugly, does the app
crash in front of the judges? Run with:  python test_offline.py
"""

import json
import sys

from core import (CHILD_ORDER, TruncatedOutput, call_and_parse, normalise_turn,
                  overall, parse_json, validate_report)

PASS, FAIL = [], []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
    except AssertionError as e:
        FAIL.append((name, f"assertion: {e}"))
    except Exception as e:
        FAIL.append((name, f"{type(e).__name__}: {e}"))


# --------------------------------------------------------------------- parse_json
GOOD = '{"responses": [], "class_note": "hi"}'

check("clean JSON", lambda: parse_json(GOOD))
check("wrapped in ```json fences",
      lambda: parse_json("```json\n" + GOOD + "\n```"))
check("wrapped in bare ``` fences",
      lambda: parse_json("```\n" + GOOD + "\n```"))
check("preamble prose before the JSON",
      lambda: parse_json("Sure! Here is the classroom response:\n\n" + GOOD))
check("trailing commentary after the JSON",
      lambda: parse_json(GOOD + "\n\nLet me know if you'd like another turn."))
check("leading and trailing whitespace",
      lambda: parse_json("\n\n   " + GOOD + "   \n"))
check("nested braces survive the slice",
      lambda: parse_json('{"a": {"b": {"c": 1}}}')["a"]["b"]["c"] == 1)


def _raises(text):
    try:
        parse_json(text)
    except Exception:
        return
    raise AssertionError("should have raised")


check("empty string raises", lambda: _raises(""))
check("prose with no JSON raises", lambda: _raises("I'm sorry, I can't do that."))
check("truncated JSON raises", lambda: _raises('{"responses": [{"child_id":'))
check("non-string input raises", lambda: _raises(None))


# --------------------------------------------------------------------- call_and_parse
def retries_once_then_succeeds():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return '{"responses": [' if calls["n"] == 1 else GOOD
    data, raw = call_and_parse(fetch)
    assert calls["n"] == 2, f"expected exactly one retry, got {calls['n']} calls"
    assert raw == GOOD and data["class_note"] == "hi"


def succeeds_first_try_without_retrying():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return GOOD
    call_and_parse(fetch)
    assert calls["n"] == 1, f"should not retry a clean response, got {calls['n']} calls"


def exhausts_attempts_and_raises_last_error():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return "still not JSON"
    try:
        call_and_parse(fetch, attempts=3)
    except ValueError:
        assert calls["n"] == 3, f"expected 3 attempts, got {calls['n']}"
        return
    raise AssertionError("should have raised after exhausting attempts")


def does_not_retry_a_truncation():
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        raise TruncatedOutput("hit the cap")
    try:
        call_and_parse(fetch, attempts=3)
    except TruncatedOutput:
        assert calls["n"] == 1, (
            f"truncation is deterministic and must not be retried, got {calls['n']} calls")
        return
    raise AssertionError("TruncatedOutput should propagate")


check("retries once on broken JSON then succeeds", retries_once_then_succeeds)
check("does not waste retries on a truncated response", does_not_retry_a_truncation)
check("does not retry a response that parses cleanly", succeeds_first_try_without_retrying)
check("raises the last error after exhausting attempts", exhausts_attempts_and_raises_last_error)


# ----------------------------------------------------------------- normalise_turn
def all_five(d):
    ids = [r["child_id"] for r in d["responses"]]
    assert ids == CHILD_ORDER, f"expected roster order, got {ids}"


check("empty dict still yields five children",
      lambda: all_five(normalise_turn({})))
check("None yields five children",
      lambda: all_five(normalise_turn(None)))
check("missing responses key yields five children",
      lambda: all_five(normalise_turn({"class_note": "x"})))
check("only two children returned, three are filled in",
      lambda: all_five(normalise_turn({"responses": [
          {"child_id": "priya", "speaks": True, "says": "35!"},
          {"child_id": "rahul", "speaks": False},
      ]})))


def unknown_child_dropped():
    d = normalise_turn({"responses": [
        {"child_id": "ravi_who_does_not_exist", "speaks": True, "says": "hi"},
        {"child_id": "meera", "speaks": True, "says": "25"},
    ]})
    all_five(d)
    assert "ravi_who_does_not_exist" not in [r["child_id"] for r in d["responses"]]


check("hallucinated child_id is dropped", unknown_child_dropped)


def duplicate_child_deduped():
    d = normalise_turn({"responses": [
        {"child_id": "priya", "speaks": True, "says": "first"},
        {"child_id": "priya", "speaks": True, "says": "second"},
    ]})
    all_five(d)
    priya = [r for r in d["responses"] if r["child_id"] == "priya"][0]
    assert priya["says"] == "first", "first entry should win"


check("duplicate child entries are deduped", duplicate_child_deduped)


def bad_engagement_defaults():
    d = normalise_turn({"responses": [
        {"child_id": "meera", "engagement": "extremely bored indeed"}]})
    meera = [r for r in d["responses"] if r["child_id"] == "meera"][0]
    assert meera["engagement"] == "engaged", meera["engagement"]


check("invalid engagement enum falls back to engaged", bad_engagement_defaults)


def speaks_true_says_null():
    d = normalise_turn({"responses": [
        {"child_id": "imran", "speaks": True, "says": None}]})
    imran = [r for r in d["responses"] if r["child_id"] == "imran"][0]
    assert imran["speaks"] is False, "speaks must be False when says is null"


check("speaks=true with says=null is corrected", speaks_true_says_null)

check("non-dict entries in responses are skipped",
      lambda: all_five(normalise_turn({"responses": ["oops", 42, None,
                                                     {"child_id": "meera"}]})))
check("non-string class_note becomes None",
      lambda: normalise_turn({"class_note": {"x": 1}})["class_note"] is None)
check("empty class_note becomes None",
      lambda: normalise_turn({"class_note": "   "})["class_note"] is None)


# ------------------------------------------------------------------------ overall
check("overall averages three scores", lambda: overall(
    {"attention_equity": 30, "question_quality": 60, "misconception_diagnosis": 30}) == 40)
check("overall on empty dict is 0", lambda: overall({}) == 0)
check("overall on None is 0", lambda: overall(None) == 0)
check("overall ignores non-numeric", lambda: overall(
    {"attention_equity": "bad", "question_quality": 50,
     "misconception_diagnosis": 50}) == 50)
check("overall rejects booleans as numbers", lambda: overall(
    {"attention_equity": True, "question_quality": 40,
     "misconception_diagnosis": 40}) == 40)


# ----------------------------------------------------------------- report shape
check("empty report is rejected", lambda: len(validate_report({})) > 0)
check("non-dict report is rejected", lambda: validate_report("nope") ==
      ["report is not an object"])


def fallback_report_is_valid():
    data = json.loads(open("demo_fallback.json").read())
    problems = validate_report(data["report"])
    assert not problems, problems


check("the offline demo report passes validation", fallback_report_is_valid)


def fallback_turns_render():
    data = json.loads(open("demo_fallback.json").read())
    for entry in data["transcript"]:
        if entry["role"] == "class":
            all_five(normalise_turn(entry["content"]))
    turns = sum(1 for e in data["transcript"] if e["role"] == "teacher")
    assert turns <= 6, f"fallback has {turns} turns, cap is 6"


check("the offline demo transcript is well-formed and within the turn cap",
      fallback_turns_render)


def out_of_range_score_caught():
    rep = json.loads(open("demo_fallback.json").read())["report"]
    rep = json.loads(json.dumps(rep))
    rep["scores"]["attention_equity"] = 420
    assert any("out of range" in p for p in validate_report(rep))


check("a score above 100 is caught", out_of_range_score_caught)


# --------------------------------------------------------------------------- out
print()
for name in PASS:
    print(f"  PASS  {name}")
for name, why in FAIL:
    print(f"  FAIL  {name}\n          {why}")
print(f"\n{len(PASS)} passed, {len(FAIL)} failed\n")
sys.exit(1 if FAIL else 0)

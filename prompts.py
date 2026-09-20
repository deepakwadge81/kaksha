"""Prompt construction for KAKSHA. Two calls: the turn engine, and the coaching report."""

import json
from personas import CHILDREN, LESSON


def _roster_block() -> str:
    lines = []
    for c in CHILDREN:
        lines.append(
            f"""
### {c['name']}  (id: {c['id']})
- Reading level (ASER band): {c['aser_band']}
- Actual level: {c['hidden_level']}
- Hidden misconception: {c['hidden_misconception']}
- Behaviour pattern: {c['behaviour']}
""".strip()
        )
    return "\n\n".join(lines)


TURN_SCHEMA = """{
  "responses": [
    {
      "child_id": "rahul | priya | anjali | imran | meera",
      "speaks": true,
      "says": "what the child says out loud, or null if silent",
      "behaviour": "what the child physically does, 3-10 words",
      "internal_state": "what the child is actually thinking, 4-14 words, never spoken aloud",
      "engagement": "engaged | drifting | lost"
    }
  ],
  "class_note": "one short line of ambient classroom detail, or null"
}"""


def turn_system_prompt(language: str = "Hinglish") -> str:
    lang_rule = (
        "Children speak in simple Hindi-English code-mixed speech, the way real Grade 3 "
        "government school children in India do. Example: \"Didi, answer 35 hai na?\""
        if language == "Hinglish"
        else "Children speak in simple English, the way real Grade 3 children do."
    )

    return f"""You are simulating a real {LESSON['grade']} classroom in India so that a teacher can practise.

LESSON
Subject: {LESSON['subject']}
Topic: {LESSON['topic']}
Setting: {LESSON['context']}

THE FIVE CHILDREN
You play all five. Each has a hidden actual level and a hidden misconception that the
teacher cannot see. You must never reveal these directly — they surface only through
what the child says and does.

{_roster_block()}

SIMULATION RULES
1. You return a response object for all five children every turn, but most turns only
   two to four of them actually speak. Set "speaks": false and "says": null for the rest.
   Silence is a real and important response.
2. Wrong answers must follow deterministically from that child's hidden misconception.
   Never produce a random wrong answer. If Priya is asked 52 - 27 she says 35, every time,
   because her bug is consistent. Consistency is what makes the misconception diagnosable.
3. A child's misconception only surfaces if the teacher asks something that would expose it.
   Imran's zero bug stays invisible until a problem with a zero appears. If the teacher
   never probes, the bug never shows — and that is the lesson.
4. Track engagement across turns. A child who is ignored, or who is unchallenged, drifts
   and then is lost. Rahul drifts after two turns without being addressed. Meera drifts
   after three turns without harder work or a chance to explain. Once lost, a child does
   not re-engage on their own — the teacher has to do something deliberate.
5. Children do not narrate their confusion. They go quiet, they guess, they copy, they
   say "haan didi" when they have understood nothing. Never have a child helpfully
   announce "I don't understand place value."
6. Keep every spoken line short — 3 to 14 words. {lang_rule}
7. "internal_state" is the child's real thought and is shown only to the teacher
   afterwards as a coaching aid. Make it honest and specific.
8. Do not coach, hint, praise or comment as a narrator. You are only the children.

OUTPUT
Return ONLY a JSON object matching this schema. No markdown fences, no commentary.

{TURN_SCHEMA}"""


def turn_user_message(transcript: list, teacher_line: str) -> str:
    history = []
    for entry in transcript:
        if entry["role"] == "teacher":
            history.append(f"TEACHER: {entry['content']}")
        else:
            for r in entry["content"].get("responses", []):
                if r.get("speaks") and r.get("says"):
                    history.append(f"  {r['child_id'].upper()}: {r['says']}")
                elif r.get("behaviour"):
                    history.append(f"  ({r['child_id']} — {r['behaviour']})")

    history_text = "\n".join(history) if history else "(the lesson has not started yet)"

    return f"""LESSON SO FAR
{history_text}

THE TEACHER NOW SAYS OR DOES:
{teacher_line}

Respond as the classroom. JSON only."""


REPORT_SCHEMA = """{
  "headline": "one blunt sentence naming the single biggest thing that went wrong",
  "scores": {
    "attention_equity": 0,
    "question_quality": 0,
    "misconception_diagnosis": 0
  },
  "attention": [
    {"child_id": "...", "times_addressed": 0, "times_spoke": 0, "note": "one short line"}
  ],
  "misconceptions": [
    {
      "child_id": "...",
      "hidden_misconception": "restate it plainly",
      "surfaced": true,
      "evidence": "what in the transcript did or did not reveal it"
    }
  ],
  "moments": [
    {"turn": 1, "what_happened": "...", "what_to_try": "the specific alternative move"}
  ],
  "next_time": ["one concrete thing", "one more concrete thing"]
}"""


def report_prompt(transcript: list) -> str:
    lines = []
    turn = 0
    for entry in transcript:
        if entry["role"] == "teacher":
            turn += 1
            lines.append(f"\n[Turn {turn}] TEACHER: {entry['content']}")
        else:
            for r in entry["content"].get("responses", []):
                c = r["child_id"]
                if r.get("speaks") and r.get("says"):
                    lines.append(f"    {c}: \"{r['says']}\"  ({r.get('behaviour','')})")
                else:
                    lines.append(f"    {c}: [silent] ({r.get('behaviour','')})")
                lines.append(f"       thinking: {r.get('internal_state','')}")

    return f"""You are an instructional coach reviewing a practice lesson. You saw everything,
including each child's hidden level and hidden misconception, which the teacher could not see.

THE FIVE CHILDREN AND WHAT WAS HIDDEN FROM THE TEACHER
{_roster_block()}

FULL TRANSCRIPT
{''.join(l + chr(10) for l in lines)}

WRITE THE COACHING REPORT.

Be specific and evidence-based. Quote or cite turn numbers. Do not give generic advice
like "engage all students" — say which child, at which turn, and what to have done instead.
Be direct but not cruel; this is a teacher practising, and the point is the next attempt.

Scoring guidance:
- attention_equity: how evenly teacher attention was distributed, weighted by need.
  Over-calling the children who already understand is the classic failure.
- question_quality: were questions open and diagnostic, or closed and confirmatory?
  Did the teacher ask "why" or only "what"?
- misconception_diagnosis: of the hidden misconceptions that could have surfaced,
  how many did the teacher actually surface and correctly identify?

Return ONLY a JSON object matching this schema. No markdown fences, no commentary.

{REPORT_SCHEMA}"""

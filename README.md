# KAKSHA 🪑 — a flight simulator for teachers

**Track: Breakthrough.**

Claude plays five Grade 3 children in an Indian government school. Each has a hidden
learning level and a hidden misconception. You teach blind, six turns. Then the X-ray
turns on — the lesson replays with what every child was actually thinking — and Claude,
who could see everything you couldn't, tells you who you lost and why.

A trainee teacher can fail this classroom a hundred times before ever meeting a real child.

---

## Why

Indian in-service teacher training runs at enormous scale — NISHTHA alone has touched
4.2 million teacher-instances — and independent evaluation (Oxford/RECOUP, Azim Premji
University) finds **no significant effect on Grade 5 maths outcomes**. The system
optimises for *training delivered*, not *practice changed*. There is nowhere safe to
practise, and DIETs, the institutions meant to provide it, carry 30–50% faculty vacancies.

The five children aren't invented. Reading levels use the **ASER 2024** bands, and the
spread across them is the documented finding that learning levels inside one nominal
grade span about **seven grade-equivalents**. The maths bugs are the classic documented
subtraction errors: smaller-from-larger, and borrowing across a zero.

No real child data. No recording. No consent problem. That's the point.

---

## Run it

```bash
pip install -r requirements.txt
mkdir -p .streamlit && echo 'ANTHROPIC_API_KEY = "sk-ant-..."' > .streamlit/secrets.toml
streamlit run app.py
```

## Deploy

1. Push to a **public** GitHub repo.
2. share.streamlit.io → New app → pick the repo → main file `app.py`.
3. Advanced settings → Secrets → **leave empty**. A Community Cloud app has no
   login, so a key in its secrets is a key anyone with the URL can spend. With no
   secret set, the app opens in Demo mode (a full recorded lesson, free) and a
   visitor who wants to teach live pastes their own key into the sidebar.
4. Deploy.

Put `ANTHROPIC_API_KEY = "sk-ant-..."` in Secrets **only** for a private or
short-lived demo where you accept that every visitor spends your credits — and
set a spend limit on that key in the Anthropic Console if you do.

`.gitignore` already excludes `.streamlit/secrets.toml`. The key never enters the repo.

---

## Tests

```bash
python test_offline.py      # 36 checks, no API key, free
ANTHROPIC_API_KEY=sk-... python test_live.py     # ~20 calls, a few cents
```

**`test_offline.py`** answers *will it crash in front of the judges?* — fenced JSON,
prose preamble, truncated output, hallucinated `child_id`s, duplicate children,
`speaks: true` with `says: null`, invalid engagement enums, out-of-range scores,
and the retry/truncation branches of `call_and_parse`.
The UI is guaranteed five well-formed children per turn no matter what comes back.

**`test_live.py`** answers *does the simulation actually behave?*

| Check | What it proves |
|---|---|
| Priya consistency | 52−27 returns 35 every run — the bug is deterministic, so it's diagnosable |
| Priya under probing | Asking for the ones column surfaces the method |
| Priya after correction | Handing her the right answer leaves the bug intact |
| Imran ordinary sum | Zero bug stays hidden — he looks fine |
| Imran on 40−18 | Zero bug surfaces only when probed |
| Rahul | Never confidently answers a whole-class question |
| Rahul drift | Drifting or lost after three unaddressed turns |
| Meera drift | Drifting or lost after three unchallenged turns |
| Meera challenged | Stays engaged when given harder work |
| Injection ×2 | Hidden profiles don't leak; children stay in character |
| Robustness ×3 | Nonsense, very long input, Hindi input |
| Report ×2 | Schema validates; a lesson that only calls Imran scores low on equity |

Run a subset: `python test_live.py priya imran`.

---

## How it works

Two Claude calls, both strict JSON.

**Turn engine.** The system prompt carries all five hidden profiles and the simulation
rules, sent as a cached block so turn two onward is cheaper and faster. It returns a
response object for all five children every turn — most stay silent, because silence is
a real response. Wrong answers derive deterministically from that child's hidden
misconception, which is what makes the bug diagnosable rather than random. Engagement
decays across turns.

**Coaching report.** Transcript plus hidden profiles go back in. Out comes attention
equity per child, question quality, misconception diagnosis, three moments with the
alternative move, and two things to try next time.

**On `max_tokens`.** Sonnet 5 thinks by default, and thinking tokens count against
`max_tokens` — so a cap sized for a non-thinking model silently truncates the JSON
mid-string, which then surfaces as a bogus parse error. The caps here (8K turn,
16K report) leave room for both. `call_claude` raises `TruncatedOutput` on
`stop_reason == "max_tokens"` so a starved cap is named rather than guessed at, and
`call_and_parse` retries genuine malformed JSON once but never retries a truncation,
which is deterministic.

| File | What |
|---|---|
| `app.py` | Streamlit UI, turn loop, X-ray reveal, leaderboard |
| `core.py` | Parsing, normalisation, validation — no Streamlit, fully testable |
| `personas.py` | The five children |
| `prompts.py` | Both prompts and both JSON schemas |
| `demo_fallback.json` | Pre-recorded session for offline demo mode |

---

## Demoing

Sidebar has **Demo mode (offline)** — replays a recorded session with zero network
calls. Use it if the venue wifi dies. The model name is editable in the sidebar; swap it
if you hit a 404.

The leaderboard persists in `leaderboard.json` next to the app, so a queue of people can
compete. It resets on redeploy — that's fine for a hackathon.

---

## Honest limits

- One lesson (Grade 3 subtraction with borrowing), one class of five, both hardcoded.
- The children are calibrated to published distributions, not to any observed classroom.
  It's a practice environment, not an evidence claim.
- Hinglish output reads well but hasn't been validated by teachers. Regional languages
  beyond Hindi are untested.

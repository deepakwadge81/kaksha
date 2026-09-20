"""
KAKSHA — a flight simulator for teachers.

Claude plays five Grade 3 children, each with a hidden learning level and a hidden
misconception. You teach blind. Then the X-ray turns on and you see what you walked past.
"""

import json
import os
from pathlib import Path

import anthropic
import streamlit as st

from core import TruncatedOutput, call_and_parse, normalise_turn, overall
from personas import CHILDREN, CHILDREN_BY_ID, LESSON
from prompts import report_prompt, turn_system_prompt, turn_user_message

DEFAULT_MODEL = "claude-sonnet-5"
MAX_TURNS = 6
HERE = Path(__file__).parent
FALLBACK_PATH = HERE / "demo_fallback.json"
BOARD_PATH = HERE / "leaderboard.json"

st.set_page_config(page_title="KAKSHA", page_icon="🪑", layout="wide")

st.markdown(
    """
<style>
.block-container { padding-top: 2rem; max-width: 1150px; }
.kid { border: 1px solid rgba(128,128,128,.28); border-radius: 14px;
       padding: .7rem .6rem; text-align: center; height: 100%; }
.kid.engaged  { border-color: #2e9e5b; background: rgba(46,158,91,.07); }
.kid.drifting { border-color: #d19a29; background: rgba(209,154,41,.09); }
.kid.lost     { border-color: #b03636; background: rgba(176,54,54,.09); opacity:.72; }
.kid .face { font-size: 1.9rem; line-height: 1.9rem; }
.kid .nm { font-weight: 600; margin-top: .2rem; }
.kid .bd { font-size: .72rem; opacity: .65; }
.kid .st { font-size: .68rem; text-transform: uppercase; letter-spacing: .04em;
           margin-top: .35rem; font-weight: 600; }
.says { margin: .15rem 0 .1rem 0; }
.beh  { font-size: .82rem; opacity: .7; font-style: italic; }
.silent { font-size: .82rem; opacity: .55; font-style: italic; }
.xray { font-size: .8rem; font-style: italic; margin-left: .2rem; padding: .18rem .5rem;
        border-left: 2px solid #7b5cd6; background: rgba(123,92,214,.10);
        border-radius: 0 5px 5px 0; display: inline-block; margin-top: .2rem; }
.tline { background: rgba(128,128,128,.10); border-left: 3px solid #6a6a6a;
         padding: .5rem .75rem; border-radius: 6px; margin: 1rem 0 .6rem 0; }
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- plumbing
def get_api_key():
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


@st.cache_resource(show_spinner=False)
def get_client(key: str):
    return anthropic.Anthropic(api_key=key)


def call_claude(client, model, system, user, max_tokens=8000):
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    if resp.stop_reason == "max_tokens":
        # Thinking-by-default models spend part of max_tokens before writing any
        # JSON, so a cap that looks generous can still truncate the payload.
        # Name it plainly here rather than letting it surface as a JSON error.
        details = getattr(resp.usage, "output_tokens_details", None)
        thinking = getattr(details, "thinking_tokens", None)
        raise TruncatedOutput(
            f"hit the {max_tokens:,}-token cap"
            + (f" ({thinking:,} spent thinking)" if thinking else "")
            + " — raise max_tokens for this call"
        )
    return "".join(b.text for b in resp.content if b.type == "text")


def load_board():
    try:
        data = json.loads(BOARD_PATH.read_text())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_board(board):
    try:
        BOARD_PATH.write_text(json.dumps(board[:10], indent=2))
    except Exception:
        pass


def init_state():
    st.session_state.setdefault("transcript", [])
    st.session_state.setdefault("engagement", {c["id"]: "engaged" for c in CHILDREN})
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("error", None)
    st.session_state.setdefault("saved", False)


init_state()


# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### KAKSHA")
    st.caption("Practise on simulated children, not real ones.")

    key = get_api_key()
    if not key:
        key = st.text_input("Anthropic API key", type="password")
    st.markdown("🟢 API key loaded" if key else "🔴 No API key")

    model = st.text_input("Model", value=DEFAULT_MODEL, help="Swap if you hit a 404.")
    language = st.radio("Children speak", ["Hinglish", "English"], horizontal=True)
    demo_mode = st.toggle("Demo mode (offline)", value=False,
                          help="Replays a recorded session. Use if the wifi dies.")

    st.divider()
    st.markdown(f"**{LESSON['grade']} · {LESSON['subject']}**")
    st.caption(LESSON["topic"])

    board = load_board()
    if board:
        st.divider()
        st.markdown("**Leaderboard**")
        for i, row in enumerate(board[:5], 1):
            st.markdown(f"{i}. **{row.get('score', 0)}** — {row.get('name', '?')}")

    if st.button("New lesson", use_container_width=True):
        for k in ("transcript", "engagement", "report", "error", "saved"):
            st.session_state.pop(k, None)
        init_state()
        st.rerun()


# --------------------------------------------------------------------------- header
st.title("KAKSHA 🪑")
st.markdown(
    "**Five children. Each has a hidden learning level and a hidden misconception.** "
    "You get six turns. You teach blind — then the X-ray turns on."
)

if demo_mode and FALLBACK_PATH.exists() and not st.session_state.transcript:
    saved = json.loads(FALLBACK_PATH.read_text())
    st.session_state.transcript = saved["transcript"]
    st.session_state.report = saved.get("report")
    for entry in st.session_state.transcript:
        if entry["role"] == "class":
            for r in entry["content"].get("responses", []):
                st.session_state.engagement[r["child_id"]] = r.get("engagement", "engaged")

xray_on = st.session_state.report is not None


# --------------------------------------------------------------------------- the class
for col, child in zip(st.columns(5), CHILDREN):
    state = st.session_state.engagement.get(child["id"], "engaged")
    col.markdown(
        f"""<div class="kid {state}">
              <div class="face">{child['avatar']}</div>
              <div class="nm">{child['name']}</div>
              <div class="bd">{child['aser_band']}</div>
              <div class="st">● {state}</div>
            </div>""",
        unsafe_allow_html=True,
    )

st.caption(
    "Reading levels follow the ASER 2024 bands. The spread across these five is the "
    "documented within-grade dispersion of about seven grade-equivalents in one classroom."
)

if xray_on:
    st.success(
        "**X-ray on.** The lesson is replayed below with what each child was actually "
        "thinking — the thing a real teacher never gets to see.",
        icon="🔍",
    )

st.divider()


# --------------------------------------------------------------------------- transcript
def render_turn(entry, xray: bool):
    if entry["role"] == "teacher":
        st.markdown(f"<div class='tline'><b>You</b> — {entry['content']}</div>",
                    unsafe_allow_html=True)
        return

    data = entry["content"]
    for r in data.get("responses", []):
        child = CHILDREN_BY_ID.get(r.get("child_id"))
        if not child:
            continue
        spoke = r.get("speaks") and r.get("says")
        thought = (r.get("internal_state") or "").strip()
        if not spoke and not r.get("behaviour") and not (xray and thought):
            continue

        c1, c2 = st.columns([1, 11])
        c1.markdown(
            f"<div style='font-size:1.5rem;text-align:center'>{child['avatar']}</div>",
            unsafe_allow_html=True,
        )
        with c2:
            if spoke:
                st.markdown(
                    f"<div class='says'><b>{child['name']}:</b> {r['says']}</div>"
                    f"<div class='beh'>{r.get('behaviour','')}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='silent'><b>{child['name']}</b> — "
                    f"{r.get('behaviour','says nothing')}</div>",
                    unsafe_allow_html=True,
                )
            if xray and thought:
                st.markdown(f"<div class='xray'>thinking: {thought}</div>",
                            unsafe_allow_html=True)
    if data.get("class_note"):
        st.caption(data["class_note"])


for entry in st.session_state.transcript:
    render_turn(entry, xray_on)

if not st.session_state.transcript:
    st.info("Open the lesson however you like. A good first move is a question — "
            "but watch who answers it.", icon="👋")

if st.session_state.error:
    st.error(st.session_state.error)


# --------------------------------------------------------------------------- input
turns = sum(1 for e in st.session_state.transcript if e["role"] == "teacher")
at_cap = turns >= MAX_TURNS

if not st.session_state.report:
    st.progress(min(turns / MAX_TURNS, 1.0),
                text=f"Turn {min(turns + 1, MAX_TURNS)} of {MAX_TURNS}")

teacher_line = st.chat_input(
    "Lesson over — end it below." if at_cap else "Say or do something as the teacher…",
    disabled=demo_mode or at_cap or bool(st.session_state.report),
)

if teacher_line and teacher_line.strip():
    if not key:
        st.session_state.error = "Add an Anthropic API key in the sidebar first."
        st.rerun()

    st.session_state.error = None
    line = teacher_line.strip()[:2000]
    st.session_state.transcript.append({"role": "teacher", "content": line})
    try:
        with st.spinner("the class responds…"):
            parsed, _raw = call_and_parse(lambda: call_claude(
                get_client(key), model,
                turn_system_prompt(language),
                turn_user_message(st.session_state.transcript[:-1], line),
            ))
            data = normalise_turn(parsed)
        st.session_state.transcript.append({"role": "class", "content": data})
        for r in data["responses"]:
            st.session_state.engagement[r["child_id"]] = r["engagement"]
    except Exception as e:
        st.session_state.transcript.pop()
        st.session_state.error = f"Turn failed — try again. ({type(e).__name__}: {e})"
    st.rerun()


# --------------------------------------------------------------------------- report
if turns >= 1 and not st.session_state.report and not demo_mode:
    left, right = st.columns([3, 1])
    left.markdown(f"**{turns} of {MAX_TURNS} turns taught.**"
                  + ("  You're out of turns." if at_cap else ""))
    if right.button("End lesson →", type="primary", use_container_width=True):
        try:
            with st.spinner("your coach is reviewing the lesson…"):
                parsed, _raw = call_and_parse(lambda: call_claude(
                    get_client(key), model,
                    "You are a rigorous, specific instructional coach. Return JSON only.",
                    report_prompt(st.session_state.transcript),
                    max_tokens=16000,
                ))
                st.session_state.report = parsed
            st.rerun()
        except Exception as e:
            st.error(f"Report failed: {type(e).__name__}: {e}")


rep = st.session_state.report
if rep:
    st.divider()
    st.subheader("Coaching report")
    st.markdown(f"#### {rep.get('headline','')}")

    s = rep.get("scores", {}) or {}
    total = overall(s)
    a, b, c, d = st.columns(4)
    a.metric("Attention equity", f"{s.get('attention_equity', 0)}")
    b.metric("Question quality", f"{s.get('question_quality', 0)}")
    c.metric("Misconceptions caught", f"{s.get('misconception_diagnosis', 0)}")
    d.metric("Overall", f"{total}/100")

    board = load_board()
    if board:
        best = board[0]
        st.markdown(
            f"**Best score so far: {best.get('score')} — {best.get('name')}.** "
            + ("You're top of the board. 🏆" if total >= best.get("score", 0)
               else "Think you can beat it?")
        )

    if not st.session_state.saved and not demo_mode:
        n1, n2 = st.columns([3, 1])
        who = n1.text_input("Your name", label_visibility="collapsed",
                            placeholder="Your name for the leaderboard")
        if n2.button("Add my score", use_container_width=True) and who.strip():
            board.append({"name": who.strip()[:24], "score": total})
            board.sort(key=lambda r: -r.get("score", 0))
            save_board(board)
            st.session_state.saved = True
            st.rerun()

    st.markdown("##### Who got your attention")
    for row in rep.get("attention", []) or []:
        child = CHILDREN_BY_ID.get(row.get("child_id"), {})
        st.markdown(
            f"{child.get('avatar','')} **{child.get('name', row.get('child_id'))}** — "
            f"addressed {row.get('times_addressed', 0)}×, spoke {row.get('times_spoke', 0)}×. "
            f"{row.get('note','')}"
        )

    st.markdown("##### What you missed")
    for m in rep.get("misconceptions", []) or []:
        child = CHILDREN_BY_ID.get(m.get("child_id"), {})
        icon = "✅" if m.get("surfaced") else "❌"
        st.markdown(
            f"{icon} **{child.get('name', m.get('child_id'))}** — "
            f"*{m.get('hidden_misconception','')}*  \n"
            f"<span class='beh'>{m.get('evidence','')}</span>",
            unsafe_allow_html=True,
        )

    st.markdown("##### Three moments")
    for mo in rep.get("moments", []) or []:
        with st.expander(f"Turn {mo.get('turn','?')} — {mo.get('what_happened','')}"):
            st.markdown(f"**Try instead:** {mo.get('what_to_try','')}")

    st.markdown("##### Next time")
    for n in rep.get("next_time", []) or []:
        st.markdown(f"- {n}")

    st.download_button(
        "Save this session",
        json.dumps({"transcript": st.session_state.transcript, "report": rep}, indent=2),
        file_name="kaksha_session.json", mime="application/json",
    )

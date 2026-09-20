"""
KAKSHA — the simulated classroom.

The five children are not invented. Their spread is the NBER/Mindspark finding
that learning levels inside a single nominal grade span roughly seven
grade-equivalents, rendered as five children. Reading levels use the ASER 2024
bands. The maths misconceptions are the classic documented subtraction bugs.
"""

LESSON = {
    "grade": "Grade 3",
    "subject": "Mathematics",
    "topic": "Two-digit subtraction with borrowing (e.g. 52 - 27)",
    "context": (
        "A government primary school in India. One teacher, no teaching assistant, "
        "a blackboard, 40 minutes."
    ),
}

CHILDREN = [
    {
        "id": "rahul",
        "name": "Rahul",
        "avatar": "🧒🏽",
        "aser_band": "Letter level",
        "public_profile": "Quiet. Rarely volunteers.",
        # --- hidden from the teacher, given to the model ---
        "hidden_level": (
            "Two full years behind. Recognises letters but cannot read words. "
            "In maths he can count objects to 20 but loses track past that. He has "
            "no concept of place value at all, so borrowing is meaningless to him — "
            "he is not making an error in the procedure, he is nowhere near the procedure."
        ),
        "hidden_misconception": (
            "Does not understand that the '5' in 52 means five tens. Treats every "
            "digit as a separate small number."
        ),
        "behaviour": (
            "Answers only if addressed by name, and even then often after a long pause "
            "or with silence. Looks at the floor. Never says he doesn't understand — "
            "he says nothing. If ignored for two turns he stops tracking the lesson entirely."
        ),
    },
    {
        "id": "priya",
        "name": "Priya",
        "avatar": "👧🏽",
        "aser_band": "Word level",
        "public_profile": "Confident. Always has an answer ready.",
        "hidden_level": "Roughly one year behind, but it is hidden by her confidence.",
        "hidden_misconception": (
            "The smaller-from-larger bug — the single most documented subtraction error. "
            "In any column she subtracts the smaller digit from the larger one regardless "
            "of which is on top. For 52 - 27 she does 5-2=3 and 7-2=5 and answers 35. "
            "She is fast, fluent and completely wrong, and she will defend the answer "
            "because the procedure feels consistent to her."
        ),
        "behaviour": (
            "First hand up. Answers loudly and quickly. If told she is wrong without being "
            "shown why, she repeats the same method louder. Only a question that makes her "
            "walk through one column aloud will expose the bug."
        ),
    },
    {
        "id": "anjali",
        "name": "Anjali",
        "avatar": "👧🏾",
        "aser_band": "Std I text",
        "public_profile": "At grade level. Does the work.",
        "hidden_level": "Genuinely at grade level and mostly secure with borrowing.",
        "hidden_misconception": (
            "No real conceptual bug, but she is unsure of herself. When she hesitates she "
            "glances at Imran's slate and copies. So a correct answer from Anjali is "
            "sometimes not hers, which makes her look more secure than she is."
        ),
        "behaviour": (
            "Polite, reliable, easy to call on — which is exactly why teachers over-call her. "
            "Sometimes pauses and looks sideways before answering; that pause is the tell."
        ),
    },
    {
        "id": "imran",
        "name": "Imran",
        "avatar": "🧑🏽",
        "aser_band": "Std I text",
        "public_profile": "Eager. Talks a lot.",
        "hidden_level": "At grade level for ordinary borrowing.",
        "hidden_misconception": (
            "The zero bug. He handles 52 - 27 fine, but breaks on a zero in the top number. "
            "For 40 - 18 he cannot borrow from the 0 and either writes 38 or freezes. "
            "The bug only appears if a problem with a zero is put in front of him."
        ),
        "behaviour": (
            "Blurts answers before being called on and takes up most of the airtime. "
            "Not naughty, just fast. If the teacher keeps taking his shouted answers, "
            "the quieter children stop trying."
        ),
    },
    {
        "id": "meera",
        "name": "Meera",
        "avatar": "👧",
        "aser_band": "Std II text",
        "public_profile": "Finishes early.",
        "hidden_level": (
            "Two years ahead. Already comfortable with three-digit subtraction and "
            "mental strategies."
        ),
        "hidden_misconception": (
            "None in subtraction. Her risk is not error, it is waste — she is given "
            "nothing to do."
        ),
        "behaviour": (
            "Solves anything set in under ten seconds, then waits. If not given something "
            "harder, or asked to explain her thinking, or asked to help Rahul, she "
            "disengages within about three turns — starts drawing, talks to a neighbour, "
            "stops answering. She will not complain. She just leaves."
        ),
    },
]

CHILDREN_BY_ID = {c["id"]: c for c in CHILDREN}

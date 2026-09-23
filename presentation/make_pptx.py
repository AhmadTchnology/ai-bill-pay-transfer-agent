"""Generates presentation/slides.pptx — the two submission slides.
Run:  py presentation/make_pptx.py"""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BG = RGBColor(0x0F, 0x14, 0x20)
PANEL = RGBColor(0x1A, 0x21, 0x30)
ACCENT = RGBColor(0x2D, 0xD4, 0xA7)
GOLD = RGBColor(0xF4, 0xB8, 0x60)
DANGER = RGBColor(0xE0, 0x5C, 0x6A)
TEXT = RGBColor(0xE8, 0xED, 0xF5)
MUTED = RGBColor(0x8B, 0x97, 0xAB)

OUT = Path(__file__).parent / "slides.pptx"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def slide():
    s = prs.slides.add_slide(BLANK)
    bg = s.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG
    return s


def box(s, x, y, w, h, fill=PANEL, line=None):
    from pptx.enum.shapes import MSO_SHAPE

    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    if line:
        sh.line.color.rgb = line
        sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def txt(shape, lines, align=PP_ALIGN.LEFT):
    """lines: list of (text, size, color, bold) or (text, size, color, bold, level)."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.16)
    tf.margin_right = Inches(0.12)
    tf.margin_top = Inches(0.10)
    first = True
    for item in lines:
        text, size, color, bold = item[:4]
        space_after = item[4] if len(item) > 4 else 4
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = text
        f = r.font
        f.size = Pt(size)
        f.color.rgb = color
        f.bold = bold
        f.name = "Segoe UI"


# ================= SLIDE 1 =================
s1 = slide()

title = box(s1, Inches(0.55), Inches(0.45), Inches(12.2), Inches(1.35), fill=BG)
txt(
    title,
    [
        ("SLIDE 1 — OUR APPROACH", 13, ACCENT, True, 2),
        ("Bill Pay & Transfer Agent — وكيل الدفع والتحويل", 30, TEXT, True, 4),
        (
            "One spoken or typed sentence in Iraqi Arabic becomes a completed, human-confirmed transaction — or an honest explanation why not.",
            13,
            MUTED,
            False,
            0,
        ),
    ],
)

# left column
l1 = box(s1, Inches(0.55), Inches(2.0), Inches(6.1), Inches(2.15))
txt(
    l1,
    [
        ("THE USER WE DESIGN FOR", 13, ACCENT, True, 6),
        (
            "▸  Less comfortable with smartphones: multi-tap wallet flows get abandoned or mis-tapped.",
            13,
            TEXT,
            False,
            4,
        ),
        (
            '▸  Speaks dialect, not formal Arabic — "حول 50 الف لأحمد", "سدد فاتورة النت".',
            13,
            TEXT,
            False,
            4,
        ),
        (
            "▸  Wants zero screens: one sentence, one confirmation, done.",
            13,
            TEXT,
            False,
            0,
        ),
    ],
)

l2 = box(s1, Inches(0.55), Inches(4.35), Inches(6.1), Inches(2.6))
txt(
    l2,
    [
        ("END TO END", 13, ACCENT, True, 6),
        (
            "🎙 Voice / text → Whisper STT → GLM-5.3 NLU (proposes only) →",
            13,
            TEXT,
            False,
            3,
        ),
        ("Resolver: ask, never guess → Confirmation card →", 13, TEXT, False, 3),
        (
            'Rule-checked "نعم" → Idempotent executor → Mock wallet → Honest result',
            13,
            TEXT,
            False,
            5,
        ),
        (
            "Missing info? It asks. Ambiguous? A numbered question, never a coin flip. Two requests in one sentence? One card, all-or-nothing.",
            12,
            MUTED,
            False,
            0,
        ),
    ],
)

# right column
r1 = box(s1, Inches(6.85), Inches(2.0), Inches(5.9), Inches(3.35))
txt(
    r1,
    [
        ("MODELS, TOOLS & DATA", 13, ACCENT, True, 6),
        (
            'NLU ("brain"):  z-ai/GLM-5.3 via NVIDIA NIM — extracts structured intent; no execution power',
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "Voice (stretch):  faster-whisper large-v3-turbo, int8 CPU (~2 GB), Iraqi prompt + hotwords",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "Stack:  FastAPI · SQLite · httpx · single-file JS chat UI",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            'Wallet data:  100% LLM-generated from a schema (15 contacts incl. 3 "Ahmeds", 7 billers) — no real records',
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "Test data:  LLM-drafted, hand-edited Iraqi dialect; held-out set written after freeze",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "Built with:  AI coding assistant (disclosed) + team review — see DISCLOSURE.md",
            12.5,
            TEXT,
            False,
            0,
        ),
    ],
)

r2 = box(s1, Inches(6.85), Inches(5.5), Inches(5.9), Inches(1.45), fill=BG, line=ACCENT)
txt(
    r2,
    [
        ("Golden rule: the LLM can only PROPOSE.", 14, ACCENT, True, 3),
        (
            'Money moves only from a designed state machine after a regex-checked human "نعم" — a hallucinated intent can never pay anyone.',
            13,
            TEXT,
            False,
            0,
        ),
    ],
)

# ================= SLIDE 2 =================
s2 = slide()

title2 = box(s2, Inches(0.55), Inches(0.45), Inches(12.2), Inches(1.25), fill=BG)
txt(
    title2,
    [
        ("SLIDE 2 — HOW WE PROVE IT WORKS", 13, ACCENT, True, 2),
        ("Evidence, not a demo", 30, TEXT, True, 3),
        (
            "Every run resets the wallet and checks bank-level invariants (balance delta, transaction count) — not just chat replies.",
            13,
            MUTED,
            False,
            0,
        ),
    ],
)

# stats row
stats = [
    (
        "58/58",
        ACCENT,
        "tuning set — live GLM-5.3 NLU\n55 Iraqi-dialect cases + 3 idempotency proofs",
    ),
    (
        "10/10",
        ACCENT,
        "held-out set — written after freeze,\nnever tuned on, run once · results committed",
    ),
    (
        "6/6",
        GOLD,
        'voice smoke — real mic format (webm/opus):\nspoken transfer → "نعم" → one debit',
    ),
    (
        "×2 same key",
        ACCENT,
        "same idempotency key submitted twice\n→ same transaction, debited once",
    ),
]
for i, (num, color, lab) in enumerate(stats):
    st = box(s2, Inches(0.55 + i * 3.07), Inches(1.95), Inches(2.87), Inches(1.25))
    tf = st.text_frame
    tf.word_wrap = True
    tf.margin_top = Inches(0.06)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = num
    r.font.size = Pt(24)
    r.font.bold = True
    r.font.color.rgb = color
    p2 = tf.add_paragraph()
    r2_ = p2.add_run()
    r2_.text = lab
    r2_.font.size = Pt(10.5)
    r2_.font.color.rgb = MUTED

# how we test
h1 = box(s2, Inches(0.55), Inches(3.4), Inches(6.1), Inches(1.7))
txt(
    h1,
    [
        ("HOW WE TEST", 13, ACCENT, True, 5),
        (
            "▸  Replay mode: recorded NLU pins the deterministic core — runs without an API key.",
            12.5,
            TEXT,
            False,
            3,
        ),
        (
            "▸  Live mode: the same 68 cases through real GLM-5.3 end-to-end.",
            12.5,
            TEXT,
            False,
            3,
        ),
        (
            "▸  Should-not-execute cases (cancel, vague reply, gibberish) verified to move ZERO money.",
            12.5,
            TEXT,
            False,
            3,
        ),
        (
            "▸  Voice tested with ar-IQ TTS fixtures — judges reproduce without a microphone.",
            12.5,
            TEXT,
            False,
            0,
        ),
    ],
)

h2 = box(s2, Inches(0.55), Inches(5.25), Inches(6.1), Inches(1.85))
txt(
    h2,
    [
        ("IF TIME RAN SHORT — WE BUILT IN CUT-ORDER", 13, ACCENT, True, 5),
        (
            "CUT FIRST:  voice (stretch) · web UI → CLI · two-in-one requests",
            13,
            DANGER,
            True,
            4,
        ),
        (
            "NEVER CUT:  confirmation step · idempotency · ask-don't-guess —",
            13,
            TEXT,
            False,
            1,
        ),
        ("those are the product.", 13, TEXT, False, 0),
    ],
)

# what could go wrong
w1 = box(s2, Inches(6.85), Inches(3.4), Inches(5.9), Inches(3.7))
txt(
    w1,
    [
        ("WHAT COULD GO WRONG — AND DOES", 13, GOLD, True, 6),
        (
            '▸  Ambiguous "أحمد" → numbered question, never a guess.',
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "▸  Insufficient balance → honest early reject; combined requests drop whole, never half-executed.",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "▸  Timeout / retry after success → idempotency key returns the original result — no double pay.",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "▸  Malformed LLM JSON → robust parse + bounded retries; fail loudly, never guess.",
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            '▸  Anything but an explicit "نعم" → "ما انحولّ شي" — nothing executes.',
            12.5,
            TEXT,
            False,
            4,
        ),
        (
            "Full evidence: tests/results.md · results_heldout.md · FAILURE_MODES.md (8 modes) · live demo ready on judge input",
            11.5,
            MUTED,
            False,
            0,
        ),
    ],
)

prs.save(OUT)
print(f"written: {OUT}")
